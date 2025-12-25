"""
Security utilities and middleware for PC Recommendation System
"""
import re
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware for request validation and protection"""

    def __init__(self, app, input_validator=None):
        super().__init__(app)
        self.input_validator = input_validator or InputValidator()

    async def dispatch(self, request: Request, call_next):
        # Request size limiting
        await self._check_request_size(request)

        # Input sanitization and validation
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_and_sanitize_request(request)

        # Add security headers
        response = await call_next(request)

        # Enhanced security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Content Security Policy for API
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'none'; "
            "style-src 'none'; "
            "img-src 'none'; "
            "font-src 'none'; "
            "connect-src 'self'; "
            "media-src 'none'; "
            "object-src 'none'; "
            "frame-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Remove server header for security
        response.headers.pop("Server", None)

        return response

    async def _check_request_size(self, request: Request):
        """Check request size limits"""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                max_size = 1024 * 1024  # 1MB limit
                if size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request too large"
                    )
            except ValueError:
                pass  # Invalid content-length header

    async def _validate_and_sanitize_request(self, request: Request):
        """Validate and sanitize request body"""
        try:
            body = await request.body()
            if not body:
                return

            body_str = body.decode('utf-8')

            # Size check
            if len(body_str) > 100000:  # 100KB limit
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request body too large"
                )

            # Basic JSON validation
            import json
            try:
                json_data = json.loads(body_str)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload"
                )

            # Input sanitization
            sanitized = self._sanitize_string(body_str)

            # Validate JSON structure after sanitization
            try:
                json.loads(sanitized)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request sanitization failed"
                )

        except HTTPException:
            raise
        except Exception as e:
            # Log suspicious requests
            logger.warning(f"Request validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request format"
            )

    async def _sanitize_request_body(self, request: Request):
        """Sanitize request body for malicious content"""
        try:
            body = await request.body()
            if body:
                body_str = body.decode('utf-8')

                # Basic input sanitization
                sanitized = self._sanitize_string(body_str)

                # Replace request body with sanitized version
                # Note: This is a basic implementation. In production,
                # consider using specialized security libraries
                import json
                try:
                    json.loads(sanitized)  # Validate JSON structure
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON payload"
                    )
        except Exception:
            # If sanitization fails, let the request proceed
            # In production, you might want to block suspicious requests
            pass

    def _sanitize_string(self, input_str: str) -> str:
        """Basic string sanitization"""
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                  # JavaScript URLs
            r'on\w+\s*=',                   # Event handlers
            r'<iframe[^>]*>.*?</iframe>',   # Iframes
            r'<object[^>]*>.*?</object>',   # Objects
            r'<embed[^>]*>.*?</embed>',     # Embeds
        ]

        sanitized = input_str
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.max_requests = 100  # requests per window
        self.window_seconds = 900  # 15 minutes

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        import time
        current_time = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < self.window_seconds
        ]

        # Check rate limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        # Add current request
        self.requests[client_id].append(current_time)
        return True

    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        if client_id not in self.requests:
            return self.max_requests

        import time
        current_time = time.time()

        # Clean old requests
        valid_requests = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < self.window_seconds
        ]

        return max(0, self.max_requests - len(valid_requests))

    def get_reset_time(self, client_id: str) -> float:
        """Get time until rate limit resets"""
        if client_id not in self.requests:
            return 0

        import time
        current_time = time.time()

        # Find oldest request in window
        valid_requests = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < self.window_seconds
        ]

        if not valid_requests:
            return 0

        oldest_request = min(valid_requests)
        return max(0, self.window_seconds - (current_time - oldest_request))


class AuthRateLimiter:
    """Rate limiter specifically for authentication endpoints"""

    def __init__(self):
        self.login_attempts = RateLimiter()
        self.login_attempts.max_requests = 5  # 5 login attempts
        self.login_attempts.window_seconds = 900  # per 15 minutes

        self.signup_attempts = RateLimiter()
        self.signup_attempts.max_requests = 3  # 3 signup attempts
        self.signup_attempts.window_seconds = 3600  # per hour

        self.password_reset_attempts = RateLimiter()
        self.password_reset_attempts.max_requests = 3  # 3 reset requests
        self.password_reset_attempts.window_seconds = 3600  # per hour


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests"""

    def __init__(self, app, auth_limiter: AuthRateLimiter = None):
        super().__init__(app)
        self.auth_limiter = auth_limiter or AuthRateLimiter()

    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP address for now)
        client_id = self._get_client_id(request)

        # Apply different rate limits based on endpoint
        path = request.url.path
        limiter = None

        if path.endswith('/auth/login'):
            limiter = self.auth_limiter.login_attempts
        elif path.endswith('/auth/signup'):
            limiter = self.auth_limiter.signup_attempts
        elif path.endswith('/auth/reset-password'):
            limiter = self.auth_limiter.password_reset_attempts

        if limiter:
            if not limiter.is_allowed(client_id):
                reset_time = limiter.get_reset_time(client_id)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Too many requests",
                        "message": "Rate limit exceeded. Please try again later.",
                        "reset_in_seconds": int(reset_time)
                    }
                )

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Use X-Forwarded-For if behind proxy, otherwise use client IP
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take first IP if multiple
            return forwarded_for.split(',')[0].strip()

        # Fallback to client host
        return request.client.host if request.client else 'unknown'


class InputValidator:
    """Input validation utilities"""

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize and validate text input"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        # Basic sanitization (extend as needed)
        text = re.sub(r'[<>]', '', text)  # Remove angle brackets

        return text

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_price(price: float) -> bool:
        """Validate price input"""
        return isinstance(price, (int, float)) and price >= 0 and price <= 10000

    @staticmethod
    def validate_purpose(purpose: str) -> bool:
        """Validate purpose input"""
        valid_purposes = ['gaming', 'office', 'creative', 'programming', 'general']
        return purpose in valid_purposes

    @staticmethod
    def validate_performance_level(level: str) -> bool:
        """Validate performance level input"""
        valid_levels = ['basic', 'standard', 'high', 'professional']
        return level in valid_levels


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT Authentication middleware"""

    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.split(" ")[1]

        # Validate token
        from app.api.services.auth_service import auth_service
        token_data = auth_service.verify_token(token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Add user info to request state
        request.state.user_id = token_data.user_id
        request.state.email = token_data.email
        request.state.token_type = token_data.token_type

        # Check rate limiting
        client_id = request.state.user_id or request.client.host
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )

        response = await call_next(request)
        return response


# Global instances
rate_limiter = RateLimiter()
input_validator = InputValidator()