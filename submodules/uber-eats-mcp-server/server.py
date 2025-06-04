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

@mcp.tool()
async def find_menu_options(search_term: str, context: Context, delivery_address: str = "809 Bouldin Ave, Austin, TX 78704") -> str:
    """Search Uber Eats for restaurants or food items at a specific delivery address.
    
    Args:
        search_term: Food or restaurant to search for
        delivery_address: Delivery address (defaults to Austin, TX location)
    """
    
    import urllib.parse
    import json
    
    # Default Austin coordinates for the default address
    default_location = {
        "address": "809 Bouldin Ave, Austin, TX 78704",
        "reference": "local",
        "latitude": 30.2515255,
        "longitude": -97.7343454
    }
    
    # Use default location for now (can be enhanced later to geocode custom addresses)
    location_data = default_location
    if delivery_address != default_location["address"]:
        # For now, use default Austin location but update address
        location_data["address"] = delivery_address
    
    # Create the location parameter as JSON then URL encode it
    location_json = json.dumps(location_data)
    encoded_location = urllib.parse.quote(location_json)
    
    # URL encode the search term
    encoded_search = urllib.parse.quote(search_term)
    
    # Construct the proper Uber Eats search URL using the correct structure
    direct_url = f"https://www.ubereats.com/search?diningMode=DELIVERY&pl={encoded_location}&query={encoded_search}"
    
    # Create comprehensive multi-restaurant search task
    task = f"""
1. Go directly to the search results URL: {direct_url}
2. Wait for the search results page to load completely (look for restaurant cards)
3. Scan the entire search results page and identify ALL restaurants that appear (aim for top 6-8 restaurants)
4. For each restaurant card on the search results page, extract:
   - Restaurant name
   - Rating (if visible)
   - Delivery time estimate
   - Distance or delivery fee (if visible)
   - Any visible menu items or prices related to "{search_term}"
5. Now visit the top 5 restaurants individually to get specific taco menu items:
   - Click on each restaurant
   - Look for menu items related to "{search_term}"
   - Get the name, price, and description of 1-2 best taco items from each restaurant
   - Capture the complete item URLs for ordering (full path like /store/restaurant-name/item-id)
   - Go back to search results and continue to next restaurant
6. Consolidate all results into a structured format showing:
   - Restaurant name, rating, delivery info
   - Available taco options with names, prices, descriptions
   - Complete ordering URLs for each item
7. Format the final response as a comprehensive taco guide for delivery to {delivery_address} with options from multiple restaurants
"""
    
    try:
        # Run the browser automation and wait for completion
        result = await run_browser_agent(task=task, on_step=None)
        
        # Extract the final result text from browser automation
        if hasattr(result, 'all_results') and result.all_results:
            # Get the last result which should be the final output
            final_result = result.all_results[-1]
            if hasattr(final_result, 'extracted_content'):
                content = final_result.extracted_content
                # Return structured data for Claude to process
                return f"Successfully found restaurants in {delivery_address}. {content}"
        
        # Fallback if result structure is different
        return f"Search completed for '{search_term}' in {delivery_address}. Browser automation finished successfully."
        
    except Exception as e:
        return f"Error searching for '{search_term}': {str(e)}"

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
async def order_food(item_url: str, item_name: str, context: Context) -> str:
    """Order food from a restaurant.
    
    Args:
        restaurant_url: URL of the restaurant
        item_name: Name of the item to order
    """
    
    task = f"""
1. Go to {item_url}
2. Click "Add to order"
3. Wait 3 seconds
4. Click "Go to checkout"
5. If there are upsell modals, click "Skip"
6. Click "Place order"
"""
    
    # Start the background task for ordering
    asyncio.create_task(
        perform_order(item_url, item_name, task, context)
    )
    
    # Return a message immediately
    return f"Order for '{item_name}' started. Your order is being processed."

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
