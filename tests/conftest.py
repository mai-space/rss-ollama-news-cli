from datetime import datetime

import pytest

from newsroom.config import AppConfig, DisplayConfig, EmailConfig, FeedConfig, OllamaConfig
from newsroom.feeds import Article


@pytest.fixture()
def sample_config() -> AppConfig:
    return AppConfig(
        feeds=[
            FeedConfig(
                name="Tech News", url="https://example.com/feed.xml", category="Tech", enabled=True
            ),
            FeedConfig(
                name="AI Blog", url="https://ai.example.com/feed", category="AI", enabled=True
            ),
            FeedConfig(
                name="Disabled", url="https://off.example.com/feed", category="Tech", enabled=False
            ),
        ],
        ollama=OllamaConfig(
            model="llama3.2", base_url="http://localhost:11434", prompt="Summarize: {content}"
        ),
        email=EmailConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="secret",
            from_addr="user@example.com",
            to_addrs=["recipient@example.com"],
        ),
        display=DisplayConfig(max_articles_per_feed=5, max_total_articles=20),
    )


@pytest.fixture()
def sample_article() -> Article:
    return Article(
        title="Exciting Tech Breakthrough",
        url="https://example.com/article/1",
        source="Tech News",
        category="Tech",
        published=datetime(2024, 6, 15, 12, 0, 0),
        content="<p>This is a <b>test</b> article about a major technological breakthrough.</p>",
    )


@pytest.fixture()
def sample_articles() -> list[Article]:
    return [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/article/{i}",
            source="Tech News",
            category="Tech",
            published=datetime(2024, 6, 15, 12 - i, 0, 0),
            content=f"<p>Content for article number {i}.</p>",
        )
        for i in range(5)
    ]
