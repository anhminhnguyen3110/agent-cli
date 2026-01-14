"""
Proper MCP (Model Context Protocol) client implementation.

MCP uses JSON-RPC 2.0 over stdio to communicate with servers.
This is a simplified implementation for basic tool integration.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
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


def call_mcp_server(server_config: MCPServerConfig, method: str, params: dict) -> Any:
    """Call an MCP server using JSON-RPC over stdio.
    
    Args:
        server_config: Server configuration
        method: JSON-RPC method name
        params: Method parameters
        
    Returns:
        Response from server
    """
    # Build command
    cmd = [server_config.command] + server_config.args
    
    # Prepare JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    try:
        # Start server process
        env = {**subprocess.os.environ, **server_config.env} if server_config.env else None
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            shell=(sys.platform == "win32")
        )
        
        # Send request
        stdout, stderr = process.communicate(
            input=json.dumps(request) + "\n",
            timeout=30
        )
        
        # Parse response
        if stderr:
            return {"error": f"Server error: {stderr}"}
            
        try:
            response = json.loads(stdout.strip())
            return response.get("result", response)
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON response: {stdout}"}
            
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}


def create_mcp_tool_simple(server_name: str, server_config: MCPServerConfig) -> StructuredTool:
    """Create a simplified MCP tool that lists available tools.
    
    For full MCP integration, we'd need to:
    1. Initialize connection with server
    2. List available tools
    3. Get tool schemas
    4. Create individual tools for each
    
    This simplified version just shows the concept.
    """
    
    def run_mcp_command(command: str) -> str:
        """Execute a command on the MCP server."""
        try:
            # Try to list available tools first
            result = call_mcp_server(server_config, "tools/list", {})
            
            if "error" in result:
                return f"MCP Server '{server_name}' error: {result['error']}"
                
            # Return available tools
            if isinstance(result, dict) and "tools" in result:
                tools_list = result["tools"]
                return f"Available tools in '{server_name}':\n" + "\n".join(
                    f"- {t.get('name', 'unknown')}: {t.get('description', 'no description')}"
                    for t in tools_list
                )
            
            return f"Connected to '{server_name}' server. Response: {json.dumps(result, indent=2)}"
            
        except Exception as e:
            return f"Error calling MCP server '{server_name}': {str(e)}"
    
    return StructuredTool.from_function(
        func=run_mcp_command,
        name=f"mcp_{server_name}_list",
        description=f"List available tools from MCP server '{server_name}' ({server_config.command})",
    )


def load_mcp_tools(config_path: str | Path | None = None) -> list[StructuredTool]:
    """Load MCP servers as tools.
    
    Note: This is a simplified implementation. Full MCP integration would require:
    - Persistent server connections
    - Proper JSON-RPC session management
    - Dynamic tool schema discovery
    - Tool result streaming
    """
    if config_path is None:
        config_path = find_mcp_config()
        if not config_path:
            return []

    config = load_mcp_config(config_path)
    if not config:
        return []

    tools = []
    for server_name, server_config in config.mcpServers.items():
        try:
            tool = create_mcp_tool_simple(server_name, server_config)
            tools.append(tool)
            print(f"✓ Loaded MCP server: {server_name}")
        except Exception as e:
            print(f"✗ Failed to load MCP server '{server_name}': {e}")

    return tools


def find_mcp_config() -> Path | None:
    """Find mcp.json in common locations."""
    search_paths = [
        Path.home() / ".agentscli" / "mcp.json",
        Path.home() / ".config" / "agentscli" / "mcp.json",
        Path.cwd() / "mcp.json",
    ]

    # Try to find project root
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            search_paths.append(current / "mcp.json")
            break
        current = current.parent

    for path in search_paths:
        if path.exists():
            return path

    return None
