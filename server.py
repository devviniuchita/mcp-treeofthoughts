"""Servidor MCP TreeOfThoughts MINIMALISTA - FastMCP Cloud Pure."""

from fastmcp import FastMCP

# ZERO configuração de autenticação - deixar FastMCP Cloud gerenciar 100%
mcp = FastMCP("MCP TreeOfThoughts Minimal")

@mcp.tool
def ping() -> str:
    """Simple ping tool to test authentication."""
    return "pong"

@mcp.tool 
def echo(message: str) -> str:
    """Echo the provided message."""
    return f"Echo: {message}"

if __name__ == "__main__":
    mcp.run()