"""Servidor temporário para TestSprite validation."""

import logging

from flask import Flask
from flask import jsonify
from flask import request

from src.exceptions import ExecutionNotFoundError
from src.exceptions import ExecutionStateError
from src.execution_manager import ExecutionManager
from src.jwt_manager import JWTManager


# Initialize enterprise components
jwt_manager = JWTManager()
execution_manager = ExecutionManager()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": "MCP TreeOfThoughts Enterprise",
            "version": "2.0.0",
        }
    )


@app.route('/api/iniciar_processo', methods=['POST'])
def iniciar_processo():
    """Start Tree of Thoughts process."""
    data = request.get_json()
    try:
        run_id = execution_manager.create_execution(
            instruction=data.get('instrucao', ''),
            constraints=data.get('restricoes'),
            task_id=data.get('task_id'),
            max_depth=data.get('max_depth', 3),
            branching_factor=data.get('branching_factor', 2),
            beam_width=data.get('beam_width', 2),
            max_nodes=data.get('max_nodes', 50),
            max_time_seconds=data.get('max_time_seconds', 60),
            strategy=data.get('strategy', 'beam_search'),
        )

        return jsonify(
            {
                "success": True,
                "run_id": run_id,
                "message": f"Processo iniciado com sucesso. ID: {run_id}",
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/status/<run_id>', methods=['GET'])
def verificar_status(run_id):
    """Check execution status."""
    try:
        status_info = execution_manager.get_execution_status(run_id)
        return jsonify(status_info)

    except ExecutionNotFoundError:
        return jsonify({"error": f"Execução {run_id} não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/resultado/<run_id>', methods=['GET'])
def obter_resultado(run_id):
    """Get execution result."""
    try:
        result_info = execution_manager.get_execution_result(run_id)
        return jsonify(result_info)

    except ExecutionNotFoundError:
        return jsonify({"error": f"Execução {run_id} não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/cancelar/<run_id>', methods=['POST'])
def cancelar_execucao(run_id):
    """Cancel execution."""
    try:
        execution_manager.cancel_execution(run_id)
        return jsonify(
            {"success": True, "message": f"Execução {run_id} cancelada com sucesso"}
        )

    except (ExecutionNotFoundError, ExecutionStateError) as e:
        return jsonify({"success": False, "error": e.message}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/listar', methods=['GET'])
def listar_execucoes():
    """List all executions."""
    try:
        executions_data = execution_manager.list_executions()
        return jsonify(executions_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/token/novo', methods=['POST'])
def gerar_token():
    """Generate new JWT token."""
    try:
        token = jwt_manager.generate_new_token()
        return jsonify({"success": True, "token": token, "expires_in": 3600})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/token/atual', methods=['GET'])
def obter_token():
    """Get current JWT token."""
    try:
        token = jwt_manager.get_current_token()
        return jsonify({"success": True, "token": token})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting MCP TreeOfThoughts Enterprise Server for TestSprite...")
    print("🔐 JWT Authentication enabled")
    print("🏗️ Enterprise architecture loaded")
    print("📡 Server starting on port 5173...")

    app.run(host='0.0.0.0', port=5173, debug=False)
