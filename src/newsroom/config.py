import json
from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".config" / "newsroom"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Curated default feeds organised by category
DEFAULT_FEEDS = [
    # UI / UX
    {
        "name": "Smashing Magazine",
        "url": "https://www.smashingmagazine.com/feed/",
        "category": "UI/UX",
        "enabled": True,
    },
    {
        "name": "Nielsen Norman Group",
        "url": "https://www.nngroup.com/feed/rss/",
        "category": "UI/UX",
        "enabled": True,
    },
    {
        "name": "UX Collective",
        "url": "https://uxdesign.cc/feed",
        "category": "UI/UX",
        "enabled": True,
    },
    # CSS / Sass
    {
        "name": "CSS-Tricks",
        "url": "https://css-tricks.com/feed/",
        "category": "CSS",
        "enabled": True,
    },
    # JavaScript / TypeScript
    {
        "name": "JavaScript Weekly",
        "url": "https://javascriptweekly.com/rss/",
        "category": "JavaScript",
        "enabled": True,
    },
    {
        "name": "TypeScript Blog",
        "url": "https://devblogs.microsoft.com/typescript/feed/",
        "category": "JavaScript",
        "enabled": True,
    },
    # Tech / Web
    {"name": "web.dev", "url": "https://web.dev/feed.xml", "category": "Tech", "enabled": True},
    {
        "name": "Mozilla Hacks",
        "url": "https://hacks.mozilla.org/feed/",
        "category": "Tech",
        "enabled": True,
    },
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "category": "Tech",
        "enabled": True,
    },
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/rss",
        "category": "Tech",
        "enabled": True,
    },
    # AI
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "AI",
        "enabled": True,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "AI",
        "enabled": True,
    },
    # PHP
    {"name": "PHP.Watch", "url": "https://php.watch/feed/", "category": "PHP", "enabled": True},
    {
        "name": "Laravel News",
        "url": "https://laravel-news.com/feed",
        "category": "PHP",
        "enabled": True,
    },
    # TYPO3
    {
        "name": "TYPO3 News",
        "url": "https://typo3.org/rss.xml",
        "category": "TYPO3",
        "enabled": True,
    },
    # SQL
    {
        "name": "SQL Performance",
        "url": "https://sqlperformance.com/feed",
        "category": "SQL",
        "enabled": True,
    },
]


class FeedConfig(BaseModel):
    name: str
    url: str
    enabled: bool = True
    category: str = "General"


class OllamaConfig(BaseModel):
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    prompt: str = (
        "You are a professional news summarizer. Summarize the following article "
        "in 3-5 concise bullet points starting with '•'. Focus on the key facts, "
        "insights, and implications. Be objective and clear.\n\nArticle:\n{content}"
    )
    max_tokens: int = 500
    timeout: int = 120


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = []
    subject_template: str = "📰 Newsroom Digest — {date}"


class DisplayConfig(BaseModel):
    max_articles_per_feed: int = 10
    max_total_articles: int = 60
    date_format: str = "%b %d %H:%M"


class AppConfig(BaseModel):
    feeds: list[FeedConfig] = Field(
        default_factory=lambda: [FeedConfig(**f) for f in DEFAULT_FEEDS]
    )
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)


def load_config() -> AppConfig:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return AppConfig.model_validate(data)
        except Exception as exc:
            from newsroom.logger import logger

            logger.warning("Failed to load config (%s) — using defaults", exc)
    config = AppConfig()
    save_config(config)
    return config


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(config.model_dump_json(indent=2), encoding="utf-8")
