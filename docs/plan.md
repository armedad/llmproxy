# LLM Proxy - Implementation Plan

Reference the detailed spec in `opportunity-assessment.md` for architecture and requirements.

---

## Phase 0: Project Setup

**Goal:** Establish project structure, dependencies, and verify environment.

**Files to create:**
- `requirements.txt`
- `run.py`
- `app/__init__.py`
- `app/config.py`
- `config.json`
- `README.md`

**Tasks:**
1. Create project structure with `app/` directory and empty `__init__.py`
2. Create `requirements.txt` with `aiohttp` as the only dependency
3. Create `config.py` that loads configuration from `config.json` with sensible defaults (port 8000, OpenAI base URL, log directory)
4. Create minimal `run.py` that imports config and prints "LLM Proxy starting on port {port}"
5. Create `config.json` with default values
6. Create `README.md` with basic usage instructions

**Done means:**
- Running `python run.py` prints startup message with configured port
- Config can be overridden via `config.json`

**Test it:**
1. Run `pip install -r requirements.txt`
2. Run `python run.py`
3. Verify output shows "LLM Proxy starting on port 8000"
4. Edit `config.json` to change port to 9000
5. Run again, verify port shows 9000

---

## Phase 1: Basic HTTP Server

**Goal:** Minimal async HTTP server that responds to requests.

**Files to create/modify:**
- `app/server.py`
- `run.py` (modify)

**Tasks:**
1. Create `server.py` with aiohttp server setup
2. Add route `GET /` that returns "LLM Proxy is running"
3. Add route `GET /health` that returns JSON `{"status": "ok"}`
4. Modify `run.py` to start the server

**Done means:**
- Server starts and accepts HTTP requests
- Browser shows "LLM Proxy is running" at `http://localhost:8000/`

**Test it:**
1. Run `python run.py`
2. Open browser to `http://localhost:8000/`
3. Verify page shows "LLM Proxy is running"
4. Open `http://localhost:8000/health`
5. Verify JSON response `{"status": "ok"}`

---

## Phase 2: Non-Streaming Proxy

**Goal:** Proxy non-streaming requests to OpenAI and return responses.

**Files to create/modify:**
- `app/proxy.py`
- `app/server.py` (modify)

**Tasks:**
1. Create `proxy.py` with function to forward requests to OpenAI
2. Handle API key: pass through client's `Authorization` header, or use override from config if set
3. Add catch-all route for `/v1/*` that proxies to OpenAI
4. Forward all headers (except Host), forward request body, return response unchanged
5. Handle errors gracefully - return OpenAI's error response to client

**Done means:**
- Request to `GET /v1/models` through proxy returns OpenAI's model list
- Request to `POST /v1/embeddings` through proxy returns embeddings

**Test it:**
1. Start proxy: `python run.py`
2. In another terminal, test models endpoint:
   ```
   curl http://localhost:8000/v1/models \
     -H "Authorization: Bearer sk-your-key"
   ```
3. Verify response contains model list from OpenAI
4. Test embeddings:
   ```
   curl http://localhost:8000/v1/embeddings \
     -H "Authorization: Bearer sk-your-key" \
     -H "Content-Type: application/json" \
     -d '{"model": "text-embedding-3-small", "input": "hello world"}'
   ```
5. Verify response contains embedding vector

---

## Phase 3: Streaming Proxy

**Goal:** Proxy streaming chat completions, passing SSE chunks through in real-time.

**Files to modify:**
- `app/proxy.py`

**Tasks:**
1. Detect streaming requests (check for `stream: true` in request body)
2. For streaming requests, set up SSE passthrough
3. Read chunks from OpenAI, immediately write to client response
4. Preserve SSE format (`data: {...}\n\n`)
5. Handle stream termination (`data: [DONE]`)

**Done means:**
- Streaming chat completion through proxy works identically to direct OpenAI call
- Chunks arrive in real-time (no buffering delay)

**Test it:**
1. Start proxy: `python run.py`
2. Test streaming chat completion:
   ```
   curl http://localhost:8000/v1/chat/completions \
     -H "Authorization: Bearer sk-your-key" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Count to 5"}], "stream": true}'
   ```
3. Verify chunks stream in real-time (not all at once)
4. Verify response format matches OpenAI's SSE format

---

## Phase 4: Request Logging (Memory)

**Goal:** Capture and store requests/responses in memory for later inspection.

**Files to create/modify:**
- `app/logger.py`
- `app/store.py`
- `app/proxy.py` (modify)

**Tasks:**
1. Create `store.py` with in-memory circular buffer (default 1000 requests)
2. Create `logger.py` with function to create log entry from request/response
3. Log entry includes: id, timestamp, method, path, headers (sanitized), request body, response body, status, duration, model, tokens
4. For streaming requests: accumulate chunks, reassemble full response for logging
5. Sanitize API keys in headers (show only last 4 chars)
6. Integrate logging into proxy handler

**Done means:**
- Every proxied request is captured in memory
- Streaming responses are reassembled into complete response for logging

**Test it:**
1. Start proxy and make a few requests (models, embeddings, streaming chat)
2. Add temporary debug endpoint `GET /api/requests` that returns stored requests
3. Verify all requests appear with correct data
4. Verify streaming response is reassembled (not chunks)
5. Verify API key is sanitized in logged headers

---

## Phase 5: Disk Logging

**Goal:** Persist request logs to disk in JSONL format.

**Files to create/modify:**
- `app/logger.py` (modify)

