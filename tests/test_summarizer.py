from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from newsroom.config import OllamaConfig
from newsroom.feeds import Article
from newsroom.summarizer import check_ollama_available, strip_html, summarize_article


def _article(
    content: str = "<p>This is a test article about AI and machine learning.</p>",
) -> Article:
    return Article(
        title="AI Breakthrough Announced",
        url="https://example.com/ai",
        source="Tech News",
        category="AI",
        published=datetime.now(),
        content=content,
    )


@pytest.fixture()
def ollama_config() -> OllamaConfig:
    return OllamaConfig(
        model="llama3.2",
        base_url="http://localhost:11434",
        prompt="Summarize: {content}",
    )


# ── strip_html ────────────────────────────────────────────────────────────────


def test_strip_html_removes_tags():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_decodes_entities():
    assert strip_html("A &amp; B &lt;3") == "A & B <3"


def test_strip_html_empty():
    assert strip_html("") == ""


def test_strip_html_plain_text():
    assert strip_html("plain text") == "plain text"


def test_strip_html_nested_tags():
    assert strip_html("<div><p><span>Nested</span></p></div>") == "Nested"


# ── summarize_article ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summarize_article_success(ollama_config: OllamaConfig):
    mock_response = MagicMock()
    mock_response.message.content = "• Key insight one\n• Key insight two\n• Key insight three"

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=mock_response)

    with patch("newsroom.summarizer.ollama.AsyncClient", return_value=mock_client):
        result = await summarize_article(_article(), ollama_config)

    assert "Key insight one" in result
    mock_client.chat.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_uses_title_for_short_content(ollama_config: OllamaConfig):
    short_article = _article(content="<p>Hi</p>")  # stripped = "Hi" — less than 50 chars

    mock_response = MagicMock()
    mock_response.message.content = "Summary"
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=mock_response)

    with patch("newsroom.summarizer.ollama.AsyncClient", return_value=mock_client):
        await summarize_article(short_article, ollama_config)

    call_kwargs = mock_client.chat.call_args.kwargs
    prompt_content = call_kwargs["messages"][0]["content"]
    assert short_article.title in prompt_content


@pytest.mark.asyncio
async def test_summarize_article_raises_on_ollama_error(ollama_config: OllamaConfig):
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=RuntimeError("model not found"))

    with patch("newsroom.summarizer.ollama.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="model not found"):
            await summarize_article(_article(), ollama_config)


@pytest.mark.asyncio
async def test_summarize_truncates_long_content(ollama_config: OllamaConfig):
    long_content = "word " * 2000  # ~10 000 chars
    article = _article(content=long_content)

    mock_response = MagicMock()
    mock_response.message.content = "Summary"
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=mock_response)

    with patch("newsroom.summarizer.ollama.AsyncClient", return_value=mock_client):
        await summarize_article(article, ollama_config)

    call_kwargs = mock_client.chat.call_args.kwargs
    prompt_text = call_kwargs["messages"][0]["content"]
    # Prompt template is "Summarize: {content}" — content is truncated to 4000 chars
    assert len(prompt_text) <= len("Summarize: ") + 4000 + 5


# ── check_ollama_available ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_ollama_available_true():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("newsroom.summarizer.httpx.AsyncClient") as mock_cls:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = ctx

        result = await check_ollama_available(OllamaConfig())

    assert result is True


@pytest.mark.asyncio
async def test_check_ollama_available_false_on_connection_error():
    with patch("newsroom.summarizer.httpx.AsyncClient") as mock_cls:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.get = AsyncMock(side_effect=Exception("connection refused"))
        mock_cls.return_value = ctx

        result = await check_ollama_available(OllamaConfig())

    assert result is False


@pytest.mark.asyncio
async def test_check_ollama_available_false_on_bad_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with patch("newsroom.summarizer.httpx.AsyncClient") as mock_cls:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        ctx.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = ctx

        result = await check_ollama_available(OllamaConfig())

    assert result is False
