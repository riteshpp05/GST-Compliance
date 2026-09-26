"""
app.security.exceptions
=======================
Structured security and authorization exceptions for UC15 (Sprint 16).
"""

from typing import Optional


class SecurityException(Exception):
    """Base class for all security-related exceptions in UC15."""
    def __init__(self, message: str, code: str = "SECURITY_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AuthenticationException(SecurityException):
    """Raised when authentication fails or credentials are missing/invalid."""
    def __init__(self, message: str = "Authentication credentials were not provided or are invalid.") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR", status_code=401)


class ForbiddenException(SecurityException):
    """Raised when an authenticated principal attempts an unauthorized action."""
    def __init__(self, message: str = "Operation forbidden: insufficient permissions.") -> None:
        super().__init__(message, code="FORBIDDEN_ERROR", status_code=403)


class CaseAccessDeniedException(ForbiddenException):
    """Raised when a principal is denied access to a specific case (e.g. cross-tenant)."""
    def __init__(self, message: str = "Access to the requested case is denied.") -> None:
        super().__init__(message)
        self.code = "CASE_ACCESS_DENIED"
        self.status_code = 403


class ToolPermissionDeniedException(ForbiddenException):
    """Raised when a principal lacks permission to execute a specific tool."""
    def __init__(self, tool_name: str, message: Optional[str] = None) -> None:
        msg = message or f"Permission denied for tool execution: '{tool_name}'."
        super().__init__(msg)
        self.code = "TOOL_PERMISSION_DENIED"
        self.tool_name = tool_name
        self.status_code = 403


class ToolExecutionTimeoutException(SecurityException):
    """Raised when a tool execution exceeds its configured timeout boundary."""
    def __init__(self, tool_name: str, timeout_seconds: float) -> None:
        super().__init__(
            f"Tool '{tool_name}' execution timed out after {timeout_seconds}s.",
            code="TOOL_TIMEOUT",
            status_code=504,
        )
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds


class ToolInputValidationException(SecurityException):
    """Raised when tool input arguments fail schema validation."""
    def __init__(self, tool_name: str, errors: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' input validation failed: {errors}",
            code="TOOL_INPUT_INVALID",
            status_code=422,
        )
        self.tool_name = tool_name


class ToolOutputValidationException(SecurityException):
    """Raised when tool output payload fails schema validation."""
    def __init__(self, tool_name: str, errors: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' output validation failed: {errors}",
            code="TOOL_OUTPUT_INVALID",
            status_code=500,
        )
        self.tool_name = tool_name
