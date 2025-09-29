"""Constants configuration for MCP TreeOfThoughts."""

from typing import Final
from typing import List


# JWT Configuration Constants
JWT_ISSUER: Final[str] = "https://mcptreeofthoughts.fastmcp.app"
JWT_AUDIENCE: Final[str] = "mcp-production-api"
JWT_EXPIRY_SECONDS: Final[int] = 3600

# OAuth2 Scopes
SCOPE_READ_TOOLS: Final[str] = "read:tools"
SCOPE_EXECUTE_TOOLS: Final[str] = "execute:tools"
SCOPE_READ_RESOURCES: Final[str] = "read:resources"

JWT_DEFAULT_SCOPES: Final[List[str]] = [
    SCOPE_READ_TOOLS,
    SCOPE_EXECUTE_TOOLS,
    SCOPE_READ_RESOURCES,
]

# File Configuration
TOKEN_FILE_PATH: Final[str] = "current_token.txt"
DEFAULTS_FILE_PATH: Final[str] = "defaults.json"

# Execution Configuration
MAX_WIP_LIMIT: Final[int] = 3  # Kanban WIP limit
DEFAULT_MAX_DEPTH: Final[int] = 3
DEFAULT_BRANCHING_FACTOR: Final[int] = 2
DEFAULT_BEAM_WIDTH: Final[int] = 2
DEFAULT_MAX_NODES: Final[int] = 50
DEFAULT_MAX_TIME_SECONDS: Final[int] = 60

# Quality Metrics
MAX_COMPLEXITY: Final[int] = 15
MAX_LINE_LENGTH: Final[int] = 88
MIN_TEST_COVERAGE: Final[float] = 0.90

# Error Messages
ERROR_EXECUTION_NOT_FOUND: Final[str] = "Execução com ID {run_id} não encontrada."
ERROR_EXECUTION_NOT_RUNNING: Final[str] = (
    "Execução {run_id} não está em andamento (status: {status})."
)
ERROR_KEY_PAIR_NOT_CONFIGURED: Final[str] = "Key pair não configurado."
ERROR_TOKEN_GENERATION_FAILED: Final[str] = "Erro ao gerar token: {error}"
