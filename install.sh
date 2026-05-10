#!/usr/bin/env bash
# Newsroom — one-line installer / updater
# Usage: curl -fsSL https://raw.githubusercontent.com/mai-space/rss-ollama-news-cli/main/install.sh | bash

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; }
info() { echo -e "  ${BLUE}ℹ${NC}  $*"; }

echo ""
echo -e "${BLUE}${BOLD}  📰 Newsroom Installer${NC}"
echo -e "${DIM}  RSS feeds + AI summaries in your terminal${NC}"
echo -e "  ${DIM}──────────────────────────────────────────${NC}"
echo ""

# ── Check Python ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  err "Python 3 not found."
  info "Install Python 3.11+ from https://python.org"
  exit 1
fi

PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_VER="${PY_MAJOR}.${PY_MINOR}"

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ]]; then
  err "Python 3.11+ required — found ${PY_VER}"
  info "Upgrade from https://python.org"
  exit 1
fi
ok "Python ${PY_VER}"

# ── Check pip ─────────────────────────────────────────────────────────────────
if ! python3 -m pip --version &>/dev/null; then
  err "pip not found."
  info "Fix with: python3 -m ensurepip --upgrade"
  exit 1
fi
ok "pip available"

# ── Check Ollama ─────────────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
  OLLAMA_VER=$(ollama --version 2>/dev/null | head -1 || echo "unknown version")
  ok "Ollama — ${OLLAMA_VER}"
else
  warn "Ollama not found (required for AI summaries)."
  echo ""
  echo -e "  ${YELLOW}Install Ollama:${NC}"
  echo -e "    ${DIM}curl -fsSL https://ollama.ai/install.sh | sh${NC}"
  echo -e "    ${DIM}ollama pull llama3.2${NC}"
  echo ""
  read -r -p "  Continue without Ollama? [y/N] " REPLY
  echo
  [[ "$REPLY" =~ ^[Yy]$ ]] || exit 1
fi

# ── Install / upgrade Newsroom ────────────────────────────────────────────────
echo ""
echo -e "  ${BLUE}Installing Newsroom…${NC}"

REPO="https://github.com/mai-space/rss-ollama-news-cli"

if python3 -m pip install --quiet --upgrade "rss-ollama-news-cli @ git+${REPO}.git" 2>&1; then
  ok "Newsroom installed"
else
  err "pip install failed — trying with --user flag…"
  python3 -m pip install --quiet --user --upgrade "rss-ollama-news-cli @ git+${REPO}.git" || {
    err "Installation failed."
    info "Try manually: pip install git+${REPO}.git"
    exit 1
  }
  ok "Newsroom installed (user-local)"
fi

# ── Verify the command is on PATH ─────────────────────────────────────────────
if ! command -v news &>/dev/null; then
  LOCAL_BIN="$HOME/.local/bin"
  warn "'news' not found in PATH."
  echo ""
  echo -e "  Add ${BOLD}~/.local/bin${NC} to your PATH:"
  echo ""
  echo -e "    ${DIM}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc${NC}"
  echo -e "    ${DIM}source ~/.bashrc${NC}"
  echo ""
  echo -e "  ${DIM}(For zsh, replace .bashrc with .zshrc)${NC}"
else
  NEWS_VER=$(news --version 2>/dev/null || echo "installed")
  ok "'news' command ready — ${NEWS_VER}"
fi

# ── Usage summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${DIM}1.  Start Ollama:        ollama serve${NC}"
echo -e "    ${DIM}2.  Pull a model:        ollama pull llama3.2${NC}"
echo -e "    ${DIM}3.  Launch Newsroom:     news${NC}"
echo ""
echo -e "  ${BOLD}Commands:${NC}"
echo -e "    ${BLUE}news${NC}                       Launch interactive TUI"
echo -e "    ${BLUE}news digest${NC}                Print a text digest"
echo -e "    ${BLUE}news digest --email${NC}        Email the digest"
echo -e "    ${BLUE}news feeds list${NC}            Show configured feeds"
echo -e "    ${BLUE}news feeds add NAME URL${NC}    Add a feed"
echo -e "    ${BLUE}news config show${NC}           View configuration"
echo -e "    ${BLUE}news config set KEY VALUE${NC}  Change a setting"
echo ""
echo -e "  ${DIM}Config: ~/.config/newsroom/config.json${NC}"
echo -e "  ${DIM}Logs:   ~/.local/share/newsroom/logs/newsroom.log${NC}"
echo ""
