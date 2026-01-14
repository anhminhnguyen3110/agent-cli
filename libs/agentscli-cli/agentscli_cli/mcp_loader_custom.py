"""
Custom MCP loader for Windows - bypasses stdio issues with langchain-mcp-adapters.

Uses direct subprocess communication instead of mcp SDK's stdio_client.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class MCPConfig(BaseModel):
    """Full MCP configuration from mcp.json."""
    mcpServers: dict[str, MCPServerConfig]


def load_mcp_config(config_path: str | Path) -> MCPConfig | None:
    """Load MCP configuration from a JSON file."""
    path = Path(config_path)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return MCPConfig(**data)
    except Exception as e:
        print(f"Warning: Failed to load MCP config from {path}: {e}")
        return None


async def call_mcp_rpc(server_config: MCPServerConfig, method: str, params: dict = None) -> dict:
    """Call MCP server with JSON-RPC request."""
    import sys
    
    # Build command - use cmd.exe on Windows for .cmd files
    if sys.platform == "win32" and server_config.command in ["npx", "node"]:
        cmd = ["cmd.exe", "/c", "npx"] + server_config.args
    else:
        cmd = [server_config.command] + server_config.args
    
    # JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    try:
        # Start process
        env = {**subprocess.os.environ, **server_config.env} if server_config.env else None
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Send request
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()
        
        # Read response from stdout (stderr has server logs)
        try:
            line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            
            if line:
                response = json.loads(line.decode())
                if "result" in response:
                    return response["result"]
                if "error" in response:
                    return {"error": response["error"]}
            
            return {"error": "No response from server"}
            
        except asyncio.TimeoutError:
            return {"error": "Response timeout"}
        
    except Exception as e:
        return {"error": str(e)}


async def get_mcp_tools_list(server_name: str, server_config: MCPServerConfig) -> list[dict]:
    """Get list of tools from MCP server."""
    # First initialize
    init_result = await call_mcp_rpc(server_config, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "agentscli-cli",
            "version": "0.0.12"
        }
    })
    
    if "error" in init_result:
        print(f"  [X] {server_name}: {init_result['error']}")
        return []
    
    # Then list tools
    tools_result = await call_mcp_rpc(server_config, "tools/list", {})
    
    if "error" in tools_result:
        print(f"  [X] {server_name}: {tools_result['error']}")
        return []
    
    tools = tools_result.get("tools", [])
    print(f"  [OK] {server_name}: {len(tools)} tools")
    return tools


def create_mcp_tool(server_name: str, server_config: MCPServerConfig, tool_info: dict) -> BaseTool:
    """Create a LangChain tool from MCP tool info."""
    
    tool_name = tool_info["name"]
    tool_description = tool_info.get("description", "")
    tool_schema = tool_info.get("inputSchema", {})
    
    async def run_tool(**kwargs) -> str:
        """Execute the MCP tool."""
        result = await call_mcp_rpc(server_config, "tools/call", {
            "name": tool_name,
            "arguments": kwargs
        })
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Extract content from result
        content = result.get("content", [])
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict):
                return first_item.get("text", str(first_item))
            return str(first_item)
        
        return str(result)
    
    return StructuredTool(
        name=f"{server_name}_{tool_name}",
        description=tool_description or f"Tool {tool_name} from {server_name}",
        coroutine=run_tool,
        args_schema=tool_schema if tool_schema else None
    )


async def load_mcp_tools_custom(config_path: str | Path | None = None) -> list[BaseTool]:
    """Load MCP tools using custom Windows-compatible implementation."""
    if config_path is None:
        from agentscli_cli.mcp_loader import find_mcp_config
        config_path = find_mcp_config()
        if not config_path:
            return []
    
    config = load_mcp_config(config_path)
    if not config:
        return []
    
    print(f"Loading MCP servers from: {config_path}")
    
    all_tools = []
    for server_name, server_config in config.mcpServers.items():
        try:
            tools_list = await get_mcp_tools_list(server_name, server_config)
            for tool_info in tools_list:
                tool = create_mcp_tool(server_name, server_config, tool_info)
                all_tools.append(tool)
        except Exception as e:
            print(f"  [X] {server_name}: {e}")
    
    print(f"\nTotal: {len(all_tools)} tools loaded")
    return all_tools


def find_mcp_config() -> Path | None:
    """Find mcp.json in standard locations."""
    search_paths = [
        Path.home() / ".agentscli" / "mcp.json",
        Path.home() / ".config" / "agentscli" / "mcp.json",
        Path.cwd() / "mcp.json",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None
