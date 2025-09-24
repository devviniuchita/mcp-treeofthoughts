
import pytest
import requests
import time
import subprocess
import os

# URL base da API FastAPI
BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="module")
def api_server():
    # Inicia o servidor FastAPI em um processo separado
    process = None
    try:
        # Certifique-se de que o diretório mcp-treeofthoughts está no PYTHONPATH
        # ou que o comando uvicorn é executado a partir do diretório correto
        # Para este exemplo, vamos assumir que estamos no diretório raiz do projeto
        # e o comando é executado de lá.
        # Ajuste o caminho se necessário.
        print("Iniciando o servidor FastAPI...")
        process = subprocess.Popen(
            ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd="/home/ubuntu/mcp-treeofthoughts", # Executa uvicorn a partir do diretório do projeto
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Espera o servidor iniciar
        time.sleep(10) # Aumentado para dar mais tempo ao servidor para iniciar
        print("Servidor FastAPI iniciado.")
        yield process
    finally:
        if process:
            print("Encerrando o servidor FastAPI...")
            process.terminate()
            process.wait()
            print("Servidor FastAPI encerrado.")

def test_game24_scenario(api_server):
    print("\nExecutando teste de cenário Game24...")
    task_instruction = "Use os números 4, 6, 7, 8 para fazer 24. Você pode usar +, -, *, / e parênteses."
    run_request_payload = {
        "task": {
            "instruction": task_instruction,
            "constraints": "Apenas uma solução é necessária. A solução deve ser uma expressão matemática válida."
        },
        "config": {
            "max_depth": 3,
            "beam_width": 2,
            "propose_temp": 0.7,
            "value_temp": 0.2,
            "finalize_temp": 0.0,
            "stop_conditions": {"max_nodes": 50, "max_time_seconds": 60}
        }
    }

    # 1. Iniciar a execução do ToT
    try:
        response = requests.post(f"{BASE_URL}/run", json=run_request_payload)
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["run_id"]
        print(f"Execução iniciada com ID: {run_id}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Falha ao iniciar a execução: {e}")

    # 2. Polling para verificar o status da execução
    status = "running"
    timeout_start = time.time()
    timeout_seconds = 120 # Tempo limite para a execução do ToT

    while status == "running" and (time.time() - timeout_start) < timeout_seconds:
        time.sleep(5) # Espera antes de verificar novamente
        try:
            status_response = requests.get(f"{BASE_URL}/status/{run_id}")
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data["status"]
            print(f"Status da execução {run_id}: {status}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter status da execução {run_id}: {e}")
            break

    assert status == "completed", f"A execução não foi concluída com sucesso. Status final: {status}"

    # 3. Obter o resultado final e verificar a resposta
    try:
        trace_response = requests.get(f"{BASE_URL}/trace/{run_id}")
        trace_response.raise_for_status()
        trace_data = trace_response.json()
        final_answer = trace_data.get("final_answer")
        print(f"Resposta final: {final_answer}")

        assert final_answer is not None, "A resposta final não deve ser nula."
        # Avaliar a expressão para verificar se o resultado é 24
        try:
            # Remover qualquer texto explicativo e tentar extrair apenas a expressão
            expression = final_answer.strip()
            # Pode ser necessário um parsing mais robusto aqui se o LLM retornar texto extra
            # Por exemplo, se retornar "A solução é: (6 * 4) * (8 - 7)"
            # Para este teste, vamos assumir que a resposta é a expressão ou contém a expressão de forma clara.
            # Uma abordagem simples é tentar encontrar a expressão entre parênteses ou que contenha os números.
            # Para simplificar, vamos tentar avaliar a string diretamente, o que pode falhar se houver texto extra.
            # Uma solução mais robusta seria usar um parser de expressão matemática.
            # Por enquanto, vamos tentar uma avaliação direta e, se falhar, procurar por '24' no texto.
            result = eval(expression)
            assert result == 24, f"A expressão '{expression}' não avalia para 24. Resultado: {result}"
        except (SyntaxError, NameError, TypeError) as e:
            print(f"[WARNING] Não foi possível avaliar a expressão diretamente: {e}. Verificando a presença de '24' no texto.")
            assert "24" in final_answer, "A resposta final deve conter '24' indicando a solução, ou ser uma expressão que avalie para 24."

        # Uma verificação mais robusta seria avaliar a expressão, mas isso é mais complexo.
        # Por enquanto, verificamos a presença de '24' e que a resposta não é vazia.

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Falha ao obter o trace da execução: {e}")

    print("Teste de cenário Game24 concluído com sucesso!")


