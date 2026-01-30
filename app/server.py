"""HTTP server setup for LLM Proxy."""

import os
from pathlib import Path
from aiohttp import web
from datetime import datetime
from .proxy import setup_proxy_routes
from .store import get_store


# Get static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


def timestamp():
    """Return current timestamp for logging."""
    return datetime.now().strftime("%H:%M:%S")


async def handle_root(request):
    """Handle GET / - serve the web UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="LLM Proxy is running", content_type="text/plain")


async def handle_help(request):
    """Handle GET /help - serve the help page."""
    help_path = STATIC_DIR / "help.html"
    if help_path.exists():
        return web.FileResponse(help_path)
    return web.Response(text="Help page not found", status=404)


async def handle_health(request):
    """Handle GET /health - health check endpoint."""
    return web.json_response({"status": "ok"})


async def handle_api_requests(request):
    """Handle GET /api/requests - list logged requests."""
    store = get_store()
    
    # Parse query params
    limit = int(request.query.get("limit", 50))
    offset = int(request.query.get("offset", 0))
    path = request.query.get("path")
    model = request.query.get("model")
    status = request.query.get("status")
    
    requests_list, total = store.list(
        limit=limit,
        offset=offset,
        path=path,
        model=model,
        status=status,
    )
    
    return web.json_response({
        "requests": requests_list,
        "total": total,
    })


async def handle_api_request_detail(request):
    """Handle GET /api/requests/{id} - get single request detail."""
    store = get_store()
    request_id = request.match_info.get("id")
    
    entry = store.get(request_id)
    if entry is None:
        return web.json_response(
            {"error": "Request not found"},
            status=404,
        )
    
    return web.json_response(entry)


def create_app(config: dict):
    """Create and configure the aiohttp application."""
    app = web.Application()
    
    # Routes
    app.router.add_get("/", handle_root)
    app.router.add_get("/help", handle_help)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/api/requests", handle_api_requests)
    app.router.add_get("/api/requests/{id}", handle_api_request_detail)
    
    # Static files
    app.router.add_static("/static/", path=str(STATIC_DIR), name="static")
    
    # Proxy routes (must be added after specific routes)
    setup_proxy_routes(app, config)
    
    return app


async def start_server(config: dict):
    """Start the HTTP server."""
    app = create_app(config)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "127.0.0.1", config["port"])
    await site.start()
    
    print(f"")
    print(f"  LLM Proxy running at http://127.0.0.1:{config['port']}")
    print(f"")
    print(f"  Web UI:     http://127.0.0.1:{config['port']}/")
    print(f"  Proxy API:  http://127.0.0.1:{config['port']}/v1/...")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"")
    
    return runner
