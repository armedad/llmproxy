#!/usr/bin/env python3
"""LLM Proxy - Entry point."""

import asyncio
import signal
from app.config import get_config
from app.server import start_server


async def main():
    config = get_config()
    
    runner = await start_server(config)
    
    # Keep running until interrupted
    stop_event = asyncio.Event()
    
    def handle_signal():
        print("\n[SERVER] Shutting down...")
        stop_event.set()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    
    await stop_event.wait()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
