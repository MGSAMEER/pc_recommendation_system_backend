# Services package
from .auth_service import auth_service
from .user_service import user_service
from .recommendation_engine import recommendation_engine

__all__ = [
    "auth_service",
    "user_service",
    "recommendation_engine",
]

