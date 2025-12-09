"""Custom decorators for route handlers."""
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, Request
from app.core.security import verify_firebase_token


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Usage:
        @router.get("/protected")
        @require_auth
        def protected_route(request: Request):
            # request will have verified user info
            return {"message": "authenticated"}
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find Request object in kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            request = kwargs.get("request")
        
        if not request:
            raise HTTPException(
                status_code=500,
                detail="Request object not found"
            )
        
        # Verify token and add user info to kwargs
        user_data = verify_firebase_token(request)
        kwargs["current_user"] = user_data
        
        return await func(*args, **kwargs) if hasattr(func, "__call__") else func(*args, **kwargs)
    
    return wrapper


def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator to handle common exceptions in routes.
    
    Usage:
        @router.get("/endpoint")
        @handle_exceptions
        def endpoint():
            # Your code here
            pass
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(*args, **kwargs) if hasattr(func, "__call__") else func(*args, **kwargs)
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )
    
    return wrapper

