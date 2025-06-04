#!/usr/bin/env python3
import asyncio
import sys
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from browser import run_browser_agent

# Load environment variables from .env file
load_dotenv()

# Configure logging to go to stderr to avoid interfering with JSON-RPC on stdout
logging.basicConfig(
    level=logging.CRITICAL,  # Only show critical errors
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Redirect any remaining stdout prints from dependencies to stderr
class StderrRedirect:
    def write(self, text):
        if text.strip():  # Only redirect non-empty text
            sys.stderr.write(text)
    def flush(self):
        sys.stderr.flush()

# Store original stdout for JSON-RPC
original_stdout = sys.stdout

# Initialize FastMCP server
mcp = FastMCP("uber_eats")

# In-memory storage for search results
search_results = {}

# REMOVED: find_menu_options tool - search functionality now handled by fast taco search MCP
# This server now focuses purely on order fulfillment

async def perform_search(request_id: str, search_term: str, delivery_address: str, task: str, context: Context):
    """Perform the actual search in the background."""
    try:
        step_count = 0
        
        async def step_handler(*args, **kwargs):
            nonlocal step_count
            step_count += 1
            await context.info(f"Step {step_count} completed")
            await context.report_progress(step_count)
        
        result = await run_browser_agent(task=task, on_step=step_handler)
        
        search_results[request_id] = result
    
    except Exception as e:
        # Store the error with the request ID
        search_results[request_id] = f"Error: {str(e)}"
        await context.error(f"Error searching for '{search_term}': {str(e)}")

@mcp.resource(uri="resource://search_results/{request_id}")
async def get_search_results(request_id: str) -> str:
    """Get the search results for a given request ID.
    
    Args:
        request_id: The ID of the request to get the search results for
    """
    # Check if the results exist
    if request_id not in search_results:
        return f"No search results found for request ID: {request_id}"
    
    # Return the successful search results
    return search_results[request_id]

@mcp.tool()
async def order_food(restaurant_name: str, item_name: str, context: Context, item_url: str = "", quantity: int = 1, delivery_address: str = "809 Bouldin Ave, Austin, TX 78704") -> str:
    """Place an order for specific food items from a restaurant on Uber Eats.
    
    Args:
        restaurant_name: Name of the restaurant (from fast search results)
        item_name: Name of the item to order (from fast search results)
        item_url: Direct URL to the item (if available from search)
        quantity: Number of items to order (default: 1)
        delivery_address: Delivery address for the order
    """
    
    # If we have a direct item URL, use it; otherwise construct search-based task
    if item_url and item_url.startswith("http"):
        task = f"""
1. Go directly to the item URL: {item_url}
2. If quantity selector is available, set quantity to {quantity}
3. Click "Add to cart" or "Add to order"
4. Wait for item to be added to cart
5. Navigate to cart/checkout
6. Review order details for {restaurant_name}
7. Confirm delivery address: {delivery_address}
8. Complete the order placement process
9. Capture order confirmation details
"""
    else:
        # Fallback: search-based ordering
        task = f"""
1. Go to https://www.ubereats.com
2. Search for "{restaurant_name}" restaurant
3. Click on {restaurant_name} from search results
4. Look for "{item_name}" on the menu
5. If quantity selector is available, set quantity to {quantity}
6. Click "Add to cart" for {item_name}
7. Navigate to cart/checkout
8. Review order details
9. Confirm delivery address: {delivery_address}
10. Complete the order placement process
11. Capture order confirmation details
"""
    
    # Start the background task for ordering
    asyncio.create_task(
        perform_order(restaurant_name, item_name, task, context)
    )
    
    # Return immediate confirmation
    return f"Order started: {quantity}x {item_name} from {restaurant_name}. Processing your order now!"

@mcp.tool()
async def place_multiple_items_order(restaurant_name: str, items: list, context: Context, delivery_address: str = "809 Bouldin Ave, Austin, TX 78704") -> str:
    """Place an order for multiple items from the same restaurant.
    
    Args:
        restaurant_name: Name of the restaurant
        items: List of items with name, quantity, and optional item_url
        delivery_address: Delivery address for the order
    """
    
    items_text = []
    for item in items:
        item_name = item.get('name', '')
        quantity = item.get('quantity', 1)
        items_text.append(f"{quantity}x {item_name}")
    
    items_summary = ", ".join(items_text)
    
    task = f"""
1. Go to https://www.ubereats.com
2. Search for "{restaurant_name}" restaurant
3. Click on {restaurant_name} from search results
4. Add the following items to cart:
"""
    
    for item in items:
        item_name = item.get('name', '')
        quantity = item.get('quantity', 1)
        item_url = item.get('item_url', '')
        
        if item_url:
            task += f"""
   - Go to {item_url} and add {quantity}x {item_name}"""
        else:
            task += f"""
   - Find "{item_name}" on menu and add {quantity} to cart"""
    
    task += f"""
5. Navigate to cart/checkout
6. Review all items in order
7. Confirm delivery address: {delivery_address}
8. Complete the order placement process
9. Capture order confirmation details
"""
    
    # Start the background task for ordering
    asyncio.create_task(
        perform_order(restaurant_name, f"Multiple items: {items_summary}", task, context)
    )
    
    return f"Multi-item order started from {restaurant_name}: {items_summary}. Processing your order now!"

async def perform_order(restaurant_url: str, item_name: str, task: str, context: Context):
    """Perform the actual food ordering in the background."""
    try:
        step_count = 0
        
        async def step_handler(*args, **kwargs):
            nonlocal step_count
            step_count += 1
            await context.info(f"Order step {step_count} completed")
            await context.report_progress(step_count)
        
        result = await run_browser_agent(task=task, on_step=step_handler)
        
        # Report completion
        await context.info(f"Order for '{item_name}' has been placed successfully!")
        return result
    
    except Exception as e:
        error_msg = f"Error ordering '{item_name}': {str(e)}"
        await context.error(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run(transport='stdio')
