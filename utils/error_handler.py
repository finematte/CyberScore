"""
Error handling utilities for CyberScore
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import traceback
from utils.logger import get_logger

logger = get_logger(__name__)


class CyberScoreError(Exception):
    """Base exception for CyberScore"""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        details: Optional[Dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(CyberScoreError):
    """Validation error"""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})


class AuthenticationError(CyberScoreError):
    """Authentication error"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")


class AuthorizationError(CyberScoreError):
    """Authorization error"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "AUTHZ_ERROR")


class DatabaseError(CyberScoreError):
    """Database error"""

    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR", {"operation": operation})


class APIError(CyberScoreError):
    """API error"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, "API_ERROR", {"status_code": status_code})


def handle_error(error: Exception, request: Request = None) -> JSONResponse:
    """Handle errors and return appropriate response"""

    # Log the error
    logger.error(f"Error occurred: {str(error)}", exc_info=True)

    # Determine error type and response
    if isinstance(error, CyberScoreError):
        status_code = 400
        if isinstance(error, AuthenticationError):
            status_code = 401
        elif isinstance(error, AuthorizationError):
            status_code = 403
        elif isinstance(error, DatabaseError):
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "error": error.error_code,
                "message": error.message,
                "details": error.details,
            },
        )

    # Handle HTTP exceptions
    elif isinstance(error, HTTPException):
        return JSONResponse(
            status_code=error.status_code,
            content={"error": "HTTP_ERROR", "message": error.detail, "details": {}},
        )

    # Handle unexpected errors
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"traceback": traceback.format_exc()},
            },
        )


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present"""
    missing_fields = [
        field for field in required_fields if field not in data or data[field] is None
    ]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with default"""
    try:
        return data.get(key, default)
    except (KeyError, TypeError):
        return default
