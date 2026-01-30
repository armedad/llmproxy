"""Request/response logging for LLM Proxy."""

import json
import uuid
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


def sanitize_api_key(auth_header: str) -> str:
    """Sanitize API key to show only last 4 characters."""
    if not auth_header:
        return ""
    
    # Format: "Bearer sk-..."
    parts = auth_header.split(" ", 1)
    if len(parts) == 2 and len(parts[1]) > 4:
        key = parts[1]
        return f"{parts[0]} ...{key[-4:]}"
    
    return auth_header


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Sanitize headers, masking sensitive values."""
    sanitized = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            sanitized[key] = sanitize_api_key(value)
        else:
            sanitized[key] = value
    return sanitized


def extract_model(body: Optional[bytes]) -> Optional[str]:
    """Extract model name from request body."""
    if not body:
        return None
    try:
        data = json.loads(body)
        return data.get("model")
    except (json.JSONDecodeError, TypeError):
        return None


def extract_tokens(response_body: Optional[bytes]) -> Optional[Dict[str, int]]:
    """Extract token usage from response body."""
    if not response_body:
        return None
    try:
        data = json.loads(response_body)
        usage = data.get("usage")
        if usage:
            return {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            }
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def parse_body(body: Optional[bytes], log_bodies: bool = True) -> Any:
    """Parse body for logging, respecting config."""
    if not body:
        return None
    if not log_bodies:
        return "[body logging disabled]"
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        # Return as string if not JSON
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            return f"[binary data, {len(body)} bytes]"


class DiskLogger:
    """Writes request logs to disk in JSONL format."""
    
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Create log directory if it doesn't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self) -> Path:
        """Get the log file path for today."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"requests-{date_str}.jsonl"
    
    def write(self, entry: Dict[str, Any]) -> None:
        """Write a log entry to disk."""
        log_file = self._get_log_file()
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                json.dump(entry, f, separators=(",", ":"))
                f.write("\n")
        except IOError as e:
            print(f"[DISK] Error writing log: {e}")


class RequestLogger:
    """Creates log entries for proxied requests."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_request_bodies = config.get("log_request_bodies", True)
        self.log_response_bodies = config.get("log_response_bodies", True)
        self.disk_logger = DiskLogger(config.get("log_dir", "./logs"))
    
    def create_entry(
        self,
        request_id: str,
        method: str,
        path: str,
        request_headers: Dict[str, str],
        request_body: Optional[bytes],
        response_status: int,
        response_headers: Dict[str, str],
        response_body: Optional[bytes],
        duration_ms: float,
        is_streaming: bool = False,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a log entry for a request/response pair."""
        entry = {
            "id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": method,
            "path": path,
            "request_headers": sanitize_headers(request_headers),
            "request_body": parse_body(request_body, self.log_request_bodies),
            "response_status": response_status,
            "response_headers": dict(response_headers),
            "response_body": parse_body(response_body, self.log_response_bodies),
            "is_streaming": is_streaming,
            "duration_ms": round(duration_ms, 2),
            "model": extract_model(request_body),
            "tokens": extract_tokens(response_body) if not is_streaming else None,
            "error": error,
        }
        
        # Write to disk
        self.disk_logger.write(entry)
        
        return entry


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def get_time_ms() -> float:
    """Get current time in milliseconds."""
    return time.time() * 1000
