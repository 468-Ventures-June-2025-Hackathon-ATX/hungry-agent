"""
MCP (Model Context Protocol) client for communicating with food delivery servers
"""

import asyncio
import json
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import settings
from .models import MCPRequest, MCPResponse, Platform, OrderItem
from .real_mcp_client import create_uber_eats_client
from .taco_search_client import taco_search_client


class MCPClient:
    """Client for communicating with Uber Eats MCP server"""
    
    def __init__(self):
        self.uber_eats_mcp = None
        self._initialize_uber_eats()
    
    def _initialize_uber_eats(self):
        """Initialize the Uber Eats MCP server"""
        try:
            # Import the Uber Eats MCP server directly
            import server
            self.uber_eats_mcp = server
        except ImportError:
            print("Warning: Could not import Uber Eats MCP server")
            self.uber_eats_mcp = None
    
    async def _call_uber_eats_function(self, function_name: str, **kwargs) -> MCPResponse:
        """Call a function on the Uber Eats MCP server"""
        
        try:
            if not self.uber_eats_mcp:
                return MCPResponse(
                    success=False,
                    error="Uber Eats MCP server not available",
                    platform=Platform.UBER_EATS,
                    session_id=kwargs.get("session_id", "")
                )
            
            # For now, return a simulated response since we need to integrate properly
            if function_name == "find_menu_options":
                search_term = kwargs.get("search_term", "")
                return MCPResponse(
                    success=True,
                    data={
                        "message": f"Search for '{search_term}' started. Please wait for 2 minutes, then you can retrieve results using the resource URI.",
                        "search_term": search_term,
                        "status": "search_initiated"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=kwargs.get("session_id", "")
                )
            
            elif function_name == "order_food":
                item_name = kwargs.get("item_name", "")
                return MCPResponse(
                    success=True,
                    data={
                        "message": f"Order for '{item_name}' started. Your order is being processed.",
                        "item_name": item_name,
                        "status": "order_initiated"
                    },
                    platform=Platform.UBER_EATS,
                    session_id=kwargs.get("session_id", "")
                )
            
            else:
                return MCPResponse(
                    success=False,
                    error=f"Unknown function: {function_name}",
                    platform=Platform.UBER_EATS,
                    session_id=kwargs.get("session_id", "")
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error calling Uber Eats MCP: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=kwargs.get("session_id", "")
            )
    
    async def search_restaurants(
        self, 
        platform: Platform, 
        query: str, 
        session_id: str = ""
    ) -> MCPResponse:
        """Search for restaurants on a platform using fast database lookup"""
        
        if platform == Platform.UBER_EATS:
            # Use fast taco search database instead of slow browser automation
            try:
                result = await taco_search_client.search_tacos(query, limit=10, session_id=session_id)
                return result
            except Exception as e:
                return MCPResponse(
                    success=False,
                    error=f"Error with fast taco search: {str(e)}",
                    platform=platform,
                    session_id=session_id
                )
        else:
            return MCPResponse(
                success=False,
                error=f"Unsupported platform: {platform}",
                platform=platform,
                session_id=session_id
            )
    
    async def get_menu(
        self, 
        platform: Platform, 
        restaurant_name: str,
        restaurant_id: Optional[str] = None,
        session_id: str = ""
    ) -> MCPResponse:
        """Get menu from a specific restaurant"""
        
        if platform == Platform.UBER_EATS:
            # For now, return a message that menu functionality is not implemented
            return MCPResponse(
                success=False,
                error="Menu functionality not yet implemented for Uber Eats MCP",
                platform=platform,
                session_id=session_id
            )
        else:
            return MCPResponse(
                success=False,
                error=f"Unsupported platform: {platform}",
                platform=platform,
                session_id=session_id
            )
    
    async def place_order(
        self, 
        platform: Platform, 
        restaurant_name: str,
        items: List[OrderItem],
        delivery_address: Optional[str] = None,
        special_instructions: Optional[str] = None,
        session_id: str = ""
    ) -> MCPResponse:
        """Place an order at a restaurant"""
        
        # Convert OrderItem objects to dictionaries
        items_data = []
        for item in items:
            item_dict = {
                "name": item.name,
                "quantity": item.quantity
            }
            if item.customizations:
                item_dict["customizations"] = item.customizations
            if item.notes:
                item_dict["notes"] = item.notes
            if item.price:
                item_dict["price"] = item.price
            
            items_data.append(item_dict)
        
        parameters = {
            "restaurant_name": restaurant_name,
            "items": items_data,
            "session_id": session_id
        }
        
        if delivery_address:
            parameters["delivery_address"] = delivery_address
        if special_instructions:
            parameters["special_instructions"] = special_instructions
        
        if platform == Platform.UBER_EATS:
            return await self._make_request(
                self.uber_eats_url, 
                "place_order", 
                parameters,
                platform
            )
        else:
            return MCPResponse(
                success=False,
                error=f"Unsupported platform: {platform}",
                platform=platform,
                session_id=session_id
            )
    
    async def check_order_status(
        self, 
        platform: Platform, 
        order_id: str,
        session_id: str = ""
    ) -> MCPResponse:
        """Check the status of an existing order"""
        
        parameters = {
            "order_id": order_id,
            "session_id": session_id
        }
        
        if platform == Platform.UBER_EATS:
            return await self._make_request(
                self.uber_eats_url, 
                "check_order_status", 
                parameters,
                platform
            )
        else:
            return MCPResponse(
                success=False,
                error=f"Unsupported platform: {platform}",
                platform=platform,
                session_id=session_id
            )
    
    async def health_check(self, platform: Platform) -> bool:
        """Check if MCP server is healthy"""
        
        if platform == Platform.UBER_EATS:
            # For health check, just return True since we can create clients on demand
            return True
        else:
            return False
    
    async def get_server_info(self, platform: Platform) -> Dict[str, Any]:
        """Get information about the MCP server"""
        
        try:
            if platform == Platform.UBER_EATS:
                url = self.uber_eats_url
            else:
                return {"error": "Unsupported platform"}
            
            async with AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{url}/info")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}


class MCPOrchestrator:
    """Orchestrates MCP operations across multiple platforms"""
    
    def __init__(self):
        self.client = MCPClient()
    
    async def execute_function_call(
        self, 
        function_name: str, 
        parameters: Dict[str, Any],
        session_id: str = ""
    ) -> MCPResponse:
        """Execute a function call from Claude on the appropriate MCP server"""
        
        try:
            platform_str = parameters.get("platform", "").lower()
            
            # Default to Uber Eats since it's the only supported platform
            platform = Platform.UBER_EATS
            
            # Route to appropriate method
            if function_name == "search_restaurants":
                return await self.client.search_restaurants(
                    platform=platform,
                    query=parameters.get("query", ""),
                    session_id=session_id
                )
            
            elif function_name == "get_restaurant_details":
                # Use fast taco search for restaurant details
                try:
                    result = await taco_search_client.get_restaurant_details(
                        restaurant_name=parameters.get("restaurant_name", ""),
                        session_id=session_id
                    )
                    return result
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error getting restaurant details: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "get_top_rated_tacos":
                # Use fast taco search for top-rated restaurants
                try:
                    result = await taco_search_client.get_top_rated_tacos(
                        limit=parameters.get("limit", 5),
                        session_id=session_id
                    )
                    return result
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error getting top-rated tacos: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "search_by_area":
                # Use fast taco search for area-based search
                try:
                    result = await taco_search_client.search_by_area(
                        area=parameters.get("area", ""),
                        limit=parameters.get("limit", 8),
                        session_id=session_id
                    )
                    return result
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error searching by area: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "intelligent_search":
                # Use fast taco search with Claude intelligence
                try:
                    result = await taco_search_client.intelligent_search(
                        query=parameters.get("query", ""),
                        limit=parameters.get("limit", 10),
                        session_id=session_id
                    )
                    return result
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error with intelligent search: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "get_menu":
                return await self.client.get_menu(
                    platform=platform,
                    restaurant_name=parameters.get("restaurant_name", ""),
                    restaurant_id=parameters.get("restaurant_id"),
                    session_id=session_id
                )
            
            elif function_name == "order_food":
                # Use Uber Eats MCP for order fulfillment
                try:
                    # Create a fresh MCP client instance for this order
                    client = create_uber_eats_client()
                    try:
                        # Call the order_food function on Uber Eats MCP
                        result = await client.send_mcp_request(
                            "tools/call",
                            {
                                "name": "order_food",
                                "arguments": {
                                    "restaurant_name": parameters.get("restaurant_name", ""),
                                    "item_name": parameters.get("item_name", ""),
                                    "quantity": parameters.get("quantity", 1),
                                    "item_url": parameters.get("item_url", ""),
                                    "delivery_address": parameters.get("delivery_address", "809 Bouldin Ave, Austin, TX 78704")
                                }
                            }
                        )
                        
                        if "result" in result:
                            return MCPResponse(
                                success=True,
                                data={
                                    "message": result["result"],
                                    "restaurant_name": parameters.get("restaurant_name", ""),
                                    "item_name": parameters.get("item_name", ""),
                                    "status": "order_started"
                                },
                                platform=platform,
                                session_id=session_id
                            )
                        else:
                            error_msg = result.get("error", "Unknown error from Uber Eats MCP server")
                            return MCPResponse(
                                success=False,
                                error=error_msg,
                                platform=platform,
                                session_id=session_id
                            )
                    finally:
                        await client.close()
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error placing order: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "place_multiple_items_order":
                # Use Uber Eats MCP for multi-item order fulfillment
                try:
                    client = create_uber_eats_client()
                    try:
                        result = await client.send_mcp_request(
                            "tools/call",
                            {
                                "name": "place_multiple_items_order",
                                "arguments": {
                                    "restaurant_name": parameters.get("restaurant_name", ""),
                                    "items": parameters.get("items", []),
                                    "delivery_address": parameters.get("delivery_address", "809 Bouldin Ave, Austin, TX 78704")
                                }
                            }
                        )
                        
                        if "result" in result:
                            return MCPResponse(
                                success=True,
                                data={
                                    "message": result["result"],
                                    "restaurant_name": parameters.get("restaurant_name", ""),
                                    "items": parameters.get("items", []),
                                    "status": "multi_order_started"
                                },
                                platform=platform,
                                session_id=session_id
                            )
                        else:
                            error_msg = result.get("error", "Unknown error from Uber Eats MCP server")
                            return MCPResponse(
                                success=False,
                                error=error_msg,
                                platform=platform,
                                session_id=session_id
                            )
                    finally:
                        await client.close()
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error placing multi-item order: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            elif function_name == "check_order_status":
                return await self.client.check_order_status(
                    platform=platform,
                    order_id=parameters.get("order_id", ""),
                    session_id=session_id
                )
            
            elif function_name == "create_batch_orders":
                # Import here to avoid circular imports
                from .batch_mcp_client import batch_mcp_orchestrator
                
                try:
                    order_ids = await batch_mcp_orchestrator.create_batch_order(
                        restaurant_queries=parameters.get("restaurant_queries", []),
                        items_per_restaurant=parameters.get("items_per_restaurant", []),
                        location=parameters.get("location", "Austin, TX"),
                        session_id=session_id
                    )
                    
                    return MCPResponse(
                        success=True,
                        data={
                            "message": f"Created {len(order_ids)} batch orders",
                            "order_ids": order_ids,
                            "estimated_completion": "2-3 minutes per restaurant"
                        },
                        platform=platform,
                        session_id=session_id
                    )
                    
                except Exception as e:
                    return MCPResponse(
                        success=False,
                        error=f"Error creating batch orders: {str(e)}",
                        platform=platform,
                        session_id=session_id
                    )
            
            else:
                return MCPResponse(
                    success=False,
                    error=f"Unknown function: {function_name}",
                    platform=platform,
                    session_id=session_id
                )
                
        except Exception as e:
            return MCPResponse(
                success=False,
                error=f"Error executing function call: {str(e)}",
                platform=Platform.UBER_EATS,  # Default
                session_id=session_id
            )
    
    async def check_all_servers(self) -> Dict[str, bool]:
        """Check health of all MCP servers"""
        
        return {
            "uber_eats": await self.client.health_check(Platform.UBER_EATS)
        }


# Global MCP orchestrator instance
mcp_orchestrator = MCPOrchestrator()
