# LLM Proxy - Opportunity Assessment

## Objective

Build a local proxy server that sits between apps and OpenAI's API, allowing observation and debugging of actual API calls. The tool enables reverse-engineering prompt strategies of third-party software and monitoring token usage across any app that supports custom OpenAI endpoints.

## Target Customer

Me - a developer who wants to:
- Understand how desktop apps and local web apps communicate with OpenAI
- See exactly what prompts are being sent
- Monitor token usage and costs
- Debug API errors and latency issues

## Success

1. Point an app's OpenAI base URL at the proxy and it "just works" - no behavior change for the app
2. Full visibility into every request/response, including streaming
3. Web UI makes it easy to browse and inspect request history
4. Disk logs capture everything for later analysis
5. Single command to run: `python run.py`

## What I Believe

- Many apps support custom OpenAI base URLs (most SDK-based apps and many IDEs do)
- Streaming (SSE) is the default for most AI apps - must work from day 1
- A local dev tool doesn't need auth, multi-user support, or cloud deployment
- Simple list-based UI is enough to start - can add dashboards later
- Generic passthrough is better than hardcoding specific endpoints

## What I Need to Research

- Exact request/response format for OpenAI's streaming API (SSE chunk structure)
- How to reassemble streaming chunks for logging while proxying in real-time
- Best minimal-decoration format for disk logs (probably JSONL or individual JSON files)

## Solution Directions

**Architecture:**
- Single Python process serving both proxy and web UI
- Routes:
  - `POST/GET /v1/*` → proxy to OpenAI API
  - `GET /` → web UI
  - `GET /api/requests` → fetch logged requests for UI

**Core features:**
- Generic passthrough proxy for all `/v1/*` endpoints
- Full streaming support (SSE passthrough + reassembly for logging)
- Logs: request payload, response, tokens, timing, model, headers, errors
- API key passthrough with optional override via config
- Web UI: chronological list, click to expand, basic filtering
- Disk logging with minimal decoration

**Tech stack:**
- Python (minimal dependencies)
- Vanilla JS frontend
- No database - in-memory + disk logs

**Endpoints to support (via generic passthrough):**
- `/v1/chat/completions` - primary
- `/v1/embeddings` - for semantic search
- `/v1/models` - model listing
- Any other `/v1/*` - future-proof

## Risks to Validate + How to Validate Cheaply/Quickly

| Risk | Validation |
|------|------------|
| Streaming proxy adds latency | Build minimal streaming proxy first, measure overhead |
| SSE reassembly is complex | Spike on chunk parsing before full implementation |
| Apps might not work with custom base URL | Test with an OpenAI-compatible client early in development |
| Disk logging format is awkward | Start with JSONL, iterate based on actual usage |

---

