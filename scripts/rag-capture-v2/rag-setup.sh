#!/bin/bash
# rag-setup.sh — Install rag_capture.py as global 'rag' CLI command
# Run once: bash rag-setup.sh
# Works on: Ubuntu/Debian, macOS, WSL, Git Bash (Windows)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/rag_capture.py"

echo "🔧 RAG Capture CLI — Setup"
echo "   Source: $SOURCE"
echo ""

# Check Python
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYTHON" ]; then
    echo "❌ Python 3 not found."
    exit 1
fi

PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
echo "   Python: $PY_VER"

if [ "$PY_MINOR" -lt 8 ]; then
    echo "❌ Python 3.8+ required."
    exit 1
fi

# Detect install target
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    INSTALL_TARGET="/usr/local/bin/rag"
elif [ -d "$HOME/.local/bin" ]; then
    INSTALL_TARGET="$HOME/.local/bin/rag"
    mkdir -p "$HOME/.local/bin"
else
    INSTALL_TARGET="$HOME/bin/rag"
    mkdir -p "$HOME/bin"
fi

# Install
cp "$SOURCE" "$INSTALL_TARGET"
chmod +x "$INSTALL_TARGET"

# Fix shebang to use detected python
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "1s|.*|#!$PYTHON|" "$INSTALL_TARGET"
else
    sed -i "1s|.*|#!$PYTHON|" "$INSTALL_TARGET"
fi

echo "   Installed: $INSTALL_TARGET"

# Global config
CONFIG_PATH="$HOME/.rag_config.json"
if [ ! -f "$CONFIG_PATH" ]; then
    cat > "$CONFIG_PATH" << 'EOF'
{
  "qdrant_collection": "knowledge_v2",
  "qdrant_url": "http://192.168.18.199:6333",
  "author": "Figur Ulul Azmi",
  "default_environment": "dev",
  "default_chunk_source": "code",
  "push_script": "~/scripts/push-to-qdrant.sh",
  "summaries_subdir": ".claude/summaries",
  "projects": {
    "petrochina-eproc": {
      "default_environment": "dev",
      "default_branch": "feature/",
      "tags_preset": ["petrochina", "eproc"]
    },
    "homelab": {
      "default_environment": "homelab",
      "default_branch": "main",
      "tags_preset": ["homelab", "vm-b1"]
    },
    "mit-internal": {
      "default_environment": "dev",
      "default_branch": "main",
      "tags_preset": ["mit"]
    },
    "homeplate": {
      "default_environment": "dev",
      "default_branch": "feature/",
      "tags_preset": ["homeplate", "saas"]
    }
  }
}
EOF
    echo "   Config created: $CONFIG_PATH"
else
    echo "   Config exists: $CONFIG_PATH (unchanged)"
fi

# PATH check
if ! echo "$PATH" | grep -q "$(dirname "$INSTALL_TARGET")"; then
    echo ""
    echo "⚠️  Add this to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"$(dirname "$INSTALL_TARGET"):\$PATH\""
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Quick test:"
echo "   rag --help"
echo "   rag status"
echo ""
echo "Quick start:"
echo "   rag add -p petrochina-eproc -t debug --topic 'My fix' --tags 'tag1,tag2'"
echo "   rag list"
echo "   rag merge --output 2026-04-14-session.md"
echo "   rag remind"