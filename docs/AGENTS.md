# LLM Proxy - Agent Instructions

## What This Project Is

A local proxy server that sits between OpenAI-compatible apps and OpenAI's API. It allows observation and debugging of actual API calls - seeing exact prompts, responses, token usage, and timing.

**Key insight:** This is a developer debugging tool, not a production service. Optimize for visibility and simplicity over scalability.

## Project Structure

```
llm-proxy/
├── run.py                 # Entry point - start here
├── config.json            # Runtime configuration
├── requirements.txt       # Python dependencies (minimal)
├── opportunity-assessment.md  # Product spec (read this for context)
├── plan.md                # Implementation phases
├── app/
│   ├── __init__.py
│   ├── server.py          # HTTP server setup, routing
│   ├── proxy.py           # OpenAI proxy logic, streaming
│   ├── logger.py          # Request/response logging
│   ├── store.py           # In-memory request storage
│   └── config.py          # Configuration loading
├── static/
│   ├── index.html         # Web UI structure
│   ├── app.js             # UI logic (vanilla JS)
│   └── styles.css         # Styling
└── logs/                  # Created at runtime
    └── requests-YYYY-MM-DD.jsonl
```

## Key Architectural Decisions

1. **Single process** - Proxy server and web UI in one Python process. Simpler to run and debug.

2. **Generic passthrough** - Proxy forwards any `/v1/*` request to OpenAI rather than hardcoding specific endpoints. Future-proof.

3. **In-memory + disk** - Requests stored in circular buffer (fast UI access) and appended to JSONL files (persistence).

4. **Streaming first** - SSE streaming is a must-have. Proxy passes chunks through immediately while accumulating for logging.

5. **Minimal dependencies** - Only `aiohttp`. No ORM, no database, no frontend framework.

## How to Run

```bash
pip install -r requirements.txt
python run.py
```

Opens on `http://localhost:8000` by default. Configure port in `config.json`.

## Critical Patterns

### Streaming SSE Proxy (CRITICAL)

When proxying streaming responses:
1. Pass each chunk to client immediately - no buffering
2. Accumulate chunks in memory for logging
3. Reassemble complete response only after stream ends
4. Handle `data: [DONE]` termination

Never buffer the entire response before sending - that defeats streaming.

### API Key Handling (CRITICAL)

- **Never log full API keys** - sanitize to show only last 4 characters
- Pass through client's `Authorization` header by default
- Allow override via `config.json` for testing

### Error Passthrough

Return OpenAI's error responses unchanged to the client. The proxy should be invisible - apps should behave identically whether using proxy or direct connection.

## Development Workflow

### After any change to Python files:
1. Stop the server (Ctrl+C)
2. Restart: `python run.py`
3. Verify with a test request

### Testing the proxy:
```bash
# Non-streaming
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-your-key"

# Streaming
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}], "stream": true}'
```

### Testing with an OpenAI-compatible client:
Configure the client's OpenAI base URL to `http://localhost:8000` and use normally.

## Logging Standards

All log output should include timestamps:
```
[HH:MM:SS] [PROXY] Forwarding POST /v1/chat/completions
[HH:MM:SS] [PROXY] Response 200 in 1234ms
```

## Error Handling

- Fail fast with clear error messages
- Log errors with enough context for debugging
- User-facing errors should suggest what to do next
- Verbose errors are better than silent failures

## Code Style

- **DRY** - Don't repeat yourself
- **YAGNI** - You aren't gonna need it
- **Names reveal intent** - `sanitize_api_key()` not `process_header()`
- **Comments explain why** - not what the code does

## When Requirements Are Unclear

- Make the most reasonable assumption and state it explicitly
- Proceed with implementation rather than blocking
- Document assumptions in code comments
- Flag assumptions clearly: "Assuming X because Y"

## Verification Before Completion

**No completion claims without fresh verification evidence.**

Before claiming any phase is complete:
1. Run the verification steps from `plan.md`
2. Confirm actual output matches expected
3. Only then claim completion

"Should work" is not verification. Run it and see.

## What NOT to Do

- Don't add authentication - this is a local dev tool
- Don't add a database - in-memory + JSONL is enough
- Don't add a build step for the frontend - vanilla JS only
- Don't buffer streaming responses - pass through immediately
- Don't log full API keys - sanitize them
