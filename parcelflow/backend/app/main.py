"""
FastAPI Main Application
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import (
    auth, users, businesses, branches, waybills, orders,
    vendors, agents, products, inventory, leads, accounting,
    dashboard, tracking, public, warehouses, roles,
    pickups, dispatches, deliveries, notifications, reports,
    bulk, audit, vendor_portal
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only warnings and errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Set app logger to INFO
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
# Silence noisy third-party loggers
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("passlib").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Run database migrations
    from app.utils.migrations import run_migrations
    run_migrations()
    logger.info("Database migrations completed")

    # Create default roles and permissions if not exist
    from app.services.rbac import initialize_rbac
    initialize_rbac()
    logger.info("RBAC initialized")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ParcelFlow - Multi-tenant Logistics and E-commerce CRM Platform
    
    ## Features
    - **Multi-tenant Architecture**: Business and branch isolation
    - **Logistics Management**: Waybills, pickups, warehouse, dispatch, delivery
    - **Inventory Management**: Products, stock movements, warehouses
    - **Vendor Portal**: Vendor management and remittances
    - **Order Management**: Orders, leads, customer tracking
    - **Accounting**: Transactions, expenses, vendor ledger
    - **Analytics**: Dashboards and reports
    
    ## Authentication
    JWT-based authentication with role-based access control (RBAC).
    """,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data: https:; frame-ancestors 'none'"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


app.add_middleware(SecurityHeadersMiddleware)


# Rate Limiting Middleware (simplified inline version)
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting"""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = {}  # {ip: {endpoint: [(timestamp, count)]}}
        self.lock = threading.Lock()
    
    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, ip: str, endpoint: str) -> bool:
        from datetime import datetime, timedelta
        import threading
        
        # Rate limits: (max_requests, window_seconds)
        limits = {
            "/api/auth/login": (10, 300),
            "/api/auth/register": (5, 3600),
            "/api/auth/forgot-password": (3, 3600),
            "/api/auth/reset-password": (5, 3600),
            "/api/public/orders/landing": (60, 60),
        }
        
        max_requests, window = limits.get(endpoint, (300, 60))
        cutoff = datetime.utcnow() - timedelta(seconds=window)
        
        with self.lock:
            if ip not in self.requests:
                self.requests[ip] = {}
            if endpoint not in self.requests[ip]:
                self.requests[ip][endpoint] = []
            
            # Cleanup old entries
            self.requests[ip][endpoint] = [
                t for t in self.requests[ip][endpoint] if t > cutoff
            ]
            
            # Check limit
            if len(self.requests[ip][endpoint]) >= max_requests:
                return True
            
            # Add current request
            self.requests[ip][endpoint].append(datetime.utcnow())
            return False
    
    async def dispatch(self, request: Request, call_next):
        import threading
        
        # Skip for health checks
        if request.url.path in ["/health", "/", "/api/health"]:
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        
        if self.is_rate_limited(client_ip, request.url.path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later."
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)


import threading
app.add_middleware(RateLimitMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error" if not settings.DEBUG else str(exc)
        }
    )


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(businesses.router, prefix="/api/businesses", tags=["Businesses"])
app.include_router(branches.router, prefix="/api/branches", tags=["Branches"])
app.include_router(roles.router, prefix="/api/roles", tags=["Roles"])
app.include_router(warehouses.router, prefix="/api/warehouses", tags=["Warehouses"])
app.include_router(waybills.router, prefix="/api/waybills", tags=["Waybills"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(vendors.router, prefix="/api/vendors", tags=["Vendors"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(accounting.router, prefix="/api/accounting", tags=["Accounting"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["Tracking"])
app.include_router(public.router, prefix="/api/public", tags=["Public API"])
app.include_router(pickups.router, prefix="/api/pickups", tags=["Pickups"])
app.include_router(dispatches.router, prefix="/api/dispatches", tags=["Dispatches"])
app.include_router(deliveries.router, prefix="/api/deliveries", tags=["Deliveries"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(bulk.router, prefix="/api/bulk", tags=["Bulk Operations"])
app.include_router(audit.router, prefix="/api/audit-logs", tags=["Audit Logs"])
app.include_router(vendor_portal.router, prefix="/api/vendor-portal", tags=["Vendor Portal"])


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs" if settings.DEBUG else "Documentation disabled in production"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
