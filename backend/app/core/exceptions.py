from typing import Any, Optional


class FaceLogixException(Exception):
    """Base exception for FaceLogix application."""
    
    def __init__(
        self,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(FaceLogixException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details
        )


class AuthorizationError(FaceLogixException):
    """Raised when user lacks required permissions."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        code: str = "AUTHORIZATION_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=403,
            details=details
        )


class NotFoundError(FaceLogixException):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            code=code,
            status_code=404,
            details=details if details else None
        )


class ValidationError(FaceLogixException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        errors: Optional[list] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=422,
            details={"errors": errors} if errors else None
        )


class ConflictError(FaceLogixException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(
        self,
        message: str = "Resource already exists",
        code: str = "CONFLICT",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=409,
            details=details
        )


class RateLimitError(FaceLogixException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=429,
            details={"retry_after": retry_after} if retry_after else None
        )


class FaceServiceError(FaceLogixException):
    """Raised when face recognition service fails."""
    
    def __init__(
        self,
        message: str = "Face service error",
        code: str = "FACE_SERVICE_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=503,
            details=details
        )


class DeviceError(FaceLogixException):
    """Raised for device-related errors."""
    
    def __init__(
        self,
        message: str = "Device error",
        code: str = "DEVICE_ERROR",
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details
        )


class DatabaseError(FaceLogixException):
    """Raised when database operations fail."""
    
    def __init__(
        self,
        message: str = "Database error",
        code: str = "DATABASE_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )
