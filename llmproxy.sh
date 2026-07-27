#!/bin/bash
# LLM Proxy - Mac/Linux launcher

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    cat << 'EOF'
LLM Proxy - Local OpenAI API debugging proxy

USAGE:
    ./llmproxy.sh [OPTIONS]

OPTIONS:
    --help, -h      Show this help message
    --port PORT     Override the default port (default: 8000)
    --install       Install Python dependencies

DESCRIPTION:
    LLM Proxy sits between your apps and OpenAI's API, letting you observe
    and debug actual API calls. It logs requests/responses and provides a
    web UI for inspection.

QUICK START:
    1. Start the proxy:
       ./llmproxy.sh

    2. Open the web UI:
       http://localhost:8000

    3. Configure your app to use the proxy as the OpenAI base URL:
       http://localhost:8000

CONFIGURING APPS:
    OpenAI-compatible IDE or client:
        Set the OpenAI base URL / API endpoint to http://localhost:8000

    OpenAI Python SDK:
        client = OpenAI(base_url="http://localhost:8000/v1", api_key="...")

    curl:
        curl http://localhost:8000/v1/chat/completions \
          -H "Authorization: Bearer sk-..." \
          -H "Content-Type: application/json" \
          -d '{"model": "gpt-4o", "messages": [...]}'

CONFIGURATION:
    Edit config.json to change settings:
    - port: Local port (default 8000)
    - api_key_override: Use a specific API key instead of client's
    - log_dir: Where to store request logs

LOGS:
    Request logs are saved to: logs/requests-YYYY-MM-DD.jsonl

MORE INFO:
    See README.md for full documentation.

EOF
}

install_deps() {
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo "Done!"
}

# Parse arguments
PORT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --install)
            install_deps
            exit 0
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    echo "Install Python 3.9+ and try again"
    exit 1
fi

# Check dependencies
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "Dependencies not installed. Run: ./llmproxy.sh --install"
    exit 1
fi

# Set port via environment if specified
if [ -n "$PORT" ]; then
    export LLM_PROXY_PORT="$PORT"
fi

# Run the proxy
exec python3 run.py
