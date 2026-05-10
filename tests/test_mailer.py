from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from newsroom.config import EmailConfig
from newsroom.feeds import Article
from newsroom.mailer import build_html_digest, build_text_digest, send_digest


def _article(
    title: str = "Test Article",
    source: str = "Tech News",
    category: str = "Tech",
    summary: str | None = "• Point one\n• Point two\n• Point three",
    status: str = "done",
) -> Article:
    a = Article(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        source=source,
        category=category,
        published=datetime(2024, 6, 15, 12, 0),
        content="Full article body.",
    )
    a.summary = summary
    a.summary_status = status  # type: ignore[assignment]
    return a


@pytest.fixture()
def articles() -> list[Article]:
    return [
        _article("AI Advances", "MIT Tech Review", "AI"),
        _article("TYPO3 Update", "TYPO3 News", "TYPO3", summary=None, status="pending"),
        _article("CSS Tips", "CSS-Tricks", "CSS"),
    ]


@pytest.fixture()
def email_cfg() -> EmailConfig:
    return EmailConfig(
        enabled=True,
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="sender@example.com",
        password="s3cr3t",
        from_addr="sender@example.com",
        to_addrs=["recipient@example.com"],
    )


# ── HTML digest ───────────────────────────────────────────────────────────────


def test_html_digest_contains_titles(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    for a in articles:
        assert a.title in html


def test_html_digest_contains_urls(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    for a in articles:
        assert a.url in html


def test_html_digest_is_complete_html(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_html_digest_summary_bullets(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    assert "Point one" in html


def test_html_digest_no_summary_placeholder(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    assert "No summary available" in html


def test_html_digest_includes_categories(articles: list[Article]):
    html = build_html_digest(articles, datetime(2024, 6, 15))
    assert "AI" in html
    assert "TYPO3" in html


# ── Text digest ───────────────────────────────────────────────────────────────


def test_text_digest_header(articles: list[Article]):
    text = build_text_digest(articles, datetime(2024, 6, 15))
    assert "NEWSROOM DIGEST" in text


def test_text_digest_contains_titles(articles: list[Article]):
    text = build_text_digest(articles, datetime(2024, 6, 15))
    for a in articles:
        assert a.title in text


def test_text_digest_contains_urls(articles: list[Article]):
    text = build_text_digest(articles, datetime(2024, 6, 15))
    for a in articles:
        assert a.url in text


def test_text_digest_summary_bullets(articles: list[Article]):
    text = build_text_digest(articles, datetime(2024, 6, 15))
    assert "Point one" in text


def test_text_digest_no_summary_label(articles: list[Article]):
    text = build_text_digest(articles, datetime(2024, 6, 15))
    assert "(no summary)" in text


# ── send_digest ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_digest_raises_when_disabled(articles: list[Article]):
    cfg = EmailConfig(enabled=False)
    with pytest.raises(ValueError, match="not enabled"):
        await send_digest(articles, cfg)


@pytest.mark.asyncio
async def test_send_digest_raises_with_no_recipients(articles: list[Article]):
    cfg = EmailConfig(enabled=True, to_addrs=[])
    with pytest.raises(ValueError, match="No recipient"):
        await send_digest(articles, cfg)


@pytest.mark.asyncio
async def test_send_digest_calls_aiosmtplib(articles: list[Article], email_cfg: EmailConfig):
    with patch("newsroom.mailer.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await send_digest(articles, email_cfg)
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_digest_propagates_smtp_error(articles: list[Article], email_cfg: EmailConfig):
    with patch("newsroom.mailer.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ConnectionRefusedError("SMTP unreachable")
        with pytest.raises(ConnectionRefusedError):
            await send_digest(articles, email_cfg)


@pytest.mark.asyncio
async def test_send_digest_subject_contains_date(articles: list[Article], email_cfg: EmailConfig):
    captured = {}

    async def fake_send(msg, **kwargs):
        captured["subject"] = msg["Subject"]

    with patch("newsroom.mailer.aiosmtplib.send", side_effect=fake_send):
        await send_digest(articles, email_cfg)

    assert "Newsroom Digest" in captured["subject"]
