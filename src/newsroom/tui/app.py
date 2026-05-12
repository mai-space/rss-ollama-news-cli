from __future__ import annotations

import hashlib
import webbrowser
from itertools import groupby
from typing import ClassVar

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Label, ListItem, ListView, Static

from newsroom.config import AppConfig, load_config
from newsroom.feeds import Article, fetch_all_feeds
from newsroom.logger import logger
from newsroom.summarizer import check_ollama_available, summarize_article

# ── Status icons and colours ──────────────────────────────────────────────────

_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "pending": ("○", "dim"),
    "loading": ("◌", "yellow"),
    "done": ("●", "green"),
    "error": ("✗", "red"),
}


def _feed_safe_id(url: str) -> str:
    """Return a stable, collision-free, CSS-safe widget ID derived from the feed URL.

    Uses a SHA-256 hash of the URL prefixed with 'f' so the result always begins
    with a letter (CSS identifiers may not start with a digit) and is guaranteed
    unique as long as feed URLs are distinct.
    """
    return "f" + hashlib.sha256(url.encode()).hexdigest()[:12]


def _status_cell(status: str) -> Text:
    icon, style = _STATUS_STYLE.get(status, ("?", "dim"))
    return Text(icon, style=style, justify="center")


# ── App ───────────────────────────────────────────────────────────────────────