# Detailed Spec

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLM Proxy Server                         │
│                     (Single Python Process)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Web UI    │    │  Proxy API  │    │   Internal API      │ │
│  │   GET /     │    │  /v1/*      │    │   /api/*            │ │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘ │
│         │                  │                      │             │
│         │                  ▼                      │             │
│         │         ┌────────────────┐              │             │
│         │         │  Request       │              │             │
│         │         │  Logger        │◄─────────────┘             │
│         │         └───────┬────────┘                            │
│         │                 │                                     │
│         │                 ▼                                     │
│         │         ┌────────────────┐                            │
│         │         │  In-Memory     │                            │
│         │         │  Request Store │                            │
│         │         └───────┬────────┘                            │
│         │                 │                                     │
│         ▼                 ▼                                     │
│  ┌─────────────┐  ┌────────────────┐                            │
│  │ Static      │  │  Disk Logger   │                            │
│  │ Files       │  │  (JSONL)       │                            │
│  └─────────────┘  └────────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   OpenAI API    │
                    │ api.openai.com  │
                    └─────────────────┘
```

## Data Flow

### Non-Streaming Request (e.g., embeddings, models)
1. Client sends request to proxy (`POST /v1/embeddings`)
2. Proxy captures: timestamp, headers, full request body
3. Proxy forwards request to OpenAI (with passthrough or override API key)
4. OpenAI returns response
5. Proxy captures: response body, status code, timing
6. Proxy logs to memory + disk
7. Proxy returns response to client (unchanged)

### Streaming Request (chat completions with `stream: true`)
1. Client sends request to proxy (`POST /v1/chat/completions`)
2. Proxy captures: timestamp, headers, full request body
3. Proxy forwards request to OpenAI
4. OpenAI streams SSE chunks
5. Proxy:
   - Passes each chunk through to client immediately (no buffering delay)
   - Accumulates chunks in memory for logging
6. On stream end:
   - Reassembles full response from chunks
   - Extracts token usage from final chunk (if present) or estimates
   - Logs complete request/response to memory + disk
7. Client receives streamed response as if talking directly to OpenAI

## Core Components

### 1. HTTP Server
- Single async Python server (using `aiohttp` or similar minimal async library)
- Handles all routes:
  - `GET /` - serves web UI (static HTML/JS/CSS)
  - `ANY /v1/*` - proxy passthrough to OpenAI
  - `GET /api/requests` - returns logged requests for UI
  - `GET /api/requests/{id}` - returns single request detail

### 2. Proxy Handler
- Forwards any `/v1/*` request to `https://api.openai.com/v1/*`
- Preserves all headers except `Host` (rewritten for OpenAI)
- API key handling:
  - Default: pass through client's `Authorization` header
  - Override: if configured, replace with proxy's API key
- Streaming detection: check for `stream: true` in request body or `Accept: text/event-stream` header
- Error passthrough: return OpenAI errors to client unchanged

### 3. Request Logger
- Captures for every request:
  - `id`: unique identifier (UUID)
  - `timestamp`: ISO 8601
  - `method`: HTTP method
  - `path`: e.g., `/v1/chat/completions`
  - `request_headers`: dict (sanitize Authorization to show only last 4 chars)
  - `request_body`: full JSON body
  - `response_status`: HTTP status code
  - `response_headers`: dict
  - `response_body`: full response (reassembled if streaming)
  - `is_streaming`: boolean
  - `duration_ms`: total request time
  - `model`: extracted from request body if present
  - `tokens`: `{prompt, completion, total}` if available
  - `error`: error message if request failed

### 4. In-Memory Store
- Circular buffer of last N requests (configurable, default 1000)
- Provides fast access for UI
- Newest first ordering

### 5. Disk Logger
- Writes each request as a single line to `logs/requests.jsonl`
- Format: one JSON object per line, minimal whitespace
- Includes all fields from Request Logger
- File rotation: new file per day (`logs/requests-2026-01-30.jsonl`)

### 6. Web UI
- Single-page app served from `/`
- Static files: `index.html`, `app.js`, `styles.css`
- Features:
  - Request list (newest first)
  - Each row shows: timestamp, method, path, model, status, duration, token count
  - Click row to expand full request/response
  - Request detail view:
    - Collapsible sections for headers, request body, response body
    - JSON syntax highlighting (basic, CSS-based)
    - Copy buttons for request/response
  - Filtering:
    - By endpoint (dropdown or text filter)
    - By model
    - By status (success/error)
    - By time range (last hour, last day, all)
  - Auto-refresh toggle (poll every 2 seconds when enabled)
- No build step - vanilla JS, no bundler

### 7. Configuration
- Config file: `config.json` (optional, sensible defaults)
- Environment variables override config file
- Settings:
  - `port`: default 8000
  - `openai_base_url`: default `https://api.openai.com`
  - `api_key_override`: optional, if set replaces client's key
  - `log_dir`: default `./logs`
  - `max_memory_requests`: default 1000
  - `log_request_bodies`: default true (can disable for privacy)
  - `log_response_bodies`: default true

## API Endpoints

### Proxy Endpoints (passthrough to OpenAI)
- `POST /v1/chat/completions` - chat completions
- `POST /v1/completions` - legacy completions
- `POST /v1/embeddings` - embeddings
- `GET /v1/models` - list models
- `ANY /v1/*` - any other OpenAI endpoint

### Internal API (for web UI)
- `GET /api/requests` - list requests
  - Query params: `limit`, `offset`, `path`, `model`, `status`, `since`
  - Returns: `{requests: [...], total: N}`
- `GET /api/requests/{id}` - single request detail
- `GET /api/stats` - summary stats (optional, for future dashboard)

## File Structure

```
llm-proxy/
├── run.py              # Entry point
├── config.json         # Configuration (optional)
├── requirements.txt    # Dependencies
├── README.md           # Usage instructions
├── app/
│   ├── __init__.py
│   ├── server.py       # HTTP server setup
│   ├── proxy.py        # Proxy handler
│   ├── logger.py       # Request logging
│   ├── store.py        # In-memory store
│   └── config.py       # Configuration loading
├── static/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── logs/               # Created at runtime
    └── requests-YYYY-MM-DD.jsonl
```

## Dependencies (Minimal)

- `aiohttp` - async HTTP client/server (handles SSE well)
- `aiofiles` - async file I/O for logging (optional, can use sync if simpler)

That's it. No ORM, no database, no frontend framework.

## Security Considerations

- **API key handling**: Never log full API keys. Sanitize to show only last 4 characters.
- **Local only**: Bind to `127.0.0.1` by default, not `0.0.0.0`
- **No auth on UI**: Acceptable for local dev tool. Document the risk if binding to all interfaces.
- **Log sensitivity**: Config option to disable body logging for sensitive use cases

## Out of Scope (Parking Lot)

- Traffic interception / system proxy / MITM
- Non-OpenAI providers (Anthropic, Cohere, etc.)
- Multi-user / authentication
- Cloud deployment / persistence
- Request replay / modification
- Cost calculation / billing alerts
- Export to other formats (HAR, etc.)
- Dashboard with charts / analytics
- Request diffing / comparison
- Websocket support (OpenAI doesn't use it currently)

## Testing Approach

- **Manual testing with an OpenAI-compatible client**: Primary validation - configure the client to use the proxy, verify normal operation
- **Unit tests**: Request parsing, SSE chunk reassembly, log formatting
- **Integration test**: Script that makes sample requests through proxy, verifies logging
- **Self-sufficiency**: Proxy should log its own errors clearly for debugging
