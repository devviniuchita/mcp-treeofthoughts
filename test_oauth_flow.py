#!/usr/bin/env python3
"""Cliente OAuth correto para FastMCP Cloud."""

import base64
import hashlib
import json
import secrets

from urllib.parse import parse_qs
from urllib.parse import urlencode

import requests


class EnterpriseOAuth2Client:
    """Enterprise OAuth 2.0 client com PKCE e security compliance."""

    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.discovery_url = f"{self.server_url}/.well-known/oauth-authorization-server"
        self.client_info = None
        self.timeout = timeout
        self.session = requests.Session()

        # Enterprise security headers
        self.session.headers.update({
            "User-Agent": "EnterpriseOAuth2Client/2.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        })

    def discover_endpoints(self):
        """Descobre endpoints OAuth do servidor."""
        response = requests.get(self.discovery_url)
        response.raise_for_status()
        return response.json()

    def register_client(self):
        """Registra cliente OAuth dinamicamente."""
        endpoints = self.discover_endpoints()

        registration_data = {
            "client_name": "FastMCP Test Client",
            "redirect_uris": ["http://localhost:8080/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid profile email",
            "token_endpoint_auth_method": "none",
        }

        response = requests.post(
            endpoints["registration_endpoint"],
            json=registration_data,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 201:
            self.client_info = response.json()
            print(f"✅ Cliente registrado: {self.client_info['client_id']}")
            return self.client_info
        else:
            print(f"❌ Erro no registro: {response.status_code} - {response.text}")
            return None

    def get_authorization_url(self):
        """Gera URL de autorização."""
        if not self.client_info:
            raise Exception("Cliente não registrado")

        endpoints = self.discover_endpoints()

        # PKCE
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
        )
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .rstrip('=')
        )

        params = {
            "response_type": "code",
            "client_id": self.client_info["client_id"],
            "redirect_uri": "http://localhost:8080/callback",
            "scope": "openid profile email",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": secrets.token_urlsafe(32),
        }

        auth_url = f"{endpoints['authorization_endpoint']}?{urlencode(params)}"
        return auth_url, code_verifier

    def test_oauth_flow(self):
        """Testa fluxo OAuth completo."""
        print("🔧 Testando fluxo OAuth com FastMCP Cloud...")

        # 1. Descobrir endpoints
        endpoints = self.discover_endpoints()
        print(f"📡 Endpoints descobertos: {list(endpoints.keys())}")

        # 2. Registrar cliente
        client_info = self.register_client()
        if not client_info:
            return False

        # 3. Gerar URL de autorização
        auth_url, code_verifier = self.get_authorization_url()
        print(f"🔗 URL de autorização: {auth_url}")

        print("\n✅ Fluxo OAuth configurado com sucesso!")
        print("🎯 Para testar completamente, seria necessário:")
        print("   1. Abrir a URL no navegador")
        print("   2. Fazer login/autorização")
        print("   3. Capturar code do redirect")
        print("   4. Trocar code por token")

        return True


if __name__ == "__main__":
    client = EnterpriseOAuth2Client("https://mcptreeofthoughts.fastmcp.app")
    client.test_oauth_flow()
