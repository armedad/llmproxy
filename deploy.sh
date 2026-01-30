#!/bin/bash
# LLM Proxy - Deploy script
# Deploys LLM Proxy to a target directory for Mac or Windows

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

show_help() {
    cat << 'EOF'
LLM Proxy - Deploy Script

USAGE:
    ./deploy.sh <target_path> <platform>

ARGUMENTS:
    target_path     Directory to deploy to (will be created if needed)
    platform        Target platform: "mac" or "windows"

EXAMPLES:
    ./deploy.sh ~/tools/llm-proxy mac
    ./deploy.sh /opt/llm-proxy mac
    ./deploy.sh C:\tools\llm-proxy windows

WHAT GETS DEPLOYED:
    - run.py (entry point)
    - app/ (Python source)
    - static/ (web UI)
    - config.json (default configuration)
    - requirements.txt (dependencies)
    - README.md (documentation)
    - Platform-specific launcher (llmproxy.sh or llmproxy.bat)

NOTES:
    - The logs/ directory is NOT copied (created at runtime)
    - Existing files in target directory will be overwritten
    - Python 3.9+ must be installed on the target machine

EOF
}

if [ "$1" == "--help" ] || [ "$1" == "-h" ] || [ -z "$1" ] || [ -z "$2" ]; then
    show_help
    exit 0
fi

TARGET_PATH="$1"
PLATFORM="$2"

# Validate platform
if [ "$PLATFORM" != "mac" ] && [ "$PLATFORM" != "windows" ]; then
    echo "Error: Platform must be 'mac' or 'windows'"
    echo "Use --help for usage information"
    exit 1
fi

echo "Deploying LLM Proxy..."
echo "  Source: $SCRIPT_DIR"
echo "  Target: $TARGET_PATH"
echo "  Platform: $PLATFORM"
echo ""

# Create target directory
mkdir -p "$TARGET_PATH"

# Copy core files
echo "Copying core files..."
cp "$SCRIPT_DIR/run.py" "$TARGET_PATH/"
cp "$SCRIPT_DIR/requirements.txt" "$TARGET_PATH/"
cp "$SCRIPT_DIR/config.json" "$TARGET_PATH/"
cp "$SCRIPT_DIR/README.md" "$TARGET_PATH/"

# Copy app directory
echo "Copying app directory..."
rm -rf "$TARGET_PATH/app"
cp -r "$SCRIPT_DIR/app" "$TARGET_PATH/"

# Copy static directory
echo "Copying static directory..."
rm -rf "$TARGET_PATH/static"
cp -r "$SCRIPT_DIR/static" "$TARGET_PATH/"

# Create logs directory
mkdir -p "$TARGET_PATH/logs"

# Copy platform-specific launcher
if [ "$PLATFORM" == "mac" ]; then
    echo "Copying Mac launcher..."
    cp "$SCRIPT_DIR/llmproxy.sh" "$TARGET_PATH/"
    chmod +x "$TARGET_PATH/llmproxy.sh"
    echo ""
    echo "✓ Deployed to $TARGET_PATH"
    echo ""
    echo "To run:"
    echo "  cd $TARGET_PATH"
    echo "  ./llmproxy.sh --install  # first time only"
    echo "  ./llmproxy.sh"
else
    echo "Copying Windows launcher..."
    cp "$SCRIPT_DIR/llmproxy.bat" "$TARGET_PATH/"
    echo ""
    echo "✓ Deployed to $TARGET_PATH"
    echo ""
    echo "To run:"
    echo "  cd $TARGET_PATH"
    echo "  llmproxy.bat --install  (first time only)"
    echo "  llmproxy.bat"
fi

echo ""
echo "Then open http://localhost:8000 in your browser."
