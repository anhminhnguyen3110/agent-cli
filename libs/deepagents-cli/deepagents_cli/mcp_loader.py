"""MCP (Model Context Protocol) configuration loader for Deep Agents CLI.

This module handles loading and parsing mcp.json configuration files to
integrate MCP servers as tools in the agent using langchain-mcp-adapters.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
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
    """Load MCP configuration from a JSON file.

    Args:
        config_path: Path to mcp.json file

    Returns:
        MCPConfig object if successful, None otherwise
    """
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


def load_mcp_config(config_path: str | Path) -> MCPConfig | None:
    """Load MCP configuration from a JSON file.

    Args:
        config_path: Path to mcp.json file

    Returns:
        MCPConfig object if successful, None otherwise
    """
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


async def load_mcp_tools(config_path: str | Path | None = None) -> list[BaseTool]:
    """Load all MCP servers from configuration as LangChain tools.

    Uses langchain-mcp-adapters MultiServerMCPClient to properly handle
    MCP protocol communication.

    Args:
        config_path: Path to mcp.json. If None, looks in standard locations.

    Returns:
        List of LangChain BaseTool objects ready to use with the agent
    """
    if config_path is None:
        config_path = find_mcp_config()
        if not config_path:
            return []

    config = load_mcp_config(config_path)
    if not config:
        return []

    # Convert MCP config to MultiServerMCPClient format
    connections = {}
    for server_name, server_config in config.mcpServers.items():
        # On Windows, wrap npx commands with cmd.exe for proper process spawning
        import sys
        command = server_config.command
        args = server_config.args
        
        if sys.platform == "win32" and command in ["npx", "node"]:
            # Windows needs cmd.exe /c to run .cmd files
            command = "cmd.exe"
            args = ["/c", "npx"] + args
        
        # Determine transport type based on command
        if command.startswith("http"):
            # HTTP-based MCP server
            connections[server_name] = {
                "url": command,
                "transport": "http",
                "env": server_config.env if server_config.env else {},
            }
        else:
            # stdio transport for local commands
            connections[server_name] = {
                "command": command,
                "args": args,
                "transport": "stdio",
                "env": server_config.env if server_config.env else {},
            }

    # Create MCP client and load tools
    try:
        client = MultiServerMCPClient(connections)
        tools = await client.get_tools()
        
        print(f"✓ Loaded {len(tools)} tool(s) from {len(connections)} MCP server(s)")
        for server_name in connections.keys():
            print(f"  - {server_name}")
        
        return tools
    except Exception as e:
        print(f"✗ Failed to load MCP tools: {e}")
        import traceback
        traceback.print_exc()
        return []


def find_mcp_config() -> Path | None:
    """Find mcp.json in common locations.

    Searches in order (for end users with wheel installation):
    1. ~/.deepagents/mcp.json (PRIMARY - user config)
    2. ~/.config/deepagents/mcp.json
    3. Current working directory (for development)
    4. Project root (if .git exists, for development)

    Returns:
        Path to mcp.json if found, None otherwise
    """
    search_paths = [
        # User config directory - PRIMARY location for end users
        Path.home() / ".deepagents" / "mcp.json",
        Path.home() / ".config" / "deepagents" / "mcp.json",
        # Development/local configs (lower priority)
        Path.cwd() / "mcp.json",
    ]

    # Try to find project root (for development)
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
