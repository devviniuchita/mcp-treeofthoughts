"""Custom exception classes for MCP TreeOfThoughts following enterprise patterns."""

from typing import Any
from typing import Optional


class MCPTreeOfThoughtsException(Exception):
    """Base exception for all MCP TreeOfThoughts errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(MCPTreeOfThoughtsException):
    """Raised when JWT authentication fails."""

    pass


class ConfigurationError(MCPTreeOfThoughtsException):
    """Raised when configuration is invalid or missing."""

    pass


class ExecutionNotFoundError(MCPTreeOfThoughtsException):
    """Raised when trying to access a non-existent execution."""

    pass


class ExecutionStateError(MCPTreeOfThoughtsException):
    """Raised when execution is in an invalid state for the requested operation."""

    pass


class LLMClientError(MCPTreeOfThoughtsException):
    """Raised when LLM client encounters errors."""

    pass


class CacheError(MCPTreeOfThoughtsException):
    """Raised when semantic cache operations fail."""

    pass


class GraphExecutionError(MCPTreeOfThoughtsException):
    """Raised when Tree of Thoughts graph execution fails."""

    pass


class TokenGenerationError(MCPTreeOfThoughtsException):
    """Raised when JWT token generation fails."""

    pass


class ValidationError(MCPTreeOfThoughtsException):
    """Raised when input validation fails."""

    pass
