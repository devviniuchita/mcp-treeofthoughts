"""Compatibility utilities for FastMCP."""


def parse_scopes(v):
    """Parse scopes from string or list."""
    if v is None:
        return None
    if isinstance(v, str):
        # Handle comma-separated or space-separated
        if ',' in v:
            return [s.strip() for s in v.split(',') if s.strip()]
        return [s.strip() for s in v.split() if s.strip()]
    if isinstance(v, list):
        return v
    return None


__all__ = ["parse_scopes"]
