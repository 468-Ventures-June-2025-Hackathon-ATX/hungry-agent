"""
Fast Taco Search MCP Client
Provides lightning-fast taco restaurant searches using SQLite database
"""

import asyncio
import json
import subprocess
import sys
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from .models import MCPResponse, Platform


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, use fallback
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker to prevent cascade failures"""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if we can execute the operation"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if we should try again
            if (self.last_failure_time and 
                datetime.utcnow().timestamp() - self.last_failure_time > self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN


class TacoSearchMCPClient:
    def __init__(self):
        self.process = None
        self.request_id = 1
        self.pending_requests = {}  # Maps request_id to Future
        self.response_processor_task = None
        self._process_lock = asyncio.Lock()
        self._is_initializing = False
        self._initialization_lock = asyncio.Lock()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
    async def start_mcp_server(self):
        """Start the fast taco search MCP server"""
        if self.process is None or self.process.returncode is not None:
            # Close any existing process first
            if self.process is not None:
                await self.close()
            
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(os.getcwd(), 'venv/lib/python3.13/site-packages')
            
            # Pass ANTHROPIC_API_KEY from main config
            from .config import settings
            if hasattr(settings, 'anthropic_api_key') and settings.anthropic_api_key:
                env['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
                print(f"🔑 ANTHROPIC_API_KEY passed to taco search MCP server (length: {len(settings.anthropic_api_key)})")
            else:
                # Try to get from environment directly
                api_key = os.environ.get('ANTHROPIC_API_KEY')
                if api_key:
                    env['ANTHROPIC_API_KEY'] = api_key
                    print(f"🔑 ANTHROPIC_API_KEY found in environment (length: {len(api_key)})")
                else:
                    print("⚠️  ANTHROPIC_API_KEY not found in settings or environment - intelligent search will use fallback")
            
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
    
    async def _ensure_process_running(self):
        """Ensure the MCP server process is running and initialized"""
        async with self._initialization_lock:
            if self._is_initializing:
                # Wait for ongoing initialization
                while self._is_initializing:
                    await asyncio.sleep(0.1)
                return
            
            if self.process is None or self.process.returncode is not None:
                self._is_initializing = True
                try:
                    await self.start_mcp_server()
                    # Start response processor if not already running
                    if self.response_processor_task is None or self.response_processor_task.done():
                        self.response_processor_task = asyncio.create_task(self._process_responses())
                finally:
                    self._is_initializing = False

    async def _process_responses(self):
        """Process responses from the MCP server in the background"""
        try:
            while self.process and self.process.returncode is None:
                try:
                    response_line = await asyncio.wait_for(
                        self.process.stdout.readline(), 
                        timeout=1.0  # Short timeout to check process status regularly
                    )
                    
                    if response_line:
                        response_text = response_line.decode().strip()
                        
                        # Skip telemetry and other non-JSON lines
                        if (response_text.startswith("INFO") or 
                            response_text.startswith("WARNING") or 
                            response_text.startswith("ERROR") or
                            not response_text):
                            continue
                        
                        try:
                            response = json.loads(response_text)
                            
                            # Handle response with ID (request response)
                            if "id" in response:
                                request_id = response["id"]
                                if request_id in self.pending_requests:
                                    future = self.pending_requests.pop(request_id)
                                    if not future.done():
                                        future.set_result(response)
                                else:
                                    print(f"⚠️  Received response for unknown request ID: {request_id}")
                            else:
                                # Handle notification or error without ID
                                print(f"📢 MCP Notification: {response}")
                                
                        except json.JSONDecodeError:
                            print(f"🔴 Non-JSON line from MCP server: {response_text}")
                            continue
                    
                except asyncio.TimeoutError:
                    # Timeout is expected, just continue to check process status
                    continue
                except Exception as e:
                    print(f"Error processing MCP response: {e}")
                    break
                    
        except Exception as e:
            print(f"Response processor error: {e}")
        finally:
            # Cancel any pending requests
            for request_id, future in self.pending_requests.items():
                if not future.done():
                    future.set_exception(Exception("MCP server connection lost"))
            self.pending_requests.clear()

    async def send_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server with improved concurrency handling"""
        
        # Ensure process is running
        await self._ensure_process_running()
        
        # Create unique request ID
        request_id = self.request_id
        self.request_id += 1
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        try:
            # Send request with process lock
            async with self._process_lock:
                if self.process is None or self.process.returncode is not None:
                    raise Exception("MCP server process not available")
                
                request_json = json.dumps(request) + "\n"
                print(f"🔵 Sending MCP request ID {request_id}: {method}")
                self.process.stdin.write(request_json.encode())
                await self.process.stdin.drain()
            
            # Wait for response with timeout
            timeout = 15.0 if method == "tools/call" and params.get("name") == "intelligent_search" else 8.0
            print(f"⏱️  Waiting for response ID {request_id} with timeout: {timeout}s")
            
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                print(f"✅ Received response for request ID {request_id}")
                return response
                
            except asyncio.TimeoutError:
                print(f"❌ Timeout waiting for response to request ID {request_id}")
                # Clean up pending request
                self.pending_requests.pop(request_id, None)
                return {"error": f"Timeout waiting for MCP server response (request {request_id})"}
                
        except Exception as e:
            print(f"❌ Error sending MCP request ID {request_id}: {str(e)}")
            # Clean up pending request
            self.pending_requests.pop(request_id, None)
            return {"error": f"MCP communication error: {str(e)}"}
    
    def _create_fallback_response(self, query: str, session_id: str = "") -> MCPResponse:
        """Create a fallback response when MCP server is unavailable"""
        fallback_message = f"""🔄 Taco search service is temporarily unavailable. Here are some popular Austin taco spots to try:

1. Torchy's Tacos - Multiple locations, famous for creative tacos
2. Veracruz All Natural - Known for fresh, authentic Mexican tacos
3. Suerte - Upscale Mexican with excellent tacos
4. La Barbacoa - Traditional barbacoa and breakfast tacos
5. Valentina's Tex Mex BBQ - Unique BBQ-Mexican fusion

Search query: "{query}"
Status: Using fallback recommendations (MCP server unavailable)"""

        return MCPResponse(
            success=True,
            data={
                "message": fallback_message,
                "search_term": query,
                "status": "fallback_response",
                "source": "static_fallback"
            },
            platform=Platform.UBER_EATS,
            session_id=session_id
        )

    async def _execute_with_circuit_breaker(self, operation_name: str, operation_func, fallback_func, *args, **kwargs):
        """Execute an operation with circuit breaker protection"""
        
        # Check circuit breaker state
        if not self.circuit_breaker.can_execute():
            print(f"🔴 Circuit breaker OPEN for {operation_name}, using fallback")
            return await fallback_func(*args, **kwargs)
        
        try:
            # Execute the operation
            result = await operation_func(*args, **kwargs)
            
            # Check if the operation was successful
            if hasattr(result, 'success') and result.success:
                self.circuit_breaker.record_success()
                return result
            else:
                # Operation returned an error
                self.circuit_breaker.record_failure()
                print(f"⚠️  {operation_name} failed, circuit breaker recorded failure")
                return await fallback_func(*args, **kwargs)
                
        except Exception as e:
            # Operation threw an exception
            self.circuit_breaker.record_failure()
            print(f"❌ {operation_name} exception, circuit breaker recorded failure: {e}")
            return await fallback_func(*args, **kwargs)

    async def _search_tacos_mcp(self, query: str, limit: int = 10, session_id: str = "") -> MCPResponse:
        """Internal method to call MCP search_tacos"""
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

    async def search_tacos(self, query: str, limit: int = 10, session_id: str = "") -> MCPResponse:
        """Search for taco restaurants using fast database lookup with circuit breaker protection"""
        
        async def fallback():
            return self._create_fallback_response(query, session_id)
        
        return await self._execute_with_circuit_breaker(
            "search_tacos",
            self._search_tacos_mcp,
            fallback,
            query, limit, session_id
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
    
    async def intelligent_search(self, query: str, limit: int = 10, session_id: str = "") -> MCPResponse:
        """Advanced AI-powered search using Claude to analyze the entire database"""
        
        try:
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "intelligent_search",
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
                        "query": query,
                        "status": "intelligent_search_completed",
                        "source": "claude_analysis"
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
                error=f"Error with intelligent search: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=session_id
            )
    
    async def health_check(self) -> bool:
        """Check if taco search MCP server is healthy"""
        try:
            # Use the dedicated health_check tool instead of doing a full search
            response = await self.send_mcp_request(
                "tools/call",
                {
                    "name": "health_check",
                    "arguments": {}
                }
            )
            
            if "result" in response:
                result_text = response["result"]
                # Check if the health check was successful
                return "✅" in result_text and "healthy" in result_text.lower()
            else:
                print(f"Taco search health check failed: {response.get('error', 'Unknown error')}")
                return False
            
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
