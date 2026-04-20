#!/usr/bin/env bash
# =============================================================================
# install.sh — RAG Pipeline one-command setup
# Usage : bash install.sh
#         bash install.sh --update   (re-run after git pull)
#         bash install.sh --check    (health check only)
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$HOME/scripts"
CONFIG_DIR="$HOME/.config"
UPDATE_MODE=false
CHECK_MODE=false

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { printf "${GREEN}  [OK]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}  [!!]${NC} %s\n" "$1"; }
info() { printf "${CYAN}  [--]${NC} %s\n" "$1"; }
fail() { printf "${RED}  [XX]${NC} %s\n" "$1"; }

# =============================================================================
# ARGS
# =============================================================================

for arg in "$@"; do
  case "$arg" in
    --update) UPDATE_MODE=true ;;
    --check)  CHECK_MODE=true ;;
  esac
done

# =============================================================================
# DETECT OS
# =============================================================================

detect_os() {
  case "$(uname -s)" in
    MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
    Linux*)                echo "linux" ;;
    Darwin*)               echo "mac" ;;
    *)                     echo "unknown" ;;
  esac
}

OS=$(detect_os)

# =============================================================================
# HEALTH CHECK MODE
# =============================================================================

if [[ "$CHECK_MODE" == true ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  RAG Pipeline Health Check"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Load env
  _RAG_ENV="$CONFIG_DIR/rag-gateway.env"
  [ -f "$_RAG_ENV" ] && source "$_RAG_ENV"
  RAG_BASE_URL="${RAG_BASE_URL:-http://192.168.18.199:5200}"

  command -v curl &>/dev/null   && ok "curl installed"   || fail "curl missing"
  command -v jq &>/dev/null     && ok "jq installed"     || fail "jq missing"
  command -v python3 &>/dev/null && ok "python3 installed" || warn "python3 missing (rag add won't work)"
  [ -f "$SCRIPTS_DIR/rag" ]           && ok "~/scripts/rag installed"              || fail "~/scripts/rag missing — run install.sh"
  [ -f "$SCRIPTS_DIR/push-to-qdrant.sh" ] && ok "~/scripts/push-to-qdrant.sh installed" || fail "push-to-qdrant.sh missing"
  [ -f "$CONFIG_DIR/qdrant-knowledge.env" ] && ok "~/.config/qdrant-knowledge.env exists" || warn "qdrant-knowledge.env missing — rag add won't push"
  [ -f "$_RAG_ENV" ] && ok "~/.config/rag-gateway.env exists (RAG_BASE_URL=${RAG_BASE_URL})" || warn "rag-gateway.env missing — using fallback ${RAG_BASE_URL}"

  echo ""
  info "Testing RAG Gateway at ${RAG_BASE_URL} ..."
  if curl -s --connect-timeout 4 "${RAG_BASE_URL}/health" -o /dev/null 2>/dev/null; then
    ok "RAG Gateway reachable"
  else
    fail "RAG Gateway unreachable at ${RAG_BASE_URL}"
    echo "     Fix: check VM B1 status or set RAG_BASE_URL in ~/.config/rag-gateway.env"
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
fi

# =============================================================================
# BANNER
# =============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$UPDATE_MODE" == true ]]; then
  echo "  RAG Pipeline Update"
else
  echo "  RAG Pipeline Setup"
fi
echo "  OS: $OS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# =============================================================================
# STEP 1 — Create ~/scripts
# =============================================================================

echo "[ Step 1 ] Setting up ~/scripts ..."
mkdir -p "$SCRIPTS_DIR"
ok "~/scripts directory ready"

# =============================================================================
# STEP 2 — Copy scripts
# =============================================================================

echo ""
echo "[ Step 2 ] Installing scripts ..."

cp "$REPO_ROOT/scripts/rag" "$SCRIPTS_DIR/rag"
chmod +x "$SCRIPTS_DIR/rag"
ok "~/scripts/rag installed"

cp "$REPO_ROOT/scripts/push-to-qdrant.sh" "$SCRIPTS_DIR/push-to-qdrant.sh"
chmod +x "$SCRIPTS_DIR/push-to-qdrant.sh"
ok "~/scripts/push-to-qdrant.sh installed"

# Copy rag-capture-v2 if python3 available
if command -v python3 &>/dev/null; then
  mkdir -p "$SCRIPTS_DIR/rag-capture-v2"
  cp -r "$REPO_ROOT/scripts/rag-capture-v2/." "$SCRIPTS_DIR/rag-capture-v2/"
  ok "~/scripts/rag-capture-v2/ installed"

  if python3 -c "import pip" &>/dev/null 2>&1; then
    python3 -m pip install --quiet pyyaml requests 2>/dev/null && ok "Python deps installed (pyyaml, requests)" || warn "pip install failed — install manually: pip install pyyaml requests"
  else
    warn "pip not found — install manually: pip install pyyaml requests"
  fi
else
  warn "python3 not found — rag-capture-v2 skipped (rag add/merge won't work)"
fi

# =============================================================================
# STEP 3 — PATH setup
# =============================================================================

echo ""
echo "[ Step 3 ] Setting up PATH ..."

SHELL_RC=""
if [[ "$OS" == "windows" ]]; then
  SHELL_RC="$HOME/.bashrc"
elif [[ -f "$HOME/.zshrc" ]]; then
  SHELL_RC="$HOME/.zshrc"
else
  SHELL_RC="$HOME/.bashrc"
fi

PATH_LINE='export PATH="$PATH:$HOME/scripts"'

if ! grep -qF 'PATH.*scripts' "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# RAG Pipeline scripts" >> "$SHELL_RC"
  echo "$PATH_LINE" >> "$SHELL_RC"
  ok "Added ~/scripts to PATH in $SHELL_RC"
else
  ok "~/scripts already in PATH ($SHELL_RC)"
fi

# =============================================================================
# STEP 4 — RAG Gateway URL config
# =============================================================================

echo ""
echo "[ Step 4 ] RAG Gateway URL ..."
mkdir -p "$CONFIG_DIR"

RAG_ENV_FILE="$CONFIG_DIR/rag-gateway.env"

if [[ "$UPDATE_MODE" == true ]] && [[ -f "$RAG_ENV_FILE" ]]; then
  source "$RAG_ENV_FILE"
  ok "Keeping existing RAG_BASE_URL=${RAG_BASE_URL}"
else
  echo ""
  echo "  VM B1 IPs:"
  echo "    LAN       : 192.168.18.199:5200 (office network)"
  echo "    Tailscale : 100.120.249.99:5200 (remote access)"
  echo ""
  echo "  Press ENTER to use auto-detect (tries LAN -> Tailscale),"
  echo "  or enter a custom URL:"
  read -r -p "  RAG_BASE_URL [auto-detect]: " RAG_URL_INPUT

  if [[ -z "$RAG_URL_INPUT" ]]; then
    # Auto-detect at runtime — leave env file empty so script falls back to its own detection
    cat > "$RAG_ENV_FILE" <<'EOF'
# RAG Gateway URL — set this if auto-detect doesn't work
# RAG_BASE_URL=http://192.168.18.199:5200    # LAN
# RAG_BASE_URL=http://100.120.249.99:5200    # Tailscale
# RAG_BASE_URL=http://localhost:5200         # local dev
EOF
    ok "Using auto-detect (VM B1 LAN -> Tailscale fallback)"
  else
    echo "RAG_BASE_URL=${RAG_URL_INPUT}" > "$RAG_ENV_FILE"
    ok "RAG_BASE_URL=${RAG_URL_INPUT} saved to ${RAG_ENV_FILE}"
  fi
fi

# =============================================================================
# STEP 5 — Qdrant API Key
# =============================================================================

echo ""
echo "[ Step 5 ] Qdrant API key ..."

QDRANT_ENV_FILE="$CONFIG_DIR/qdrant-knowledge.env"

if [[ -f "$QDRANT_ENV_FILE" ]]; then
  ok "~/.config/qdrant-knowledge.env already exists — skipping"
else
  echo ""
  read -r -s -p "  Enter QDRANT_API_KEY (input hidden): " QDRANT_KEY_INPUT
  echo ""

  if [[ -n "$QDRANT_KEY_INPUT" ]]; then
    echo "QDRANT_API_KEY=${QDRANT_KEY_INPUT}" > "$QDRANT_ENV_FILE"
    chmod 600 "$QDRANT_ENV_FILE"
    ok "Saved to ~/.config/qdrant-knowledge.env (mode 600)"
  else
    warn "Skipped — create manually: echo 'QDRANT_API_KEY=xxx' > ~/.config/qdrant-knowledge.env"
  fi
fi

# =============================================================================
# STEP 6 — Claude Code MCP (instructions only — platform-specific)
# =============================================================================

echo ""
echo "[ Step 6 ] Claude Code MCP setup ..."
echo ""

if [[ "$OS" == "windows" ]]; then
  info "Windows detected — MCP needs PowerShell SSH bridge."
  echo ""
  echo "  1. Copy MCP connect script:"
  echo "     cp scripts/claude-mcp-connect.ps1.template ~/.claude/claude-mcp-connect.ps1"
  echo "     (edit B1_LOCAL_IP / B1_TAILSCALE_IP / USER if different)"
  echo ""
  echo "  2. Copy Claude settings (includes mcpServers entry):"
  echo "     Get settings.json from the original device:"
  echo "     scp <original-device>:~/.claude/settings.json ~/.claude/settings.json"
  echo "     -- OR -- add this block manually to ~/.claude/settings.json:"
  cat <<'EOF'
  "mcpServers": {
    "qdrant-knowledge": {
      "command": "powershell",
      "args": ["-ExecutionPolicy", "Bypass", "-File", "C:\\Users\\<YOU>\\.claude\\claude-mcp-connect.ps1"]
    }
  }
EOF
else
  info "Linux/Mac detected — MCP uses SSH stdio bridge."
  echo ""
  echo "  Add to ~/.claude/settings.json:"
  cat <<'EOF'
  {
    "mcpServers": {
      "qdrant-knowledge": {
        "command": "ssh",
        "args": [
          "-o", "StrictHostKeyChecking=no",
          "-o", "BatchMode=yes",
          "figulazmi@192.168.18.199",
          "set -a; . ~/.qdrant-mcp.env; set +a; node /opt/mcp-servers/qdrant-knowledge/qdrant-mcp-server.js"
        ]
      }
    }
  }
EOF
fi

echo ""
echo "  Then verify: claude mcp list"
echo ""
warn "MCP must be configured manually — values are machine-specific"

# =============================================================================
# DONE
# =============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Next steps:"
echo "  1. Reload shell:  source ${SHELL_RC}"
echo "  2. Health check:  bash install.sh --check"
echo "  3. Test search:   rag \"how does qdrant work\" -p homelab"
echo ""
echo "  To update after git pull:"
echo "  bash install.sh --update"
echo ""