**Tasks:**
1. Add disk logging to logger - write each request as JSON line to `logs/requests-YYYY-MM-DD.jsonl`
2. Create logs directory if it doesn't exist
3. Use date-based file rotation (new file each day)
4. Write synchronously (simple, and we're not high-throughput)
5. Respect config options for disabling body logging

**Done means:**
- Each request creates a line in the daily log file
- Log files are valid JSONL (one JSON object per line)

**Test it:**
1. Start proxy and make several requests
2. Check `logs/` directory for today's log file
3. Verify file contains one JSON object per line
4. Verify each line can be parsed as valid JSON
5. Verify request/response bodies are captured

---

## Phase 6: Internal API

**Goal:** API endpoints for the web UI to fetch request data.

**Files to create/modify:**
- `app/server.py` (modify)

**Tasks:**
1. Add `GET /api/requests` endpoint
   - Returns list of requests from in-memory store
   - Query params: `limit` (default 50), `offset`, `path`, `model`, `status`
   - Response: `{"requests": [...], "total": N}`
2. Add `GET /api/requests/{id}` endpoint
   - Returns single request by ID
   - 404 if not found

**Done means:**
- UI can fetch paginated request list
- UI can fetch individual request details

**Test it:**
1. Start proxy, make several requests
2. `curl http://localhost:8000/api/requests` - verify list response
3. `curl http://localhost:8000/api/requests?limit=2` - verify pagination
4. `curl http://localhost:8000/api/requests/{id}` with valid ID - verify detail response
5. `curl http://localhost:8000/api/requests/invalid-id` - verify 404

---

## Phase 7: Web UI - Basic Structure

**Goal:** Serve static web UI with basic layout.

**Files to create:**
- `static/index.html`
- `static/app.js`
- `static/styles.css`

**Files to modify:**
- `app/server.py` (add static file serving)

**Tasks:**
1. Configure server to serve static files from `static/` directory
2. Create `index.html` with basic structure: header, request list container, detail panel
3. Create `styles.css` with clean, minimal styling (dark theme preferred for dev tool)
4. Create `app.js` with basic fetch to `/api/requests` and console.log of results

**Done means:**
- Navigating to `http://localhost:8000/` shows the web UI
- Console shows fetched request data

**Test it:**
1. Start proxy, make a few requests
2. Open `http://localhost:8000/` in browser
3. Open browser dev tools console
4. Verify request data is logged to console

---

## Phase 8: Web UI - Request List

**Goal:** Display request list in the UI.

**Files to modify:**
- `static/app.js`
- `static/styles.css`
- `static/index.html`

**Tasks:**
1. Render request list as table/list in the UI
2. Each row shows: timestamp, method, path, model, status, duration, token count
3. Style rows: green for success, red for errors
4. Newest requests at top
5. Add auto-refresh toggle (poll every 2 seconds when enabled)

**Done means:**
- Request list displays in browser
- New requests appear when auto-refresh is on

**Test it:**
1. Start proxy
2. Open UI in browser
3. Make a request through proxy
4. Enable auto-refresh
5. Verify new request appears in list within 2 seconds
6. Verify error requests show in red

---

## Phase 9: Web UI - Request Detail

**Goal:** Click a request to see full details.

**Files to modify:**
- `static/app.js`
- `static/styles.css`
- `static/index.html`

**Tasks:**
1. Click handler on request rows
2. Fetch full request detail from `/api/requests/{id}`
3. Display in detail panel: headers, request body, response body
4. Collapsible sections for each
5. JSON formatting with basic syntax highlighting (CSS-based)
6. Copy buttons for request body and response body

**Done means:**
- Clicking a request shows full details
- JSON is formatted and readable
- Can copy request/response with one click

**Test it:**
1. Start proxy, make requests
2. Open UI, click on a request
3. Verify detail panel shows headers, request body, response body
4. Verify JSON is formatted (not single line)
5. Click copy button, paste somewhere, verify correct content

---

## Phase 10: Web UI - Filtering

**Goal:** Filter requests by endpoint, model, status.

**Files to modify:**
- `static/app.js`
- `static/index.html`
- `static/styles.css`

**Tasks:**
1. Add filter controls above request list
2. Endpoint filter: text input or dropdown
3. Model filter: dropdown populated from seen models
4. Status filter: success/error/all
5. Filters update the API request params
6. Persist filter state in URL query params (for refresh)

**Done means:**
- Can filter to show only chat completions
- Can filter to show only errors
- Filters persist on page refresh

**Test it:**
1. Make various requests (different endpoints, some errors)
2. Open UI
3. Filter by endpoint - verify list updates
4. Filter by status=error - verify only errors show
5. Refresh page - verify filters persist

---

## Phase 11: Polish & Documentation

**Goal:** Final cleanup and documentation.

**Files to modify:**
- `README.md`
- Various files for cleanup

**Tasks:**
1. Update README with:
   - Quick start instructions
   - Configuration options
   - How to configure an OpenAI-compatible client to use the proxy
   - Screenshots of UI (optional)
2. Add helpful startup message showing URL to open
3. Handle graceful shutdown (Ctrl+C)
4. Review and clean up any debug code

**Done means:**
- New user can get running from README alone
- Clean startup/shutdown experience

**Test it:**
1. Follow README instructions from scratch
2. Verify proxy starts and works
3. Verify Ctrl+C shuts down cleanly
4. Configure an OpenAI-compatible client to use the proxy, verify it works normally
