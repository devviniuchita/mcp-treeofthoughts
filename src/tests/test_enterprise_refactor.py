"""Test isolado da nova arquitetura enterprise."""

import pytest

from src.config.constants import JWT_DEFAULT_SCOPES
from src.config.constants import JWT_ISSUER
from src.exceptions import ConfigurationError
from src.exceptions import ExecutionNotFoundError
from src.execution_manager import ExecutionManager
from src.jwt_manager import JWTManager


def test_constants_defined():
    """Test que constants estão definidas corretamente."""
    assert JWT_ISSUER == "https://mcptreeofthoughts.fastmcp.app"
    assert len(JWT_DEFAULT_SCOPES) == 3
    assert "read:tools" in JWT_DEFAULT_SCOPES


def test_jwt_manager_initialization():
    """Test inicialização do JWT Manager."""
    jwt_manager = JWTManager()
    assert jwt_manager.auth_provider is not None
    assert jwt_manager.access_token is not None
    assert jwt_manager.key_pair is not None


def test_execution_manager_initialization():
    """Test inicialização do Execution Manager."""
    execution_manager = ExecutionManager()
    assert isinstance(execution_manager.active_runs, dict)
    assert len(execution_manager.active_runs) == 0


def test_execution_not_found_exception():
    """Test exception handling específico."""
    execution_manager = ExecutionManager()

    with pytest.raises(ExecutionNotFoundError):
        execution_manager.get_execution_status("invalid-id")

    with pytest.raises(ExecutionNotFoundError):
        execution_manager.get_execution_result("invalid-id")


def test_execution_manager_create_execution():
    """Test criação de execução com novos patterns."""
    execution_manager = ExecutionManager()

    run_id = execution_manager.create_execution(
        instruction="Test problem solving",
        constraints="Stay focused",
        max_depth=2,
        branching_factor=2,
        beam_width=1,
        max_nodes=10,
        max_time_seconds=30,
        strategy="beam_search",
    )

    assert isinstance(run_id, str)
    assert run_id in execution_manager.active_runs

    # Verificar status
    status_info = execution_manager.get_execution_status(run_id)
    assert status_info["status"] == "running"
    assert status_info["run_id"] == run_id


def test_jwt_token_generation():
    """Test geração de tokens JWT."""
    jwt_manager = JWTManager()

    # Test token atual
    token1 = jwt_manager.get_current_token()
    assert isinstance(token1, str)
    assert len(token1) > 100  # JWT tokens são longos

    # Test novo token
    token2 = jwt_manager.generate_new_token()
    assert isinstance(token2, str)
    assert token1 != token2  # Tokens diferentes


def test_execution_manager_list_empty():
    """Test listagem de execuções vazia."""
    execution_manager = ExecutionManager()

    executions_data = execution_manager.list_executions()
    assert executions_data["total"] == 0
    assert executions_data["executions"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
