"""Simple tests for JWKS endpoint using validation server."""

import sys

from pathlib import Path


# Add project root to path to import validation_server
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from validation_server import app


def test_jwks_endpoint():
    """Test /.well-known/jwks.json endpoint."""
    print("🔍 Testando /.well-known/jwks.json")

    with app.test_client() as client:
        response = client.get('/.well-known/jwks.json')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")

        assert response.status_code == 200
        assert response.content_type == 'application/json'


def test_health_endpoint():
    """Test /health endpoint."""
    print("\n🔍 Testando /health")

    with app.test_client() as client:
        response = client.get('/health')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")

        assert response.status_code in [200, 503]  # Can be unhealthy in tests
        assert response.content_type == 'application/json'


if __name__ == '__main__':
    print("🧪 Testando endpoint JWKS...")
    test_jwks_endpoint()
    test_health_endpoint()
    print("\n✅ Testes concluídos!")
