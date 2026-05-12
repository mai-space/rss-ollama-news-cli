#!/usr/bin/env bash
# Newsroom — one-line installer / updater
# Stable:  curl -fsSL https://raw.githubusercontent.com/mai-space/rss-ollama-news-cli/main/install.sh | bash
# Dev:     curl -fsSL "https://raw.githubusercontent.com/mai-space/rss-ollama-news-cli/claude/cli-newsletter-rss-ai-heER5/install.sh" | bash

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; }
info() { echo -e "  ${BLUE}ℹ${NC}  $*"; }

# When the script is piped to bash (curl … | bash), bash and the built-in
# 'read' share the same stdin (the pipe).  If 'read' pulls from that pipe it
# consumes lines of the script itself, causing bash to skip or misparse them.
# Fix: always read interactive input from /dev/tty; fall back to the default
# answer when no controlling terminal is available (CI, Docker, etc.).
ask() {
  local prompt="$1" default="$2"
  if [ -c /dev/tty ] && [ -r /dev/tty ]; then
    if ! read -r -p "  ${prompt} " REPLY </dev/tty; then
      REPLY=""
    fi
  else
    REPLY=""
  fi
  # If nothing was entered, use the supplied default character
  [[ -z "$REPLY" ]] && REPLY="$default"
}

echo ""
echo -e "${BLUE}${BOLD}  📰 Newsroom Installer${NC}"
echo -e "${DIM}  RSS feeds + AI summaries in your terminal${NC}"
echo -e "  ${DIM}──────────────────────────────────────────${NC}"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
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

# ── Check Ollama ──────────────────────────────────────────────────────────────
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
  ask "Continue without Ollama? [y/N]" "N"
  echo
  [[ "$REPLY" =~ ^[Yy]$ ]] || exit 1
fi

# ── Package coordinates ───────────────────────────────────────────────────────
REPO="https://github.com/mai-space/rss-ollama-news-cli"
# Pin to the branch this script ships on; update to @main after merge.
BRANCH="claude/cli-newsletter-rss-ai-heER5"
GIT_URL="${REPO}.git@${BRANCH}"

echo ""
echo -e "  ${BLUE}Installing Newsroom…${NC}"

# ── Strategy 1: pipx ─────────────────────────────────────────────────────────
# pipx is the recommended way to install Python CLI tools — it creates an
# isolated venv automatically and puts the binary on PATH. On macOS with
# Homebrew Python (PEP 668) this is the only clean path.
if command -v pipx &>/dev/null; then
  if pipx install "git+${GIT_URL}" --force 2>&1; then
    ok "Newsroom installed via pipx"
    INSTALLED_VIA="pipx"
  else
    warn "pipx install failed (ensurepip unavailable? e.g. Homebrew Python 3.14+)."
    info "Falling back to isolated venv install…"
    INSTALLED_VIA="venv"
  fi

# ── Strategy 2: offer to install pipx, then retry ────────────────────────────
elif command -v brew &>/dev/null; then
  warn "pipx not found. It is the recommended installer for CLI tools on macOS."
  echo ""
  ask "Install pipx via Homebrew now? [Y/n]" "Y"
  echo
  if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then
    brew install pipx --quiet
    pipx ensurepath --quiet
    export PATH="${HOME}/.local/bin:${PATH}"
    if pipx install "git+${GIT_URL}" --force 2>&1; then
      ok "Newsroom installed via pipx"
      INSTALLED_VIA="pipx"
    else
      warn "pipx install failed — falling back to isolated venv install…"
      INSTALLED_VIA="venv"
    fi
  else
    # Fall through to venv strategy
    INSTALLED_VIA="venv"
  fi

# ── Strategy 3: dedicated venv (Linux / no Homebrew) ─────────────────────────
else
  INSTALLED_VIA="venv"
fi

if [[ "${INSTALLED_VIA:-venv}" == "venv" ]]; then
  VENV_DIR="${HOME}/.local/share/newsroom/venv"
  BIN_DIR="${HOME}/.local/bin"

  info "Creating isolated venv at ${VENV_DIR}"
  mkdir -p "${BIN_DIR}"

  # Some Python distributions (e.g. Homebrew Python 3.14+) ship without
  # ensurepip, which causes `python3 -m venv` to fail.  Fall back to
  # --without-pip and bootstrap pip via get-pip.py in that case.
  if ! python3 -m venv "${VENV_DIR}" --clear 2>/dev/null; then
    python3 -m venv "${VENV_DIR}" --clear --without-pip
    info "Bootstrapping pip (ensurepip unavailable)…"
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | "${VENV_DIR}/bin/python3" - --quiet
  fi

  "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
  "${VENV_DIR}/bin/pip" install --quiet "rss-ollama-news-cli @ git+${GIT_URL}"

  # Write a thin wrapper so 'news' works from any shell
  cat > "${BIN_DIR}/news" <<WRAPPER
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/news" "\$@"
WRAPPER
  chmod +x "${BIN_DIR}/news"
  ok "Newsroom installed (${VENV_DIR})"
fi

# ── Verify 'news' is reachable ────────────────────────────────────────────────
# Reload PATH in case pipx/pipx ensurepath just modified it
export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v news &>/dev/null; then
  warn "'news' not yet on PATH."
  echo ""
  echo -e "  Add ${BOLD}~/.local/bin${NC} to your shell's PATH:"
  echo ""
  echo -e "    ${DIM}# bash${NC}"
  echo -e "    ${DIM}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${NC}"
  echo ""
  echo -e "    ${DIM}# zsh${NC}"
  echo -e "    ${DIM}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc${NC}"
  echo ""
else
  ok "'news' command is ready"
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
