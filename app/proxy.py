"""Proxy handler for forwarding requests to OpenAI."""

import json
import aiohttp
from aiohttp import web
from datetime import datetime

from .logger import RequestLogger, generate_request_id, get_time_ms
from .store import get_store


def timestamp():
    """Return current timestamp for logging."""
    return datetime.now().strftime("%H:%M:%S")


def get_api_key(request, config):
    """Get API key - use override if set, otherwise pass through client's key."""
    if config.get("api_key_override"):
        return f"Bearer {config['api_key_override']}"
    return request.headers.get("Authorization", "")


def prepare_headers(request, config):
    """Prepare headers for forwarding to OpenAI."""
    # Headers to forward (exclude hop-by-hop headers)
    skip_headers = {"host", "content-length", "transfer-encoding", "connection"}
    
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in skip_headers:
            headers[key] = value
    
    # Set/override authorization
    auth = get_api_key(request, config)
    if auth:
        headers["Authorization"] = auth
    
    return headers


def is_streaming_request(body: bytes) -> bool:
    """Check if request body indicates streaming."""
    if not body:
        return False
    try:
        data = json.loads(body)
        return data.get("stream", False) is True
    except (json.JSONDecodeError, TypeError):
        return False


async def proxy_streaming_request(request, config, body, headers, target_url, logger, store):
    """Proxy a streaming request, passing SSE chunks through in real-time."""
    request_id = generate_request_id()
    start_time = get_time_ms()
    path = f"/v1/{request.match_info.get('path', '')}"
    
    print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Streaming {request.method} -> {target_url}")
    
    # Accumulate chunks for logging
    accumulated_chunks = []
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
            ) as resp:
                # If OpenAI returns an error, pass it through as regular JSON
                if resp.status != 200:
                    error_body = await resp.read()
                    duration_ms = get_time_ms() - start_time
                    print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Error: {resp.status}")
                    
                    # Log the error
                    entry = logger.create_entry(
                        request_id=request_id,
                        method=request.method,
                        path=path,
                        request_headers=dict(request.headers),
                        request_body=body,
                        response_status=resp.status,
                        response_headers=dict(resp.headers),
                        response_body=error_body,
                        duration_ms=duration_ms,
                        is_streaming=True,
                        error=f"HTTP {resp.status}",
                    )
                    store.add(entry)
                    
                    return web.Response(
                        status=resp.status,
                        body=error_body,
                        content_type="application/json",
                    )
                
                # Set up streaming response
                response = web.StreamResponse(
                    status=200,
                    headers={
                        "Content-Type": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    }
                )
                await response.prepare(request)
                
                # Stream chunks through
                chunk_count = 0
                async for chunk in resp.content.iter_any():
                    if chunk:
                        await response.write(chunk)
                        accumulated_chunks.append(chunk)
                        chunk_count += 1
                
                duration_ms = get_time_ms() - start_time
                print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Streamed {chunk_count} chunks in {duration_ms:.0f}ms")
                
                # Reassemble and log
                full_response = b"".join(accumulated_chunks)
                entry = logger.create_entry(
                    request_id=request_id,
                    method=request.method,
                    path=path,
                    request_headers=dict(request.headers),
                    request_body=body,
                    response_status=200,
                    response_headers=dict(resp.headers),
                    response_body=full_response,
                    duration_ms=duration_ms,
                    is_streaming=True,
                )
                store.add(entry)
                
                await response.write_eof()
                return response
                
        except aiohttp.ClientError as e:
            duration_ms = get_time_ms() - start_time
            print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Error: {e}")
            
            # Log the error
            entry = logger.create_entry(
                request_id=request_id,
                method=request.method,
                path=path,
                request_headers=dict(request.headers),
                request_body=body,
                response_status=502,
                response_headers={},
                response_body=None,
                duration_ms=duration_ms,
                is_streaming=True,
                error=str(e),
            )
            store.add(entry)
            
            return web.json_response(
                {"error": {"message": str(e), "type": "proxy_error"}},
                status=502,
            )


async def proxy_request(request, config, logger, store):
    """Proxy a request to OpenAI and return the response."""
    # Build target URL
    path_segment = request.match_info.get("path", "")
    target_url = f"{config['openai_base_url']}/v1/{path_segment}"
    path = f"/v1/{path_segment}"
    
    # Get request body if present
    body = None
    if request.body_exists:
        body = await request.read()
    
    # Prepare headers
    headers = prepare_headers(request, config)
    
    # Check if this is a streaming request
    if is_streaming_request(body):
        return await proxy_streaming_request(request, config, body, headers, target_url, logger, store)
    
    # Non-streaming request
    request_id = generate_request_id()
    start_time = get_time_ms()
    
    print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] {request.method} {path} -> {target_url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
            ) as resp:
                # Read response
                response_body = await resp.read()
                duration_ms = get_time_ms() - start_time
                
                print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Response: {resp.status} in {duration_ms:.0f}ms")
                
                # Build response headers (exclude hop-by-hop)
                response_headers = {}
                skip_response_headers = {"content-encoding", "transfer-encoding", "connection"}
                for key, value in resp.headers.items():
                    if key.lower() not in skip_response_headers:
                        response_headers[key] = value
                
                # Log the request
                entry = logger.create_entry(
                    request_id=request_id,
                    method=request.method,
                    path=path,
                    request_headers=dict(request.headers),
                    request_body=body,
                    response_status=resp.status,
                    response_headers=response_headers,
                    response_body=response_body,
                    duration_ms=duration_ms,
                    is_streaming=False,
                )
                store.add(entry)
                
                return web.Response(
                    status=resp.status,
                    body=response_body,
                    headers=response_headers,
                )
        except aiohttp.ClientError as e:
            duration_ms = get_time_ms() - start_time
            print(f"[{timestamp()}] [PROXY] [{request_id[:8]}] Error: {e}")
            
            # Log the error
            entry = logger.create_entry(
                request_id=request_id,
                method=request.method,
                path=path,
                request_headers=dict(request.headers),
                request_body=body,
                response_status=502,
                response_headers={},
                response_body=None,
                duration_ms=duration_ms,
                is_streaming=False,
                error=str(e),
            )
            store.add(entry)
            
            return web.json_response(
                {"error": {"message": str(e), "type": "proxy_error"}},
                status=502,
            )


def setup_proxy_routes(app, config):
    """Add proxy routes to the application."""
    logger = RequestLogger(config)
    store = get_store(config.get("max_memory_requests", 1000))
    
    async def handle_proxy(request):
        return await proxy_request(request, config, logger, store)
    
    # Catch-all for /v1/* routes
    app.router.add_route("*", "/v1/{path:.*}", handle_proxy)
