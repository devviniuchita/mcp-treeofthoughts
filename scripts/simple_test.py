#!/usr/bin/env python3
"""Teste simples de conectividade MCP usando requests."""

import json
import os

import requests

from dotenv import load_dotenv


load_dotenv()
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
if not AUTH_TOKEN:
    print("ERROR: AUTH_TOKEN not set in environment")
    exit(1)

url = "https://mcptreeofthoughts.fastmcp.app/mcp"
headers = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}

# Teste 1: List Tools
payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

print(f"🌐 Testing MCP server at: {url}")
print(f"🔑 Using AUTH_TOKEN: {AUTH_TOKEN[:10]}...{AUTH_TOKEN[-4:]}")
print()

try:
    print("📋 Testing tools/list...")
    response = requests.post(url, headers=headers, json=payload, timeout=10)

    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ SUCCESS! Response: {json.dumps(data, indent=2)}")

            if "result" in data and "tools" in data["result"]:
                tools = data["result"]["tools"]
                print(f"\n🛠️ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.get('name', 'unknown')}")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Raw response: {response.text}")
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")

print("\n🎯 Test completed!")
