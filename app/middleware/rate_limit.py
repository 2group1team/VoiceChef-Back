from fastapi import FastAPI, Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Callable, Optional
from functools import wraps
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CustomLimiter(Limiter):
    def __init__(self, key_func=get_remote_address, **kwargs):
        super().__init__(key_func=key_func, **kwargs)

    async def handle_request_limit_exceeded(self, request: Request, exc: RateLimitExceeded):

        logger.warning(
            f"Rate limit exceeded for IP {request.client.host} "
            f"on endpoint {request.url.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Too many requests",
                "message": str(exc)
            }
        )


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: CustomLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            return await self.limiter.handle_request_limit_exceeded(request, e)


limiter = CustomLimiter(key_func=get_client_ip)


def rate_limit(
        calls: int,
        period: str,
        key_func: Optional[Callable] = None,
        error_message: Optional[str] = None
) -> Callable:
    if period not in ["second", "minute", "hour", "day"]:
        raise ValueError("Invalid period. Use 'second', 'minute', 'hour' or 'day'")

    def decorator(func: Callable) -> Callable:
        @limiter.limit(
            f"{calls}/{period}",
            key_func=key_func,
            error_message=error_message
        )
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except RateLimitExceeded as e:
                request = kwargs.get('request') or args[0]
                await limiter.handle_request_limit_exceeded(request, e)
            except Exception as e:
                logger.error(f"Error in rate limited function: {str(e)}")
                raise

        return wrapper

    return decorator


def setup_rate_limiting(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
