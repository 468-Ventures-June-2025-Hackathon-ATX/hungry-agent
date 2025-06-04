"""
Real MCP client that communicates with the Uber Eats MCP server via stdio JSON-RPC
"""

import asyncio
import json
import subprocess
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

from .models import MCPResponse, Platform


class RealUberEatsMCPClient:
    def __init__(self):
        self.process = None
        self.request_id = 1
        self.active_searches = {}  # Track ongoing searches
        
    async def start_mcp_server(self):
        """Start the real Uber Eats MCP server"""
        if self.process is None or self.process.returncode is not None:
            # Close any existing process first
            if self.process is not None:
                await self.close()
            
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(os.getcwd(), 'venv/lib/python3.13/site-packages')
            
            # Add browser automation environment variables
            env['BROWSERUSE_CONFIG_DIR'] = '/tmp/browseruse'
            
            # Ensure the config directory exists
            os.makedirs('/tmp/browseruse', exist_ok=True)
            
            # Start the MCP server as a subprocess
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, "server.py",
                cwd="submodules/uber-eats-mcp-server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Wait a moment for the server to initialize
            await asyncio.sleep(3)
            print("🚀 Uber Eats MCP server started")
            
            # Initialize the MCP connection
            await self._initialize_mcp_connection()
    
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
                        "name": "hungry-agent",
                        "version": "1.0.0"
                    }
                }
            )
            
            print(f"Initialize response: {init_response}")
            
            # Send initialized notification
            await self.send_mcp_notification("notifications/initialized", {})
            
        except Exception as e:
            print(f"Error initializing MCP connection: {e}")
    
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
        
        # Additional check for transport state
        try:
            if self.process.stdin.is_closing():
                print("Transport is closing, restarting MCP server...")
                await self.start_mcp_server()
        except:
            print("Transport check failed, restarting MCP server...")
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
            
            # Read response with timeout, filtering out non-JSON lines
            max_attempts = 10
            for attempt in range(max_attempts):
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), 
                    timeout=30.0  # Increased timeout for browser operations
                )
                
                if response_line:
                    response_text = response_line.decode().strip()
                    print(f"MCP Server Output: {response_text}")  # Debug output
                    
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
                    return {"error": "No response from MCP server"}
            
            return {"error": "No valid JSON response after multiple attempts"}
                
        except asyncio.TimeoutError:
            return {"error": "MCP server timeout"}
        except Exception as e:
            return {"error": f"MCP communication error: {str(e)}"}
    
    async def search_restaurants(self, search_term: str, session_id: str = "") -> MCPResponse:
        """Start a restaurant search using the real MCP server"""
        
        try:
            # Call the find_menu_options tool
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "find_menu_options",
                    "arguments": {
                        "search_term": search_term
                    }
                }
            )
            
            if "result" in response:
                # The MCP server returns a message about the search being started
                result_text = response["result"]
                
                # Extract request ID from the result if available
                if "resource://search_results/" in result_text:
                    # Store this search for later retrieval
                    search_id = f"search_{self.request_id}_{session_id}"
                    self.active_searches[search_id] = {
                        "search_term": search_term,
                        "started_at": datetime.utcnow(),
                        "session_id": session_id
                    }
                
                return MCPResponse(
                    success=True,
                    data={
                        "message": result_text,
                        "search_term": search_term,
                        "status": "search_started",
                        "search_id": search_id if "resource://search_results/" in result_text else None
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error calling Uber Eats MCP: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def get_search_results(self, search_id: str) -> MCPResponse:
        """Get search results using the resource endpoint"""
        
        try:
            if search_id not in self.active_searches:
                return MCPResponse(
                    success=False,
                    error="Search ID not found",
                    platform=Platform.UBER_EATS,
                    session_id=""
                )
            
            search_info = self.active_searches[search_id]
            
            # Try to get results using the resource endpoint
            response = await self.send_mcp_request(
                "resources/read",
                {
                    "uri": f"resource://search_results/{search_id}"
                }
            )
            
            if "result" in response:
                return MCPResponse(
                    success=True,
                    data={
                        "results": response["result"],
                        "search_term": search_info["search_term"],
                        "status": "results_ready"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=search_info["session_id"]
                )
            else:
                return MCPResponse(
                    success=False,
                    error="Results not ready yet",
                    platform=Platform.UBER_EATS,
                    session_id=search_info["session_id"]
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error getting search results: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=""
            )
    
    async def place_order(self, item_url: str, item_name: str, session_id: str = "") -> MCPResponse:
        """Place an order using the real MCP server"""
        
        try:
            # Call the order_food tool
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "order_food",
                    "arguments": {
                        "item_url": item_url,
                        "item_name": item_name
                    }
                }
            )
            
            if "result" in response:
                return MCPResponse(
                    success=True,
                    data={
                        "message": response["result"],
                        "item_name": item_name,
                        "item_url": item_url,
                        "status": "order_started"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
            else:
                error_msg = response.get("error", "Unknown error from MCP server")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    platform=Platform.UBER_EATS,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error placing order: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            if self.process is None:
                return False
            
            # Check if process is still running
            if self.process.returncode is not None:
                return False
            
            return True
        except:
            return False
    
    async def close(self):
        """Close the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
                print("🛑 Uber Eats MCP server stopped")


# Factory function to create new instances
def create_uber_eats_client():
    return RealUberEatsMCPClient()

# Global instance
real_uber_eats_client = RealUberEatsMCPClient()