class NewsroomApp(App[None]):
    """Newsroom — RSS + AI newsletter TUI."""

    TITLE = "Newsroom"
    SUB_TITLE = "RSS · AI · Terminal"

    CSS = """
    Screen {
        background: #0d1117;
        color: #e6edf3;
        layers: base;
    }

    Header {
        background: #161b22;
        color: #58a6ff;
        text-style: bold;
    }

    Footer {
        background: #161b22;
        color: #8b949e;
    }

    #main {
        height: 1fr;
    }

    /* ── Left panel ── */
    #left {
        width: 28;
        border-right: tall #30363d;
        background: #0d1117;
    }

    #source-header {
        background: #161b22;
        color: #8b949e;
        text-style: bold;
        height: 2;
        padding: 0 1;
        content-align: left middle;
    }

    #feed-list {
        background: #0d1117;
        height: 1fr;
        border: none;
        scrollbar-size: 1 1;
        scrollbar-color: #30363d;
    }

    #feed-list > ListItem {
        padding: 0 1;
        height: 2;
        background: #0d1117;
        color: #e6edf3;
    }

    #feed-list > ListItem.--highlight {
        background: #1f6feb;
        color: #ffffff;
    }

    #feed-list > ListItem:hover {
        background: #21262d;
    }

    .category-item {
        color: #8b949e;
        text-style: bold italic;
        background: #0d1117;
        padding: 0 1;
        height: 1;
    }

    /* ── Right panel ── */
    #right {
        width: 1fr;
    }

    #articles-panel {
        height: 1fr;
        border-bottom: tall #30363d;
    }

    DataTable {
        height: 1fr;
        background: #0d1117;
        border: none;
        scrollbar-size: 1 1;
        scrollbar-color: #30363d;
    }

    DataTable > .datatable--header {
        background: #161b22;
        color: #8b949e;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1f6feb;
        color: #ffffff;
    }

    DataTable > .datatable--hover {
        background: #21262d;
    }

    /* ── Summary panel ── */
    #summary-panel {
        height: 14;
        border-top: tall #30363d;
        background: #161b22;
        padding: 0 2 1 2;
        overflow-y: auto;
    }

    #summary-title {
        color: #58a6ff;
        text-style: bold;
        padding: 1 0 0 0;
        height: 3;
    }

    #summary-body {
        color: #c9d1d9;
    }

    /* ── Status bar ── */
    #status-bar {
        height: 1;
        background: #0d1117;
        padding: 0 2;
        color: #8b949e;
        border-top: tall #21262d;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_article", "Open URL"),
        Binding("e", "email_digest", "Email Digest"),
        Binding("tab", "focus_next", "Next panel"),
        Binding("shift+tab", "focus_previous", "Prev panel"),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    # ── State ────────────────────────────────────────────────────────────────
    _articles: list[Article]
    _filter: str | None  # None = all

    selected_article: reactive[Article | None] = reactive(None)

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self._articles = []
        self._filter = None
        self._feed_name_map: dict[str, str] = {}  # sanitised id-suffix -> original name

    # ── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            # Left: feed list
            with Vertical(id="left"):
                yield Label("  SOURCES", id="source-header")
                yield ListView(
                    ListItem(Label("  All Feeds"), id="feed-all"),
                    id="feed-list",
                )

            # Right: articles + summary
            with Vertical(id="right"):
                with Vertical(id="articles-panel"):
                    yield DataTable(id="article-table", cursor_type="row", zebra_stripes=True)
                with Vertical(id="summary-panel"):
                    yield Label("", id="summary-title")
                    yield Static("Select an article to view its AI summary.", id="summary-body")

        yield Static("", id="status-bar")
        yield Footer()

    # ── Mount ────────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        table = self.query_one("#article-table", DataTable)
        table.add_column("", key="status", width=3)
        table.add_column("Title", key="title")
        table.add_column("Source", key="source", width=18)
        table.add_column("Category", key="category", width=14)
        table.add_column("Published", key="published", width=13)

        self._populate_feed_list()
        self.refresh_feeds()

    def _populate_feed_list(self) -> None:
        lv = self.query_one("#feed-list", ListView)
        # Group enabled feeds by category
        enabled = [f for f in self.config.feeds if f.enabled]
        enabled.sort(key=lambda f: f.category)
        for category, feeds in groupby(enabled, key=lambda f: f.category):
            lv.append(ListItem(Label(f"  {category.upper()}"), classes="category-item"))
            for feed in feeds:
                safe_id = _feed_safe_id(feed.url)
                self._feed_name_map[safe_id] = feed.name
                lv.append(ListItem(Label(f"    {feed.name}"), id=f"feed-{safe_id}"))

    # ── Workers ──────────────────────────────────────────────────────────────

    @work(exclusive=True, group="fetch")
    async def refresh_feeds(self) -> None:
        self._set_status("Fetching feeds…", "loading")

        ollama_ok = await check_ollama_available(self.config.ollama)
        if not ollama_ok:
            self._set_status(
                "⚠ Ollama not reachable — summaries disabled. Start Ollama and press [r] to retry.",
                "warn",
            )

        try:
            articles = await fetch_all_feeds(
                self.config.feeds,
                max_per_feed=self.config.display.max_articles_per_feed,
            )
        except Exception as exc:
            logger.error("Feed refresh failed: %s", exc)
            self._set_status(f"Error fetching feeds: {exc}", "error")
            return

        limit = self.config.display.max_total_articles
        self._articles = articles[:limit]
        self._rebuild_table()
        self._set_status(
            f"Loaded {len(self._articles)} articles from {len([f for f in self.config.feeds if f.enabled])} feeds",
            "ok",
        )

        if ollama_ok:
            for article in self._articles:
                self._summarize(article)

    @work(group="summarize")
    async def _summarize(self, article: Article) -> None:
        article.summary_status = "loading"
        self._update_status_cell(article)

        try:
            article.summary = await summarize_article(article, self.config.ollama)
            article.summary_status = "done"
        except Exception as exc:
            article.error = str(exc)
            article.summary_status = "error"

        self._update_status_cell(article)

        # Refresh summary panel if this article is currently shown
        sel = self.selected_article
        if sel and sel.url == article.url:
            self._show_summary(article)

    # ── Table helpers ────────────────────────────────────────────────────────

    def _visible_articles(self) -> list[Article]:
        if self._filter is None:
            return self._articles
        return [a for a in self._articles if a.source == self._filter]

    def _rebuild_table(self) -> None:
        table = self.query_one("#article-table", DataTable)
        table.clear()
        for article in self._visible_articles():
            table.add_row(
                _status_cell(article.summary_status),
                article.title[:90],
                article.source[:18],
                article.category[:14],
                article.published.strftime(self.config.display.date_format),
                key=article.url,
            )

    def _update_status_cell(self, article: Article) -> None:
        try:
            table = self.query_one("#article-table", DataTable)
            table.update_cell(article.url, "status", _status_cell(article.summary_status))
        except Exception:
            pass  # Row may not be visible under current filter

    # ── Summary panel ────────────────────────────────────────────────────────

    def _show_summary(self, article: Article) -> None:
        self.query_one("#summary-title", Label).update(
            f"[bold]{article.title}[/bold]  [dim]— {article.source}[/dim]"
        )
        body = self.query_one("#summary-body", Static)

        if article.summary_status == "done" and article.summary:
            body.update(article.summary)
        elif article.summary_status == "loading":
            body.update("[yellow]◌  Generating summary…[/yellow]")
        elif article.summary_status == "error":
            body.update(f"[red]✗  Summary failed:[/red] {article.error}")
        else:
            body.update("[dim]○  Pending…[/dim]")

    # ── Status bar ───────────────────────────────────────────────────────────

    def _set_status(self, message: str, kind: str = "info") -> None:
        style_map = {
            "loading": "yellow",
            "ok": "green",
            "error": "red",
            "warn": "yellow",
            "info": "dim",
        }
        colour = style_map.get(kind, "dim")
        bar = self.query_one("#status-bar", Static)
        bar.update(f"[{colour}]{message}[/{colour}]")

    # ── Event handlers ───────────────────────────────────────────────────────

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        key = event.row_key.value
        article = next((a for a in self._articles if a.url == key), None)
        if article:
            self.selected_article = article
            self._show_summary(article)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id == "feed-all":
            self._filter = None
        elif item_id.startswith("feed-"):
            id_suffix = item_id[len("feed-"):]
            if id_suffix not in self._feed_name_map:
                logger.warning("No feed name found for id suffix %r", id_suffix)
                return
            self._filter = self._feed_name_map[id_suffix]
        else:
            return  # category header — ignore
        self._rebuild_table()

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._articles = []
        self._rebuild_table()
        self.refresh_feeds()

    def action_open_article(self) -> None:
        article = self.selected_article
        if article and article.url:
            webbrowser.open(article.url)
            self._set_status(f"Opened {article.url}", "info")
        else:
            self._set_status("No article selected", "warn")

    def action_email_digest(self) -> None:
        self._do_email_digest()

    @work(group="email")
    async def _do_email_digest(self) -> None:
        if not self.config.email.enabled:
            self._set_status("Email not configured — run: news config email --help", "error")
            return
        self._set_status("Sending email digest…", "loading")
        try:
            from newsroom.mailer import send_digest

            done = [a for a in self._articles if a.summary_status == "done"]
            await send_digest(done, self.config.email)
            recipients = ", ".join(self.config.email.to_addrs)
            self._set_status(f"✓ Digest sent to {recipients}", "ok")
        except Exception as exc:
            logger.error("Email failed: %s", exc)
            self._set_status(f"Email failed: {exc}", "error")

    def action_show_help(self) -> None:
        self._set_status(
            "[q] Quit  [r] Refresh  [o] Open URL  [e] Email digest  "
            "[↑↓] Navigate  [Tab] Switch panel",
            "info",
        )
