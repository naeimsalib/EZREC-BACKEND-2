#!/usr/bin/env python3
"""
EZREC Custom Exception Classes
Provides structured error handling across the application
"""

from typing import Optional, Dict, Any

class EZRECException(Exception):
    """Base exception for EZREC application"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }

class CameraError(EZRECException):
    """Camera-related errors"""
    pass

class CameraNotAvailableError(CameraError):
    """Camera is not available"""
    pass

class CameraInitializationError(CameraError):
    """Camera initialization failed"""
    pass

class RecordingError(CameraError):
    """Recording operation failed"""
    pass

class BookingError(EZRECException):
    """Booking-related errors"""
    pass

class BookingNotFoundError(BookingError):
    """Booking not found"""
    pass

class BookingValidationError(BookingError):
    """Booking validation failed"""
    pass

class BookingConflictError(BookingError):
    """Booking time conflict"""
    pass

class VideoProcessingError(EZRECException):
    """Video processing errors"""
    pass

class VideoMergeError(VideoProcessingError):
    """Video merge operation failed"""
    pass

class VideoValidationError(VideoProcessingError):
    """Video validation failed"""
    pass

class UploadError(EZRECException):
    """Upload-related errors"""
    pass

class S3UploadError(UploadError):
    """S3 upload failed"""
    pass

class ConfigurationError(EZRECException):
    """Configuration-related errors"""
    pass

class DatabaseError(EZRECException):
    """Database operation errors"""
    pass

class ServiceError(EZRECException):
    """Service-related errors"""
    pass

class RetryableError(EZRECException):
    """Error that can be retried"""
    
    def __init__(self, message: str, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        super().__init__(message, **kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

def handle_exception(func):
    """Decorator to handle exceptions and convert to EZREC exceptions"""
    import functools
    import traceback
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EZRECException:
            # Re-raise EZREC exceptions as-is
            raise
        except Exception as e:
            # Convert other exceptions to EZREC exceptions
            error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
            raise ServiceError(error_msg, details={
                'function': func.__name__,
                'original_error': str(e),
                'traceback': traceback.format_exc()
            })
    
    return wrapper
