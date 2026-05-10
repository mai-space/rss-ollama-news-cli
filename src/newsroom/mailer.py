from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from newsroom.config import EmailConfig
from newsroom.feeds import Article
from newsroom.logger import logger

try:
    import aiosmtplib
except ImportError:
    aiosmtplib = None  # type: ignore[assignment]


def build_html_digest(articles: list[Article], date: datetime) -> str:
    date_str = date.strftime("%B %d, %Y")
    parts = [
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Newsroom Digest — {date_str}</title>
<style>
  body{{font-family:Georgia,serif;max-width:800px;margin:0 auto;padding:20px;background:#f8f9fa;color:#212529}}
  h1{{color:#0d1b2a;border-bottom:3px solid #1c6ef3;padding-bottom:8px}}
  .meta{{color:#6c757d;font-size:.9em;margin-bottom:24px}}
  .article{{background:#fff;border-radius:10px;padding:20px 24px;margin:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .article-source{{font-size:.85em;color:#6c757d;margin-bottom:4px}}
  .article-title{{font-size:1.25em;font-weight:700;color:#0d1b2a;margin:0 0 12px}}
  .article-title a{{color:inherit;text-decoration:none}}
  .article-title a:hover{{text-decoration:underline;color:#1c6ef3}}
  .summary ul{{margin:0;padding-left:20px;line-height:1.7}}
  .no-summary{{color:#adb5bd;font-style:italic}}
  .category{{display:inline-block;background:#e9ecef;color:#495057;font-size:.75em;padding:2px 8px;border-radius:12px;margin-bottom:8px}}
</style>
</head>
<body>
<h1>📰 Newsroom Digest</h1>
<p class="meta">{date_str} &bull; {len(articles)} articles</p>
"""
    ]

    for article in articles:
        if article.summary and article.summary_status == "done":
            bullets = "".join(
                f"<li>{line.lstrip('•- ').strip()}</li>"
                for line in article.summary.strip().splitlines()
                if line.strip()
            )
            summary_html = f'<div class="summary"><ul>{bullets}</ul></div>'
        else:
            summary_html = '<p class="no-summary">No summary available</p>'

        parts.append(
            f"""<div class="article">
  <span class="category">{article.category}</span>
  <p class="article-source">{article.source} &bull; {article.published.strftime("%b %d, %H:%M")}</p>
  <p class="article-title"><a href="{article.url}">{article.title}</a></p>
  {summary_html}
</div>
"""
        )

    parts.append("</body></html>")
    return "".join(parts)


def build_text_digest(articles: list[Article], date: datetime) -> str:
    date_str = date.strftime("%B %d, %Y")
    lines = [f"📰 NEWSROOM DIGEST — {date_str}", "=" * 60, ""]
    for i, article in enumerate(articles, 1):
        lines.append(f"{i}. {article.title}")
        lines.append(
            f"   [{article.category}] {article.source} | {article.published.strftime('%b %d, %H:%M')}"
        )
        lines.append(f"   {article.url}")
        if article.summary and article.summary_status == "done":
            for bullet in article.summary.strip().splitlines():
                if bullet.strip():
                    lines.append(f"   {bullet.strip()}")
        else:
            lines.append("   (no summary)")
        lines.append("")
    return "\n".join(lines)


async def send_digest(articles: list[Article], config: EmailConfig) -> None:
    if not config.enabled:
        raise ValueError("Email is not enabled in configuration")
    if not config.to_addrs:
        raise ValueError("No recipient addresses configured")

    if aiosmtplib is None:
        raise RuntimeError("aiosmtplib not installed — run: pip install aiosmtplib")

    now = datetime.now()
    subject = config.subject_template.format(date=now.strftime("%Y-%m-%d"))
    from_addr = config.from_addr or config.username

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(config.to_addrs)
    msg.attach(MIMEText(build_text_digest(articles, now), "plain", "utf-8"))
    msg.attach(MIMEText(build_html_digest(articles, now), "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.username,
            password=config.password,
            start_tls=config.use_tls,
        )
        logger.info("Digest sent to %s", config.to_addrs)
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        raise
