from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from newsroom.config import FeedConfig
from newsroom.feeds import Article, fetch_all_feeds, fetch_feed

SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>First Article</title>
      <link>https://example.com/1</link>
      <description>Content of the first article.</description>
      <pubDate>Mon, 15 Jan 2024 12:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Second Article</title>
      <link>https://example.com/2</link>
      <description>Content of the second article.</description>
      <pubDate>Mon, 15 Jan 2024 11:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Third Article</title>
      <link>https://example.com/3</link>
      <description>Third article content.</description>
      <pubDate>Mon, 15 Jan 2024 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def _mock_response(content: bytes = SAMPLE_RSS) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_fetch_feed_returns_articles():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response())

    articles = await fetch_feed(client, "Test Feed", "https://example.com/rss", "Tech", 10)

    assert len(articles) == 3
    assert articles[0].title == "First Article"
    assert articles[0].source == "Test Feed"
    assert articles[0].category == "Tech"
    assert articles[0].url == "https://example.com/1"


@pytest.mark.asyncio
async def test_fetch_feed_respects_max_items():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response())

    articles = await fetch_feed(client, "Test Feed", "https://example.com/rss", "Tech", 2)

    assert len(articles) == 2


@pytest.mark.asyncio
async def test_fetch_feed_returns_empty_on_http_error():
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("Connection refused"))

    articles = await fetch_feed(client, "Bad Feed", "https://bad.example.com", "Tech", 10)

    assert articles == []


@pytest.mark.asyncio
async def test_fetch_all_feeds_skips_disabled():
    feeds = [
        FeedConfig(name="Active", url="https://active.com/feed", category="Tech", enabled=True),
        FeedConfig(name="Disabled", url="https://nope.com/feed", category="Tech", enabled=False),
    ]

    with patch("newsroom.feeds.httpx.AsyncClient") as mock_cls:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.get = AsyncMock(return_value=_mock_response())
        mock_cls.return_value = ctx

        articles = await fetch_all_feeds(feeds, max_per_feed=10)

    assert all(a.source == "Active" for a in articles)


@pytest.mark.asyncio
async def test_fetch_all_feeds_sorted_by_date():
    feeds = [
        FeedConfig(name="Feed A", url="https://a.com/feed", category="Tech", enabled=True),
    ]

    with patch("newsroom.feeds.httpx.AsyncClient") as mock_cls:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.get = AsyncMock(return_value=_mock_response())
        mock_cls.return_value = ctx

        articles = await fetch_all_feeds(feeds, max_per_feed=10)

    dates = [a.published for a in articles]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_fetch_all_feeds_empty_when_all_disabled():
    feeds = [
        FeedConfig(name="Off", url="https://off.com/feed", category="Tech", enabled=False),
    ]
    articles = await fetch_all_feeds(feeds, max_per_feed=10)
    assert articles == []


def test_article_id_equals_url():
    article = Article(
        title="Test",
        url="https://example.com/article",
        source="Test",
        category="Tech",
        published=datetime.now(),
        content="",
    )
    assert article.id == "https://example.com/article"


def test_article_default_summary_status():
    article = Article(
        title="Test",
        url="https://example.com/1",
        source="Test",
        category="Tech",
        published=datetime.now(),
        content="",
    )
    assert article.summary_status == "pending"
    assert article.summary is None
    assert article.error is None
