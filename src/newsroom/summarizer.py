import html as _html
import re

import httpx

from newsroom.config import OllamaConfig
from newsroom.feeds import Article
from newsroom.logger import logger

try:
    import ollama
except ImportError:
    ollama = None  # type: ignore[assignment]

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    return _html.unescape(text).strip()


async def summarize_article(article: Article, config: OllamaConfig) -> str:
    try:
        if ollama is None:
            raise RuntimeError("ollama package not installed — run: pip install ollama")

        content = strip_html(article.content)
        if len(content) < 50:
            content = article.title

        prompt = config.prompt.format(content=content[:4000])
        client = ollama.AsyncClient(host=config.base_url)
        response = await client.chat(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": config.max_tokens},
        )
        return response.message.content.strip()
    except Exception as exc:
        logger.error("Summarize failed for '%s': %s", article.title, exc)
        raise


async def check_ollama_available(config: OllamaConfig) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{config.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
    except Exception:
        return False
