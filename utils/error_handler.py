"""Error handling utilities for AgentCore Runtime."""

from typing import Dict, Any, Optional
from .logger import logger

def create_error_response(
    error_type: str,
    message: str,
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        error_type: Type of error (e.g., "Unauthorized", "Bad Request", "Internal Error")
        message: Human-readable error message
        details: Optional additional error details
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "error": error_type,
        "message": message,
    }
    
    if details:
        response["details"] = details
    
    logger.warning(f"Error response: {error_type} - {message}")
    
    return response

def handle_authentication_error(message: str = "Authentication required") -> Dict[str, Any]:
    """
    Handle authentication errors (401).
    
    Args:
        message: Custom error message
        
    Returns:
        401 error response
    """
    return create_error_response(
        error_type="Unauthorized",
        message=message,
        details="Please provide a valid JWT token in the Authorization header"
    )

def handle_validation_error(message: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle validation errors (400).
    
    Args:
        message: Error message
        details: Optional validation details
        
    Returns:
        400 error response
    """
    return create_error_response(
        error_type="Bad Request",
        message=message,
        details=details
    )

def handle_server_error(message: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle server errors (500).
    
    Args:
        message: Error message
        details: Optional error details
        
    Returns:
        500 error response
    """
    return create_error_response(
        error_type="Internal Error",
        message=message,
        details=details
    )
