"""Teste simples do endpoint JWKS."""

from validation_server import app


if __name__ == '__main__':
    print("🧪 Testando endpoint JWKS...")

    with app.test_client() as client:
        print("🔍 Testando /.well-known/jwks.json")
        response = client.get('/.well-known/jwks.json')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")

        print("\n🔍 Testando /health")
        response2 = client.get('/health')
        print(f"Status: {response2.status_code}")
        print(f"Data: {response2.data.decode()}")
