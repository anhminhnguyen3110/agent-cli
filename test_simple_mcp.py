#!/usr/bin/env python3
"""Simple test with filesystem server"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    print("Testing filesystem MCP server...")
    
    # On Windows, use cmd.exe wrapper
    import sys
    if sys.platform == "win32":
        command = "cmd.exe"
        args = ["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", "C:/Users/admin/Desktop"]
    else:
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/admin/Desktop"]
    
    client = MultiServerMCPClient({
        "filesystem": {
            "command": command,
            "args": args,
            "transport": "stdio",
            "env": {}
        }
    })
    
    try:
        print("Loading tools...")
        tools = await client.get_tools()
        print(f"✓ Loaded {len(tools)} tools:")
        for tool in tools[:10]:  # Show first 10
            print(f"  - {tool.name}: {tool.description[:60]}...")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
