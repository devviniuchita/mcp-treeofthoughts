#!/usr/bin/env python3
"""Debug do problema de autenticação."""

import json

import requests


# Token exato do .env
TOKEN = " eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtY3AtY2xpZW50IiwiaXNzIjoiaHR0cHM6Ly9tY3B0cmVlb2Z0aG91Z2h0cy5mYXN0bWNwLmFwcCIsImlhdCI6MTc1ODk1NTU1MywiZXhwIjoxNzU4OTU5MTUzLCJhdWQiOiJtY3AtcHJvZHVjdGlvbi1hcGkiLCJzY29wZSI6InJlYWQ6dG9vbHMgZXhlY3V0ZTp0b29scyByZWFkOnJlc291cmNlcyJ9. IFMnOU1k--bSvED7Pu6SPo9GHLLFT5CyM2OOXkZDpGzjb9jDnHU2LD2t5LchX0-RSUYmaJKIrCWjqNoAf-oIRE3Mdo04iqO3tP538S-natLGNf3j42o_y6ZvLTCZ2m3EQtW4uPCXcrGzXAPnQV0kplECrCjqujG6HqDHfFouJaHjYX__JBJ2H9APXqZ-57vpwsW7SYVF3-jqrDFVaT2TVe4Zz-WawFjjfYCeq9iitCBW0NnD5rLQcSlnN9HW8pTc5wk0dCUHnvbBdmYFhCzbZyTYd4V6DzKgJR8eW0ecKWuS_E_2GkN8n6D6nScbUsr25o4RTG2oKZ-lc_snF-kfOg"
URL = "https://mcptreeofthoughts.fastmcp.app/mcp"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "DebugClient/1.0",
}

# Payload simples de teste
payload = {
    "jsonrpc": "2.0",
    "id": "debug-1",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "DebugClient", "version": "1.0"},
    },
}

print(f"🔑 Token sendo testado: {TOKEN}")
print(f"🌐 URL: {URL}")
print(f"📋 Headers: {headers}")
print()

try:
    response = requests.post(URL, headers=headers, json=payload, timeout=15)

    print(f"Status: {response.status_code}")
    print(f"Response headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print()

    try:
        data = response.json()
        print(f"Response JSON: {json.dumps(data, indent=2)}")
    except:
        print(f"Response text: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
