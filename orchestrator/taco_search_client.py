"""
Fast Taco Search MCP Client
Provides lightning-fast taco restaurant searches using SQLite database
"""

import asyncio
import json
import subprocess
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

from .models import MCPResponse, Platform


class TacoSearchMCPClient:
    def __init__(self):
        self.process = None
        self.request_id = 1
        
    async def start_mcp_server(self):
        """Start the fast taco search MCP server"""
        if self.process is None or self.process.returncode is not None:
            # Close any existing process first
            if self.process is not None:
                await self.close()
            
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(os.getcwd(), 'venv/lib/python3.13/site-packages')
            
            # Start the taco search MCP server as a subprocess
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, "server.py",
                cwd="submodules/taco-search-mcp-server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Start a task to monitor stderr for debugging
            asyncio.create_task(self._monitor_stderr())
            
            # Wait a moment for the server to initialize
            await asyncio.sleep(1)
            print("🚀 Fast Taco Search MCP server started")
            
            # Initialize the MCP connection
            await self._initialize_mcp_connection()
    
    async def _monitor_stderr(self):
        """Monitor stderr output from the MCP server for debugging"""
        try:
            while self.process and self.process.returncode is None:
                stderr_line = await self.process.stderr.readline()
                if stderr_line:
                    stderr_text = stderr_line.decode().strip()
                    if stderr_text:
                        print(f"🔴 Taco Search MCP STDERR: {stderr_text}")
                else:
                    break
        except Exception as e:
            print(f"Error monitoring taco search stderr: {e}")
    
    async def _initialize_mcp_connection(self):
        """Initialize the MCP connection with proper handshake"""
        try:
            # Send initialize request
            init_response = await self.send_mcp_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "hungry-agent-taco-search",
                        "version": "1.0.0"
                    }
                }
            )
            
            print(f"Taco Search Initialize response: {init_response}")
            
            # Send initialized notification
            await self.send_mcp_notification("notifications/initialized", {})
            
        except Exception as e:
            print(f"Error initializing taco search MCP connection: {e}")
    
    async def send_mcp_notification(self, method: str, params: Dict[str, Any]):
        """Send a notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()
    
    async def send_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server"""
        # Always ensure we have a fresh, working process
        if self.process is None or self.process.returncode is not None:
            await self.start_mcp_server()
        
        # Create JSON-RPC request for FastMCP
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        self.request_id += 1
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response with short timeout (database queries are fast)
            max_attempts = 10
            for attempt in range(max_attempts):
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), 
                    timeout=5.0  # Short timeout for fast database operations
                )
                
                if response_line:
                    response_text = response_line.decode().strip()
                    print(f"Taco Search MCP Output: {response_text}")  # Debug output
                    
                    # Skip telemetry and other non-JSON lines
                    if response_text.startswith("INFO") or response_text.startswith("WARNING") or response_text.startswith("ERROR"):
                        continue
                    
                    if response_text:
                        try:
                            response = json.loads(response_text)
                            return response
                        except json.JSONDecodeError as e:
                            # If it's not JSON, continue reading
                            print(f"Non-JSON line: {response_text}")
                            continue
                    else:
                        continue
                else:
                    return {"error": "No response from taco search MCP server"}
            
            return {"error": "No valid JSON response after multiple attempts"}
                
        except asyncio.TimeoutError:
            return {"error": "Taco search MCP server timeout"}
        except Exception as e:
            return {"error": f"Taco search MCP communication error: {str(e)}"}
    
    async def search_tacos(self, query: str, limit: int = 10, session_id: str = "") -> MCPResponse:
        """Search for taco restaurants using fast database lookup"""
        
        try:
            # Call the search_tacos tool
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "search_tacos",
                    "arguments": {
                        "query": query,
                        "limit": limit
                    }
                }
            )
            
            if "result" in response:
                result_text = response["result"]
                
                return MCPResponse(
                    success=True,
                    data={
                        "message": result_text,
                        "search_term": query,
                        "status": "search_completed",
                        "source": "fast_database"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from taco search MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error calling taco search MCP: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def get_restaurant_details(self, restaurant_name: str, session_id: str = "") -> MCPResponse:
        """Get detailed information about a specific restaurant"""
        
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "get_restaurant_details",
                    "arguments": {
                        "restaurant_name": restaurant_name
                    }
                }
            )
            
            if "result" in response:
                result_text = response["result"]
                
                return MCPResponse(
                    success=True,
                    data={
                        "message": result_text,
                        "restaurant_name": restaurant_name,
                        "status": "details_retrieved"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from taco search MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error getting restaurant details: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def get_top_rated_tacos(self, limit: int = 5, session_id: str = "") -> MCPResponse:
        """Get top-rated taco restaurants"""
        
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "get_top_rated_tacos",
                    "arguments": {
                        "limit": limit
                    }
                }
            )
            
            if "result" in response:
                result_text = response["result"]
                
                return MCPResponse(
                    success=True,
                    data={
                        "message": result_text,
                        "status": "top_rated_retrieved"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from taco search MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error getting top-rated tacos: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def search_by_area(self, area: str, limit: int = 8, session_id: str = "") -> MCPResponse:
        """Search for taco restaurants by area"""
        
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "search_by_area",
                    "arguments": {
                        "area": area,
                        "limit": limit
                    }
                }
            )
            
            if "result" in response:
                result_text = response["result"]
                
                return MCPResponse(
                    success=True,
                    data={
                        "message": result_text,
                        "area": area,
                        "status": "area_search_completed"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from taco search MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error searching by area: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def health_check(self) -> bool:
        """Check if taco search MCP server is healthy"""
        try:
            # Test if we can perform a simple search to verify the service works
            response = await self.search_tacos("test", limit=1, session_id="health_check")
            
            # If we get a successful response, the service is healthy
            return response.success
            
        except Exception as e:
            print(f"Taco search health check failed: {e}")
            return False
    
    async def close(self):
        """Close the taco search MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
                print("🛑 Fast Taco Search MCP server stopped")


# Global instance
taco_search_client = TacoSearchMCPClient()
