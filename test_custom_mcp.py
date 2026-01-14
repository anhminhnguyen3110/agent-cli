#!/usr/bin/env python3
"""Test custom MCP loader"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs", "deepagents-cli"))

from deepagents_cli.mcp_loader_custom import load_mcp_tools_custom

async def main():
    print("=" * 70)
    print("Testing Custom MCP Loader")
    print("=" * 70)
    print()
    
    tools = await load_mcp_tools_custom()
    
    if tools:
        print("\n" + "=" * 70)
        print(f"[SUCCESS] Loaded {len(tools)} tools")
        print("=" * 70)
        print("\nTools list:")
        for i, tool in enumerate(tools, 1):
            print(f"{i:2}. {tool.name}: {tool.description[:70]}...")
        
        # Test calling first tool if available
        if len(tools) > 0:
            print("\n" + "=" * 70)
            print("Testing tool execution:")
            print("=" * 70)
            
            # Test filesystem read
            fs_read_tool = next((t for t in tools if "read_text_file" in t.name), None)
            if fs_read_tool:
                print(f"\nCalling: {fs_read_tool.name}")
                try:
                    result = await fs_read_tool.ainvoke({"path": "C:/Users/admin/Desktop/deepagents/README.md"})
                    print(f"Result (first 200 chars): {str(result)[:200]}...")
                    print(f"[OK] Tool execution successful!")
                except Exception as e:
                    print(f"Error: {e}")
            
            # Test brave search
            search_tool = next((t for t in tools if "web_search" in t.name), None)
            if search_tool:
                print(f"\nCalling: {search_tool.name}")
                try:
                    result = await search_tool.ainvoke({"query": "Python programming"})
                    print(f"Result (first 200 chars): {str(result)[:200]}...")
                    print(f"[OK] Tool execution successful!")
                except Exception as e:
                    print(f"Error: {e}")
    else:
        print("\n[X] No tools loaded")

if __name__ == "__main__":
    asyncio.run(main())
