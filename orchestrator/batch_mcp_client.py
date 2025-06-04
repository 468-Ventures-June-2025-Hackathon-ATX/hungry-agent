"""
Batch MCP client for handling multiple concurrent Uber Eats orders
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .real_mcp_client import create_uber_eats_client
from .models import MCPResponse, Platform


class BatchOrder:
    def __init__(self, order_id: str, restaurant_query: str, items: List[str], location: str, session_id: str):
        self.order_id = order_id
        self.restaurant_query = restaurant_query
        self.items = items
        self.location = location
        self.session_id = session_id
        self.status = "pending"
        self.mcp_client = None
        self.search_results = None
        self.created_at = datetime.utcnow()


class BatchMCPOrchestrator:
    """Orchestrates multiple concurrent Uber Eats orders"""
    
    def __init__(self):
        self.active_orders: Dict[str, BatchOrder] = {}
        self.max_concurrent_orders = 5  # Limit concurrent browser sessions
    
    async def create_batch_order(
        self, 
        restaurant_queries: List[str], 
        items_per_restaurant: List[List[str]], 
        location: str,
        session_id: str
    ) -> List[str]:
        """Create multiple orders simultaneously"""
        
        if len(restaurant_queries) > self.max_concurrent_orders:
            raise ValueError(f"Maximum {self.max_concurrent_orders} concurrent orders allowed")
        
        order_ids = []
        
        for i, (restaurant_query, items) in enumerate(zip(restaurant_queries, items_per_restaurant)):
            order_id = f"batch_{session_id}_{uuid.uuid4().hex[:8]}"
            
            batch_order = BatchOrder(
                order_id=order_id,
                restaurant_query=restaurant_query,
                items=items,
                location=location,
                session_id=session_id
            )
            
            self.active_orders[order_id] = batch_order
            order_ids.append(order_id)
            
            # Start the order process asynchronously
            asyncio.create_task(self._process_batch_order(order_id))
        
        return order_ids
    
    async def _process_batch_order(self, order_id: str):
        """Process a single order in the batch"""
        
        batch_order = self.active_orders.get(order_id)
        if not batch_order:
            return
        
        try:
            # Create a dedicated MCP client for this order
            batch_order.mcp_client = create_uber_eats_client()
            batch_order.status = "searching"
            
            # Search for restaurants
            search_response = await batch_order.mcp_client.search_restaurants(
                search_term=batch_order.restaurant_query,
                session_id=batch_order.session_id,
                location=batch_order.location
            )
            
            if search_response.success:
                batch_order.status = "search_started"
                batch_order.search_results = search_response.data
                
                # Wait for search to complete (2 minutes as per MCP server)
                await asyncio.sleep(120)
                
                # Try to get search results
                if batch_order.search_results and "search_id" in batch_order.search_results:
                    results_response = await batch_order.mcp_client.get_search_results(
                        batch_order.search_results["search_id"]
                    )
                    
                    if results_response.success:
                        batch_order.status = "results_ready"
                        batch_order.search_results = results_response.data
                        
                        # TODO: Implement automatic ordering based on search results
                        # For now, just mark as ready for manual ordering
                        batch_order.status = "ready_to_order"
                    else:
                        batch_order.status = "search_failed"
                else:
                    batch_order.status = "search_failed"
            else:
                batch_order.status = "search_failed"
                
        except Exception as e:
            batch_order.status = "error"
            print(f"Error processing batch order {order_id}: {e}")
        
        finally:
            # Clean up the MCP client
            if batch_order.mcp_client:
                await batch_order.mcp_client.close()
    
    async def get_batch_status(self, session_id: str) -> List[Dict[str, Any]]:
        """Get status of all batch orders for a session"""
        
        session_orders = [
            order for order in self.active_orders.values() 
            if order.session_id == session_id
        ]
        
        return [
            {
                "order_id": order.order_id,
                "restaurant_query": order.restaurant_query,
                "items": order.items,
                "location": order.location,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "search_results": order.search_results
            }
            for order in session_orders
        ]
    
    async def place_batch_order(self, order_id: str, item_url: str, item_name: str) -> MCPResponse:
        """Place an order for a specific item from batch results"""
        
        batch_order = self.active_orders.get(order_id)
        if not batch_order:
            return MCPResponse(
                success=False,
                error="Order ID not found",
                platform=Platform.UBER_EATS,
                session_id=""
            )
        
        if batch_order.status != "ready_to_order":
            return MCPResponse(
                success=False,
                error=f"Order not ready. Current status: {batch_order.status}",
                platform=Platform.UBER_EATS,
                session_id=batch_order.session_id
            )
        
        try:
            # Create a new MCP client for ordering
            order_client = create_uber_eats_client()
            
            # Place the order
            order_response = await order_client.place_order(
                item_url=item_url,
                item_name=item_name,
                session_id=batch_order.session_id
            )
            
            if order_response.success:
                batch_order.status = "order_placed"
            else:
                batch_order.status = "order_failed"
            
            await order_client.close()
            return order_response
            
        except Exception as e:
            batch_order.status = "order_failed"
            return MCPResponse(
                success=False,
                error=f"Error placing order: {str(e)}",
                platform=Platform.UBER_EATS,
                session_id=batch_order.session_id
            )
    
    async def cancel_batch_order(self, order_id: str) -> bool:
        """Cancel a batch order"""
        
        batch_order = self.active_orders.get(order_id)
        if not batch_order:
            return False
        
        batch_order.status = "cancelled"
        
        if batch_order.mcp_client:
            await batch_order.mcp_client.close()
        
        return True
    
    async def cleanup_completed_orders(self, max_age_hours: int = 24):
        """Clean up old completed orders"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        orders_to_remove = [
            order_id for order_id, order in self.active_orders.items()
            if order.created_at < cutoff_time and order.status in ["completed", "cancelled", "error"]
        ]
        
        for order_id in orders_to_remove:
            del self.active_orders[order_id]
        
        return len(orders_to_remove)


# Global batch orchestrator instance
batch_mcp_orchestrator = BatchMCPOrchestrator()
