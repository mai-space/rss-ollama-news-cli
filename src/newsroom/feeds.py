import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import feedparser
import httpx

from newsroom.logger import logger

_HTTP_HEADERS = {
    "User-Agent": "Newsroom/0.1.0 (RSS reader; +https://github.com/mai-space/rss-ollama-news-cli)"
}


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    published: datetime
    content: str
    summary: str | None = None
    summary_status: Literal["pending", "loading", "done", "error"] = "pending"
    error: str | None = None

    @property
    def id(self) -> str:
        return self.url


def _parse_date(entry: object) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except Exception:
                pass
    return datetime.now()


def _extract_content(entry: object) -> str:
    if hasattr(entry, "content") and entry.content:
        return entry.content[0].get("value", "")
    if hasattr(entry, "summary"):
        return entry.summary
    if hasattr(entry, "description"):
        return entry.description
    return ""


async def fetch_feed(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    category: str,
    max_items: int,
) -> list[Article]:
    try:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        articles: list[Article] = []
        for entry in feed.entries[:max_items]:
            articles.append(
                Article(
                    title=entry.get("title", "Untitled").strip(),
                    url=entry.get("link", ""),
                    source=name,
                    category=category,
                    published=_parse_date(entry),
                    content=_extract_content(entry),
                )
            )
        logger.info("Fetched %d articles from %s", len(articles), name)
        return articles
    except Exception as exc:
        logger.error("Failed to fetch feed %s (%s): %s", name, url, exc)
        return []


async def fetch_all_feeds(
    configs: list,  # list[FeedConfig]
    max_per_feed: int = 10,
) -> list[Article]:
    enabled = [c for c in configs if c.enabled]
    if not enabled:
        return []

    async with httpx.AsyncClient(headers=_HTTP_HEADERS) as client:
        tasks = [fetch_feed(client, c.name, c.url, c.category, max_per_feed) for c in enabled]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: list[Article] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Feed gather exception: %s", result)
        elif isinstance(result, list):
            articles.extend(result)

    articles.sort(key=lambda a: a.published, reverse=True)
    return articles
