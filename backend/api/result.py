"""Result type for API responses to avoid exception-based control flow."""

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

T = TypeVar("T")


@dataclass
class Success(Generic[T]):
    """Successful API result."""
    
    data: T
    status_code: int = 200
    
    def is_success(self) -> bool:
        return True
    
    def is_error(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        """Get the data value (safe for Success)."""
        return self.data
    
    def unwrap_or(self, default: T) -> T:
        """Get data or default (returns data for Success)."""
        return self.data


@dataclass
class Error:
    """Failed API result with error details."""
    
    message: str
    status_code: int = 500
    error_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    
    def is_success(self) -> bool:
        return False
    
    def is_error(self) -> bool:
        return True
    
    def unwrap(self) -> Any:
        """Raises RuntimeError (unsafe for Error)."""
        raise RuntimeError(f"Called unwrap() on Error: {self.message}")
    
    def unwrap_or(self, default: Any) -> Any:
        """Get data or default (returns default for Error)."""
        return default


# Type alias for API results
Result = Union[Success[T], Error]


def success(data: T, status_code: int = 200) -> Success[T]:
    """Create a Success result."""
    return Success(data=data, status_code=status_code)


def error(
    message: str,
    status_code: int = 500,
    error_code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Error:
    """Create an Error result."""
    return Error(
        message=message,
        status_code=status_code,
        error_code=error_code,
        details=details,
    )


# Common error constructors
def auth_error(message: str, code: Optional[int] = None) -> Error:
    """Create an authentication error (401)."""
    return error(message, status_code=401, error_code=code)


def not_found_error(message: str) -> Error:
    """Create a not found error (404)."""
    return error(message, status_code=404)


def upstream_error(message: str, status: int = 502) -> Error:
    """Create an upstream/gateway error (502/503)."""
    return error(message, status_code=status)


def validation_error(message: str, details: Optional[Dict] = None) -> Error:
    """Create a validation error (400)."""
    return error(message, status_code=400, details=details)

