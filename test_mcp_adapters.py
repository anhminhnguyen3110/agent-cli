#!/usr/bin/env python3
"""Test MCP with langchain-mcp-adapters"""
import asyncio
import os
import sys

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs", "deepagents-cli"))

from deepagents_cli.mcp_loader import load_mcp_tools, find_mcp_config


async def main():
    print("=" * 70)
    print("Testing MCP with langchain-mcp-adapters")
    print("=" * 70)

    print("\n[1] Finding MCP config...")
    config_path = find_mcp_config()
    if config_path:
        print(f"   ✓ Found: {config_path}")
    else:
        print("   ✗ No mcp.json found")
        return

    print("\n[2] Loading MCP tools...")
    print("   (This will connect to MCP servers)")
    tools = await load_mcp_tools(config_path)

    print(f"\n[3] Loaded {len(tools)} tool(s):")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description[:80]}...")

    print("\n" + "=" * 70)
    print(f"✅ SUCCESS! Loaded {len(tools)} tools via langchain-mcp-adapters")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
