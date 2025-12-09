"""Custom exceptions for the application."""
from fastapi import HTTPException


class AppException(HTTPException):
    """Base application exception."""
    pass


class AuthenticationError(AppException):
    """Authentication related errors."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(AppException):
    """Authorization related errors."""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=403, detail=detail)


class NotFoundError(AppException):
    """Resource not found errors."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class ValidationError(AppException):
    """Validation errors."""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=400, detail=detail)

