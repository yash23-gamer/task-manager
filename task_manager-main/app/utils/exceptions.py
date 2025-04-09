from typing import Dict, Any
from werkzeug.exceptions import HTTPException

class CustomException(HTTPException):
    """
    Base exception class for application-specific errors.
    """
    def __init__(self, message: str, status_code: int = 400, request_id: str = None):
        super().__init__(description=message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the exception into a JSON response."""
        return {
            'error': self.message,
            'status_code': self.status_code,
            'request_id': self.request_id or 'no-request'
        }

class AuthenticationError(CustomException):
    """Raised for authentication-related errors."""
    def __init__(self, message: str = "Authentication failed", request_id: str = None):
        super().__init__(message, status_code=401, request_id=request_id)

class ResourceNotFoundError(CustomException):
    """Raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found", request_id: str = None):
        super().__init__(message, status_code=404, request_id=request_id)

class ValidationFailedError(CustomException):
    """Raised when input validation fails."""
    def __init__(self, message: str = "Input validation failed", request_id: str = None):
        super().__init__(message, status_code=400, request_id=request_id)

class RateLimitExceededError(CustomException):
    """Raised when the rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", request_id: str = None):
        super().__init__(message, status_code=429, request_id=request_id)