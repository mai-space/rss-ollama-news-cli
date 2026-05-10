"""Newsroom CLI — news <subcommand>"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from newsroom.config import AppConfig, FeedConfig, load_config, save_config

app = typer.Typer(
    name="news",
    help="📰 [bold]Newsroom[/bold] — RSS feeds + AI summaries in your terminal.",
    rich_markup_mode="rich",
    no_args_is_help=False,
)
feeds_app = typer.Typer(help="Manage RSS feed sources.")
config_app = typer.Typer(help="View and edit configuration.")
app.add_typer(feeds_app, name="feeds")
app.add_typer(config_app, name="config")

console = Console()


# ── Root command — launch TUI ─────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Launch the interactive Newsroom TUI."""
    if ctx.invoked_subcommand is None:
        _launch_tui()


def _launch_tui() -> None:
    from newsroom.tui.app import NewsroomApp

    NewsroomApp(config=load_config()).run()


# ── digest ────────────────────────────────────────────────────────────────────


@app.command()
def digest(
    email: bool = typer.Option(False, "--email", "-e", help="Send the digest via email."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save digest to a file."),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI summarisation."),
) -> None:
    """Fetch feeds, summarise with AI, and optionally email or save the digest."""
    asyncio.run(_run_digest(email=email, output=output, skip_ai=no_ai))


async def _run_digest(*, email: bool, output: Path | None, skip_ai: bool) -> None:
    config = load_config()

    with console.status("[bold blue]Fetching RSS feeds…"):
        from newsroom.feeds import fetch_all_feeds

        articles = await fetch_all_feeds(
            config.feeds, max_per_feed=config.display.max_articles_per_feed
        )
    console.print(f"[green]✓[/green] Fetched [bold]{len(articles)}[/bold] articles")

    if not skip_ai:
        from newsroom.summarizer import check_ollama_available, summarize_article

        if not await check_ollama_available(config.ollama):
            console.print("[yellow]⚠[/yellow] Ollama not reachable — skipping summaries")
        else:
            with console.status(f"[bold blue]Summarising with {config.ollama.model}…"):
                tasks = [summarize_article(a, config.ollama) for a in articles]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            for article, result in zip(articles, results):
                if isinstance(result, Exception):
                    article.summary_status = "error"
                    article.error = str(result)
                else:
                    article.summary = result  # type: ignore[assignment]
                    article.summary_status = "done"
            done = sum(1 for a in articles if a.summary_status == "done")
            console.print(
                f"[green]✓[/green] Summarised [bold]{done}/{len(articles)}[/bold] articles"
            )

    if output:
        from datetime import datetime

        from newsroom.mailer import build_text_digest

        output.write_text(build_text_digest(articles, datetime.now()), encoding="utf-8")
        console.print(f"[green]✓[/green] Saved digest to [bold]{output}[/bold]")

    if email:
        if not config.email.enabled:
            console.print(
                "[red]✗[/red] Email not configured. Run: [bold]news config email --help[/bold]"
            )
            raise typer.Exit(1)
        with console.status("[bold blue]Sending email…"):
            from newsroom.mailer import send_digest

            await send_digest(articles, config.email)
        console.print(f"[green]✓[/green] Sent to [bold]{', '.join(config.email.to_addrs)}[/bold]")

    if not output and not email:
        from datetime import datetime

        from newsroom.mailer import build_text_digest

        console.print(build_text_digest(articles, datetime.now()))


# ── feeds subcommands ─────────────────────────────────────────────────────────


