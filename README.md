# 📰 Newsroom

> A beautiful, keyboard-driven CLI newsletter — fetches RSS feeds from curated tech sources, summarises articles locally with [Ollama](https://ollama.ai), and lets you browse, read, and email the digest from your terminal.

[![CI](https://github.com/mai-space/rss-ollama-news-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mai-space/rss-ollama-news-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

| Feature | Details |
|---|---|
| **RSS reader** | 16 curated default feeds across UI/UX, Tech, AI, PHP, TYPO3, JS/TS, CSS, SQL |
| **AI summaries** | Local summarisation via Ollama — fully private, no API key needed |
| **Beautiful TUI** | Three-pane terminal UI (sources · articles · summary) built with [Textual](https://github.com/Textualize/textual) |
| **Optimistic UI** | Articles appear instantly; summaries load in the background per-article |
| **Email digest** | Sends a polished HTML + plain-text digest via SMTP |
| **Configurable** | Custom Ollama model, prompt, SMTP settings, and feeds — all in `~/.config/newsroom/config.json` |
| **Error logging** | All errors caught and logged to `~/.local/share/newsroom/logs/newsroom.log` |

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/mai-space/rss-ollama-news-cli/main/install.sh | bash
```

> **Development branch:** until this is merged to `main`, use the full branch URL:
> ```bash
> curl -fsSL "https://raw.githubusercontent.com/mai-space/rss-ollama-news-cli/claude/cli-newsletter-rss-ai-heER5/install.sh" | bash
> ```

The script auto-selects the best installation method for your system:

| Environment | Method used |
|---|---|
| `pipx` available | `pipx install` (isolated, recommended) |
| macOS + Homebrew, no `pipx` | Offers to `brew install pipx` first |
| Linux / no Homebrew | Dedicated venv at `~/.local/share/newsroom/venv` |

### Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| [Ollama](https://ollama.ai) | any | Local AI summarisation |
| A pulled Ollama model | — | e.g. `llama3.2`, `mistral`, `qwen2.5` |

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (one-time)
ollama pull llama3.2
```

### Manual install with pipx

If you prefer to install manually (recommended on macOS):

```bash
# Install pipx if needed
brew install pipx   # macOS
# or: pip install --user pipx

pipx install "git+https://github.com/mai-space/rss-ollama-news-cli.git"
```

---

## Usage

### Interactive TUI (default)

```bash
news
```

```
┌────────────────────────────────────────────────────────────────────────────┐
│  📰 Newsroom                                       RSS · AI · Terminal     │
├─────────────────┬──────────────────────────────────────────────────────────┤
│ SOURCES         │    Title                        Source        Published  │
│                 │  ─────────────────────────────────────────────────────── │
│ All Feeds       │ ● CSS Grid tips & tricks        CSS-Tricks    Jun 15 12  │
│                 │ ◌ TypeScript 5.5 released       TS Blog       Jun 15 11  │
│  UI/UX          │ ○ TYPO3 13.4 LTS announced      TYPO3 News    Jun 15 10  │
│    Smashing Mag │ ✗ Error fetching article        PHP.Watch     Jun 15 09  │
│    Nielsen NN   │                                                           │
│  TECH           ├──────────────────────────────────────────────────────────┤
│    web.dev      │ CSS Grid tips & tricks — CSS-Tricks                       │
│    GitHub Blog  │                                                           │
│  AI             │ • Grid layout is now supported in all major browsers      │
│    MIT Tech Rev │ • subgrid enables alignment across nested elements        │
│    Hugging Face │ • container queries complement grid for responsive design  │
│                 │                                                           │
├─────────────────┴──────────────────────────────────────────────────────────┤
│ [q] Quit  [r] Refresh  [o] Open URL  [e] Email  [Tab] Navigate             │
└────────────────────────────────────────────────────────────────────────────┘
```

### TUI Keyboard Shortcuts

| Key | Action |
|---|---|
| `q` | Quit |
| `r` | Refresh all feeds |
| `o` | Open selected article in browser |
| `e` | Send email digest |
| `↑` / `↓` | Navigate articles |
| `Tab` / `Shift+Tab` | Switch panel focus (sources ↔ articles) |
| `?` | Show keyboard help in status bar |

### CLI Commands

```bash
# Digest
news digest                          # Print text digest to stdout
news digest --output digest.txt      # Save to file
news digest --email                  # Generate + email the digest
news digest --no-ai                  # Skip AI summaries (fast)

# Feed management
news feeds list                      # Show all feeds with status
news feeds add "My Blog" https://myblog.com/feed.xml --category Tech
news feeds remove "My Blog"
news feeds toggle "Hacker News"      # Enable / disable

# Configuration
news config show                     # Print full config JSON
news config set ollama.model mistral
news config set ollama.base_url http://192.168.1.5:11434
news config set display.max_articles_per_feed 15

# Email
news config email \
  --smtp-host smtp.gmail.com \
  --username me@gmail.com \
  --password "my-app-password" \
  --to newsletter@example.com \
  --enable
```

---

## Default Feed Sources

| Category | Source |
|---|---|
| UI/UX | Smashing Magazine, Nielsen Norman Group, UX Collective |
| CSS | CSS-Tricks |
| JavaScript | JavaScript Weekly, TypeScript Blog |
| Tech | web.dev, Mozilla Hacks, GitHub Blog, Hacker News |
| AI | MIT Technology Review, Hugging Face Blog |
| PHP | PHP.Watch, Laravel News |
| TYPO3 | TYPO3 News |
| SQL | SQL Performance |

---

## Configuration Reference

Config file: `~/.config/newsroom/config.json`

```jsonc
{
  "feeds": [
    { "name": "CSS-Tricks", "url": "https://css-tricks.com/feed/", "category": "CSS", "enabled": true }
    // … more feeds
  ],
  "ollama": {
    "model": "llama3.2",              // any model you have pulled
    "base_url": "http://localhost:11434",
    "prompt": "Summarize the following article in 3-5 bullet points starting with '•'.\n\nArticle:\n{content}",
    "max_tokens": 500,
    "timeout": 120
  },
  "email": {
    "enabled": false,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": true,
    "username": "",
    "password": "",                   // use an App Password for Gmail
    "from_addr": "",
    "to_addrs": [],
    "subject_template": "📰 Newsroom Digest — {date}"
  },
  "display": {
    "max_articles_per_feed": 10,
    "max_total_articles": 60,
    "date_format": "%b %d %H:%M"
  }
}
```

### Email on a Server

To run Newsroom as a scheduled digest sender (e.g. via cron):

```bash
# Edit crontab
crontab -e

# Send digest every weekday morning at 07:30
30 7 * * 1-5 /usr/local/bin/news digest --email >> ~/.local/share/newsroom/logs/cron.log 2>&1
```

---

## Development

```bash
git clone https://github.com/mai-space/rss-ollama-news-cli.git
cd rss-ollama-news-cli
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check src/ tests/
ruff format src/ tests/
```

### Project Structure

```
src/newsroom/
├── cli.py          # Typer CLI entry point
├── config.py       # Pydantic config model + default feeds
├── feeds.py        # Async RSS fetching (httpx + feedparser)
├── summarizer.py   # Ollama async client
├── mailer.py       # HTML + plain-text email digest
├── logger.py       # File logger (~/.local/share/newsroom/logs/)
└── tui/
    ├── __init__.py
    └── app.py      # Textual three-pane TUI app

tests/
├── conftest.py
├── test_config.py
├── test_feeds.py
├── test_summarizer.py
└── test_mailer.py
```

---

## Status Icons

| Icon | Meaning |
|---|---|
| `○` | Summary pending |
| `◌` | Generating summary… |
| `●` | Summary ready |
| `✗` | Summary failed (check logs) |

---

## License

MIT — see [LICENSE](LICENSE).
