import asyncio
import os
import sys

from dotenv import load_dotenv


load_dotenv()
AUTH = os.getenv("AUTH_TOKEN")
if not AUTH:
    print("ERROR: AUTH_TOKEN not set in environment (.env not loaded or missing).")
    sys.exit(2)

from fastmcp import Client


async def main():
    url = "https://mcptreeofthoughts.fastmcp.app/mcp"
    print("Using MCP URL:", url)
    print("Using AUTH_TOKEN: [REDACTED]")
    try:
        # FastMCP Client aceita parâmetro `auth` que pode ser uma string
        # contendo o valor do header Authorization (ex.: "Bearer <token>").
        client = Client(url, auth=f"Bearer {AUTH}")
        async with client:
            print("Pinging server...")
            await client.ping()
            print("Ping OK")

            print("Listing tools...")
            tools = await client.list_tools()
            print(
                "Tools count:", len(tools) if hasattr(tools, '__len__') else 'unknown'
            )

            # Print up to first 10 tool names safely
            def name_of(t):
                try:
                    if isinstance(t, dict) and 'name' in t:
                        return t['name']
                    return str(t)
                except Exception:
                    return repr(t)

            print(
                [
                    name_of(t)
                    for t in (tools[:10] if hasattr(tools, '__len__') else [tools])
                ]
            )

            print("Listing resources...")
            resources = await client.list_resources()
            print(
                "Resources count:",
                len(resources) if hasattr(resources, '__len__') else 'unknown',
            )
            print(
                [
                    name_of(r)
                    for r in (
                        resources[:10] if hasattr(resources, '__len__') else [resources]
                    )
                ]
            )

            # Optional: call a lightweight tool if exists
            example_tool = None
            for t in tools:
                try:
                    nm = t['name'] if isinstance(t, dict) and 'name' in t else None
                except Exception:
                    nm = None
                if nm and nm.lower() in (
                    "obter_configuracao_padrao",
                    "config://defaults",
                    "info://sobre",
                    "iniciar_processo_tot",
                ):
                    example_tool = nm
                    break
            if example_tool:
                print(f"Calling example tool: {example_tool}")
                try:
                    result = await client.call_tool(example_tool, {})
                    print("Tool result (preview):", str(result)[:1000])
                except Exception as e:
                    print("Tool call failed:", e)
            else:
                print("No example tool found to call; skipping call_tool.")

    except Exception as exc:
        print("ERROR: communication with MCP failed:", exc)
        raise


if __name__ == '__main__':
    asyncio.run(main())
