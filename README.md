# LLM Proxy

A local proxy server for observing and debugging OpenAI API calls.

## What It Does

- Sits between your apps and OpenAI's API
- Logs every request and response (including streaming)
- Web UI to browse and inspect request history
- See exact prompts, token usage, timing, and errors
- Disk logging in JSONL format for later analysis

## Quick Start

```bash
pip3 install -r requirements.txt
python3 run.py
```

Open **http://localhost:8000** for the web UI.

## Configure Your App

Point your app's OpenAI base URL to `http://localhost:8000` instead of `https://api.openai.com`.

### OpenAI-compatible IDE or client

In your IDE or client settings, set the OpenAI base URL (or API endpoint) to `http://localhost:8000`. Many tools expose this under Models, API, or Provider settings.

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"
)
```

### OpenAI Node SDK

```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
    baseURL: 'http://localhost:8000/v1',
    apiKey: 'your-api-key'
});
```

### curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## Configuration

Edit `config.json`:

```json
{
  "port": 8000,
  "openai_base_url": "https://api.openai.com",
  "api_key_override": null,
  "log_dir": "./logs",
  "max_memory_requests": 1000,
  "log_request_bodies": true,
  "log_response_bodies": true
}
```

| Option | Description |
|--------|-------------|
| `port` | Local port for the proxy (default: 8000) |
| `openai_base_url` | Where to forward requests (default: OpenAI) |
| `api_key_override` | If set, uses this key instead of client's key |
| `log_dir` | Where to store request logs |
| `max_memory_requests` | How many requests to keep in memory for the UI |
| `log_request_bodies` | Set to `false` to disable logging request bodies |
| `log_response_bodies` | Set to `false` to disable logging response bodies |

### Environment Variables

Environment variables override config file:

- `LLM_PROXY_PORT` - Port number
- `LLM_PROXY_OPENAI_URL` - OpenAI base URL
- `LLM_PROXY_API_KEY` - API key override

## Web UI Features

- **Request list** - See all proxied requests with timestamp, method, path, model, status, duration, and token count
- **Request detail** - Click any request to see full headers, request body, and response body
- **Filtering** - Filter by endpoint, model, or status (success/error)
- **Auto-refresh** - Toggle to poll for new requests every 2 seconds
- **Copy buttons** - One-click copy of request/response data
- **Keyboard shortcuts** - Press `R` to refresh, `Esc` to close detail panel

## Logs

Requests are logged to `logs/requests-YYYY-MM-DD.jsonl` (one JSON object per line).

Example log entry:

```json
{
  "id": "abc123",
  "timestamp": "2026-01-30T12:00:00.000Z",
  "method": "POST",
  "path": "/v1/chat/completions",
  "request_body": {"model": "gpt-4o", "messages": [...]},
  "response_status": 200,
  "response_body": {"choices": [...]},
  "duration_ms": 1234.5,
  "model": "gpt-4o",
  "tokens": {"prompt": 10, "completion": 20, "total": 30}
}
```

## Security Notes

- **API keys are sanitized** in logs - only the last 4 characters are shown
- **Binds to localhost only** by default (127.0.0.1)
- **No authentication** on the web UI - this is a local dev tool

## Supported Endpoints

The proxy forwards any `/v1/*` request to OpenAI, including:

- `/v1/chat/completions` (streaming and non-streaming)
- `/v1/completions`
- `/v1/embeddings`
- `/v1/models`
- Any other OpenAI API endpoint

## Troubleshooting

### Port already in use

```bash
lsof -ti:8000 | xargs kill -9
```

### App not connecting

Make sure your app supports custom base URLs. Some apps hardcode `api.openai.com`.

### Streaming not working

Check that your app sends `"stream": true` in the request body. The proxy detects this and enables SSE passthrough.
