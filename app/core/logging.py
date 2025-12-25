"""
Logging configuration for PC Recommendation System
"""
import logging
import sys
import time
import json
from pathlib import Path
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings


def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # File handler for errors only
    error_file_handler = logging.FileHandler(log_dir / "error.log")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)

    # Set specific loggers
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return root_logger


# Global logger instance
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/favicon.ico"]
        self.logger = get_logger("http")

    async def dispatch(self, request: Request, call_next):
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Extract request information
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query": str(request.url.query),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "content_length": request.headers.get("content-length", 0),
        }

        # Log request
        self.logger.info(f"REQUEST: {json.dumps(request_info)}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate response time
            response_time = time.time() - start_time

            # Extract response information
            response_info = {
                "status_code": response.status_code,
                "content_length": response.headers.get("content-length", 0),
                "response_time_ms": round(response_time * 1000, 2),
            }

            # Log response
            log_level = "info" if response.status_code < 400 else "warning" if response.status_code < 500 else "error"
            log_method = getattr(self.logger, log_level)
            log_method(f"RESPONSE: {json.dumps({**request_info, **response_info})}")

            return response

        except Exception as e:
            # Calculate response time for errors
            response_time = time.time() - start_time

            # Log error
            error_info = {
                **request_info,
                "error": str(e),
                "response_time_ms": round(response_time * 1000, 2),
                "status_code": 500
            }
            self.logger.error(f"ERROR: {json.dumps(error_info)}")

            # Re-raise the exception
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fallback to client host
        return request.client.host if request.client else "unknown"


class AuditLogger:
    """Logger for security and audit events"""

    def __init__(self):
        self.logger = get_logger("audit")

    def log_event(self, event_type: str, user_id: Optional[str] = None,
                  resource: Optional[str] = None, action: str = "",
                  details: dict = None, severity: str = "info"):
        """Log an audit event"""
        event_data = {
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "details": details or {},
            "timestamp": time.time(),
            "severity": severity
        }

        log_method = getattr(self.logger, severity, self.logger.info)
        log_method(f"AUDIT: {json.dumps(event_data)}")

    def log_auth_attempt(self, email: str, success: bool, ip_address: str,
                        user_agent: str = "", details: dict = None):
        """Log authentication attempt"""
        self.log_event(
            event_type="auth_attempt",
            resource=email,
            action="login",
            details={
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                **(details or {})
            },
            severity="warning" if not success else "info"
        )

    def log_user_action(self, user_id: str, action: str, resource: str = "",
                       details: dict = None):
        """Log user action"""
        self.log_event(
            event_type="user_action",
            user_id=user_id,
            resource=resource,
            action=action,
            details=details
        )

    def log_security_event(self, event_type: str, severity: str = "warning",
                          details: dict = None):
        """Log security-related event"""
        self.log_event(
            event_type=f"security_{event_type}",
            severity=severity,
            details=details
        )


# Global instances
audit_logger = AuditLogger()
