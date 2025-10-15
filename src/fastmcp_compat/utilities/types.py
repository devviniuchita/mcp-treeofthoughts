"""Compatibility types for FastMCP."""

from typing import Any


class NotSetType:
    """Sentinel type for unset values."""

    def __repr__(self) -> str:
        return "NotSet"

    def __bool__(self) -> bool:
        return False


# Singleton instance
NotSet = NotSetType()

# Type alias
NotSetT = type(NotSet)


__all__ = ["NotSet", "NotSetT"]
