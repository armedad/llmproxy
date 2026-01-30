"""In-memory request store with circular buffer."""

from collections import deque
from typing import Optional, List, Dict, Any
import threading


class RequestStore:
    """Thread-safe circular buffer for storing request logs."""
    
    def __init__(self, max_size: int = 1000):
        self._requests = deque(maxlen=max_size)
        self._by_id = {}  # Quick lookup by ID
        self._lock = threading.Lock()
    
    def add(self, request_log: Dict[str, Any]) -> None:
        """Add a request log entry."""
        with self._lock:
            request_id = request_log.get("id")
            
            # If buffer is full, remove oldest from lookup dict
            if len(self._requests) == self._requests.maxlen:
                oldest = self._requests[0]
                self._by_id.pop(oldest.get("id"), None)
            
            self._requests.append(request_log)
            if request_id:
                self._by_id[request_id] = request_log
    
    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a request by ID."""
        with self._lock:
            return self._by_id.get(request_id)
    
    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        path: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,  # "success" or "error"
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        List requests with optional filtering.
        Returns (requests, total_count).
        """
        with self._lock:
            # Start with all requests, newest first
            all_requests = list(reversed(self._requests))
            
            # Apply filters
            filtered = all_requests
            
            if path:
                filtered = [r for r in filtered if path in r.get("path", "")]
            
            if model:
                filtered = [r for r in filtered if r.get("model") == model]
            
            if status == "success":
                filtered = [r for r in filtered if 200 <= r.get("response_status", 0) < 400]
            elif status == "error":
                filtered = [r for r in filtered if r.get("response_status", 0) >= 400]
            
            total = len(filtered)
            
            # Apply pagination
            paginated = filtered[offset:offset + limit]
            
            return paginated, total
    
    def count(self) -> int:
        """Get total number of stored requests."""
        with self._lock:
            return len(self._requests)


# Global store instance
_store: Optional[RequestStore] = None


def get_store(max_size: int = 1000) -> RequestStore:
    """Get or create the global request store."""
    global _store
    if _store is None:
        _store = RequestStore(max_size)
    return _store
