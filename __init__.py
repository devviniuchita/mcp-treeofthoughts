"""Mcp TreeOfThoughts package initializer."""

__version__ = "1.0.0"
__author__ = "Seu Nome"
__description__ = "MCP TreeOfThoughts - Raciocínio Avançado para LLMs"

# Importações principais para facilitar o uso do package
try:
    from .server import mcp
    from .src.graph import create_tot_graph
    from .src.models import GraphState
    from .src.models import RunConfig
    from .src.models import RunTask

    __all__ = [
        "mcp",
        "GraphState",
        "RunConfig",
        "RunTask",
        "create_tot_graph",
        "__version__",
    ]
except ImportError:
    # Se as importações falharem (ex: durante install), apenas definir version
    __all__ = ["__version__"]

# Configuração de logging para desenvolvimento
import logging
import os


# Configurar logging baseado em variável de ambiente
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Logger específico do projeto
logger = logging.getLogger("mcp_treeofthoughts")

# Suprimir logs verbose de libraries externas em produção
if log_level != "DEBUG":
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langsmith").setLevel(logging.WARNING)