@feeds_app.command("list")
def feeds_list() -> None:
    """List all configured RSS feeds."""
    config = load_config()
    table = Table(title="RSS Feeds", show_lines=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Category")
    table.add_column("URL")
    table.add_column("Status")

    for i, feed in enumerate(config.feeds, 1):
        status = "[green]enabled[/green]" if feed.enabled else "[red]disabled[/red]"
        table.add_row(str(i), feed.name, feed.category, feed.url, status)

    console.print(table)


@feeds_app.command("add")
def feeds_add(
    name: str = typer.Argument(..., help="Feed display name"),
    url: str = typer.Argument(..., help="RSS/Atom feed URL"),
    category: str = typer.Option("General", "--category", "-c", help="Feed category"),
) -> None:
    """Add a new RSS feed."""
    config = load_config()
    if any(f.url == url for f in config.feeds):
        console.print(f"[yellow]⚠[/yellow] A feed with URL [bold]{url}[/bold] already exists")
        raise typer.Exit(1)
    config.feeds.append(FeedConfig(name=name, url=url, category=category))
    save_config(config)
    console.print(f"[green]✓[/green] Added [bold]{name}[/bold] ([dim]{url}[/dim])")


@feeds_app.command("remove")
def feeds_remove(
    name: str = typer.Argument(..., help="Exact feed name to remove"),
) -> None:
    """Remove an RSS feed by name."""
    config = load_config()
    before = len(config.feeds)
    config.feeds = [f for f in config.feeds if f.name != name]
    if len(config.feeds) == before:
        console.print(f"[red]✗[/red] Feed [bold]{name!r}[/bold] not found")
        raise typer.Exit(1)
    save_config(config)
    console.print(f"[green]✓[/green] Removed [bold]{name}[/bold]")


@feeds_app.command("toggle")
def feeds_toggle(
    name: str = typer.Argument(..., help="Feed name to enable/disable"),
) -> None:
    """Toggle a feed on or off."""
    config = load_config()
    for feed in config.feeds:
        if feed.name == name:
            feed.enabled = not feed.enabled
            save_config(config)
            verb = "enabled" if feed.enabled else "disabled"
            console.print(f"[green]✓[/green] [bold]{name}[/bold] {verb}")
            return
    console.print(f"[red]✗[/red] Feed [bold]{name!r}[/bold] not found")
    raise typer.Exit(1)


# ── config subcommands ────────────────────────────────────────────────────────


@config_app.command("show")
def config_show() -> None:
    """Show the current configuration."""
    config = load_config()
    console.print(
        Panel(
            config.model_dump_json(indent=2),
            title="[bold]Configuration[/bold]",
            border_style="blue",
        )
    )


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dot-separated key, e.g. ollama.model"),
    value: str = typer.Argument(..., help="New value (JSON-decoded automatically)"),
) -> None:
    """Set a configuration value by dot-separated key path."""
    config = load_config()
    data = config.model_dump()

    keys = key.split(".")
    node = data
    for k in keys[:-1]:
        if k not in node:
            console.print(f"[red]✗[/red] Unknown key segment: [bold]{k}[/bold]")
            raise typer.Exit(1)
        node = node[k]

    last = keys[-1]
    if last not in node:
        console.print(f"[red]✗[/red] Unknown key: [bold]{key}[/bold]")
        raise typer.Exit(1)

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value

    node[last] = parsed

    try:
        new_config = AppConfig.model_validate(data)
        save_config(new_config)
        console.print(f"[green]✓[/green] Set [bold]{key}[/bold] = {value!r}")
    except Exception as exc:
        console.print(f"[red]✗[/red] Invalid value: {exc}")
        raise typer.Exit(1) from exc


@config_app.command("email")
def config_email(
    smtp_host: str | None = typer.Option(None, help="SMTP server hostname"),
    smtp_port: int | None = typer.Option(None, help="SMTP port (default 587)"),
    username: str | None = typer.Option(None, help="SMTP login username"),
    password: str | None = typer.Option(None, help="SMTP login password"),
    from_addr: str | None = typer.Option(None, "--from", help="Sender email address"),
    to: list[str] | None = typer.Option(None, "--to", help="Recipient addresses (repeatable)"),
    enable: bool = typer.Option(True, "--enable/--disable", help="Enable or disable email sending"),
) -> None:
    """Configure email (SMTP) settings."""
    config = load_config()
    em = config.email

    if smtp_host is not None:
        em.smtp_host = smtp_host
    if smtp_port is not None:
        em.smtp_port = smtp_port
    if username is not None:
        em.username = username
    if password is not None:
        em.password = password
    if from_addr is not None:
        em.from_addr = from_addr
    if to:
        em.to_addrs = list(to)
    em.enabled = enable

    save_config(config)
    console.print("[green]✓[/green] Email configuration saved")
    if enable and not em.to_addrs:
        console.print("[yellow]⚠[/yellow] No recipients set — add with --to address@example.com")


if __name__ == "__main__":
    app()
