from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """Generic response wrapper for API responses."""
    
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with calculated pages."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    success: bool = False
    error: str
    code: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
