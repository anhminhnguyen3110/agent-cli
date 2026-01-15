"""
Custom MCP loader for Windows - bypasses stdio issues with langchain-mcp-adapters.

Uses direct subprocess communication instead of mcp SDK's stdio_client.
Maintains persistent connections and implements full MCP protocol handshake.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field


class MCPServerConnection:
    """Maintains a persistent connection to an MCP server subprocess."""
    
    def __init__(self, server_config: 'MCPServerConfig'):
        self.config = server_config
        self.process: asyncio.subprocess.Process | None = None
        self._initialized = False
        self._request_id = 0
        
    async def __aenter__(self):
        """Start the MCP server subprocess."""
        import sys
        
        # Build command
        if sys.platform == "win32" and self.config.command in ["npx", "node"]:
            cmd = ["cmd.exe", "/c", "npx"] + self.config.args
        else:
            cmd = [self.config.command] + self.config.args
        
        # Start process
        env = {**subprocess.os.environ, **self.config.env} if self.config.env else None
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the subprocess."""
        if self.process:
            try:
                # Close stdin first to signal clean shutdown
                if self.process.stdin:
                    self.process.stdin.close()
                    await asyncio.sleep(0.1)  # Give process time to shutdown gracefully
                
                # Then terminate if still running
                if self.process.returncode is None:
                    self.process.terminate()
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        self.process.kill()
                        await self.process.wait()
            except Exception:
                # Suppress any cleanup errors
                pass
    
    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id
    
    async def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send JSON-RPC request and wait for response."""
        if not self.process:
            return {"error": "Connection not established"}
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params
        
        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0
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
    
    async def send_notification(self, method: str, params: dict | None = None) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self.process:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notification["params"] = params
        
        try:
            notification_str = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_str.encode())
            await self.process.stdin.drain()
        except Exception:
            pass
    
    async def initialize(self) -> bool:
        """Perform MCP handshake: initialize → initialized notification."""
        if self._initialized:
            return True
        
        # Send initialize request
        init_result = await self.send_request("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {
                "name": "agentscli-cli",
                "version": "0.0.12"
            }
        })
        
        if "error" in init_result:
            return False
        
        # Send initialized notification
        await self.send_notification("notifications/initialized")
        
        self._initialized = True
        return True


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


async def get_mcp_tools_list(server_name: str, server_config: MCPServerConfig) -> list[dict]:
    """Get list of tools from MCP server using persistent connection."""
    try:
        async with MCPServerConnection(server_config) as conn:
            # Perform handshake
            if not await conn.initialize():
                print(f"  [X] {server_name}: Failed to initialize")
                return []
            
            # List tools
            tools_result = await conn.send_request("tools/list")
            
            if "error" in tools_result:
                print(f"  [X] {server_name}: {tools_result['error']}")
                return []
            
            tools = tools_result.get("tools", [])
            print(f"  [OK] {server_name}: {len(tools)} tools")
            return tools
            
    except Exception as e:
        print(f"  [X] {server_name}: {e}")
        return []


def create_mcp_tool(server_name: str, server_config: MCPServerConfig, tool_info: dict) -> BaseTool:
    """Create a LangChain tool from MCP tool info."""
    
    tool_name = tool_info["name"]
    tool_description = tool_info.get("description", "")
    tool_schema = tool_info.get("inputSchema", {})
    
    async def run_tool(**kwargs) -> str:
        """Execute the MCP tool using persistent connection."""
        try:
            async with MCPServerConnection(server_config) as conn:
                # Initialize connection
                if not await conn.initialize():
                    return "Error: Failed to initialize MCP connection"
                
                # Call tool
                result = await conn.send_request("tools/call", {
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
                
        except Exception as e:
            return f"Error: {e}"
    
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
