"""
Rate Limiting Middleware
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import Request, HTTPException, status
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import threading

# In-memory rate limiting store (use Redis in production)
# Structure: {ip_address: {endpoint: [(timestamp, count)]}}
_rate_limit_store: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
_rate_limit_lock = threading.Lock()

# Rate limit configurations
RATE_LIMITS = {
    # Authentication endpoints - stricter limits
    "/api/auth/login": (10, 300),      # 10 requests per 5 minutes
    "/api/auth/register": (5, 3600),   # 5 requests per hour
    "/api/auth/forgot-password": (3, 3600),  # 3 requests per hour
    "/api/auth/reset-password": (5, 3600),   # 5 requests per hour
    "/api/auth/refresh": (30, 60),     # 30 requests per minute
    
    # Public API endpoints
    "/api/public/orders/landing": (60, 60),  # 60 requests per minute
    "/api/public/track": (120, 60),    # 120 requests per minute
    
    # Default for other endpoints
    "default": (300, 60),              # 300 requests per minute
}


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for X-Forwarded-For header (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def cleanup_old_entries(ip: str, endpoint: str, window_seconds: int) -> None:
    """Remove entries older than the window"""
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    with _rate_limit_lock:
        if ip in _rate_limit_store and endpoint in _rate_limit_store[ip]:
            _rate_limit_store[ip][endpoint] = [
                entry for entry in _rate_limit_store[ip][endpoint]
                if entry[0] > cutoff
            ]


def is_rate_limited(ip: str, endpoint: str) -> Tuple[bool, int, int]:
    """
    Check if IP is rate limited for endpoint.
    Returns: (is_limited, remaining_requests, retry_after_seconds)
    """
    # Get rate limit config
    max_requests, window_seconds = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    
    # Cleanup old entries
    cleanup_old_entries(ip, endpoint, window_seconds)
    
    now = datetime.utcnow()
    
    with _rate_limit_lock:
        entries = _rate_limit_store[ip][endpoint]
        
        # Count requests in current window
        current_count = len(entries)
        
        if current_count >= max_requests:
            # Calculate retry after
            if entries:
                oldest = min(entry[0] for entry in entries)
                retry_after = int((oldest + timedelta(seconds=window_seconds) - now).total_seconds())
                retry_after = max(1, retry_after)
            else:
                retry_after = window_seconds
            
            return True, 0, retry_after
        
        # Add new entry
        entries.append((now, 1))
        remaining = max_requests - current_count - 1
        
        return False, remaining, 0


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for FastAPI.
    Should be added before routing middleware.
    """
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/", "/api/health"]:
        return await call_next(request)
    
    # Get client IP
    client_ip = get_client_ip(request)
    
    # Check rate limit
    is_limited, remaining, retry_after = is_rate_limited(client_ip, request.url.path)
    
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Please try again in {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    max_requests, window_seconds = RATE_LIMITS.get(request.url.path, RATE_LIMITS["default"])
    response.headers["X-RateLimit-Limit"] = str(max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(window_seconds)
    
    return response


# IP blacklist for blocking malicious IPs
_ip_blacklist: set = set()
_ip_blacklist_lock = threading.Lock()


def add_to_blacklist(ip: str) -> None:
    """Add an IP to the blacklist"""
    with _ip_blacklist_lock:
        _ip_blacklist.add(ip)


def remove_from_blacklist(ip: str) -> None:
    """Remove an IP from the blacklist"""
    with _ip_blacklist_lock:
        _ip_blacklist.discard(ip)


def is_blacklisted(ip: str) -> bool:
    """Check if IP is blacklisted"""
    with _ip_blacklist_lock:
        return ip in _ip_blacklist


async def ip_blacklist_middleware(request: Request, call_next):
    """
    IP blacklist middleware.
    Blocks requests from blacklisted IPs.
    """
    client_ip = get_client_ip(request)
    
    if is_blacklisted(client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return await call_next(request)
