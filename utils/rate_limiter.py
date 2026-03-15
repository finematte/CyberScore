"""
Rate limiting utilities for CyberScore
"""

import time
from typing import Dict, Optional
from collections import defaultdict, deque
from config import settings


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.max_requests = settings.rate_limit_requests_per_minute
        self.window_size = 60  # 1 minute in seconds
        self.burst_limit = settings.rate_limit_burst

    def is_allowed(self, client_id: str) -> tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed for client
        Returns (is_allowed, rate_limit_info)
        """
        now = time.time()
        client_requests = self.requests[client_id]

        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_size:
            client_requests.popleft()

        # Check if under rate limit
        if len(client_requests) >= self.max_requests:
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset_time": int(client_requests[0] + self.window_size),
                "retry_after": int(client_requests[0] + self.window_size - now),
            }

        # Add current request
        client_requests.append(now)

        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - len(client_requests),
            "reset_time": int(now + self.window_size),
        }

    def get_client_id(self, request) -> str:
        """Extract client ID from request"""
        # Try to get IP address
        client_ip = getattr(request, "client", {}).get("host", "unknown")
        return client_ip


# Global rate limiter instance
rate_limiter = RateLimiter()
