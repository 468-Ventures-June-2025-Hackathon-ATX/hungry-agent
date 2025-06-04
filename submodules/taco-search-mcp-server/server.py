#!/usr/bin/env python3
"""
Fast Taco Search MCP Server
Provides lightning-fast taco restaurant and menu searches using pre-compiled SQLite database
"""

import sqlite3
import json
import sys
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP, Context

# Configure logging to stderr
logging.basicConfig(
    level=logging.CRITICAL,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize FastMCP server
mcp = FastMCP("taco_search")

# Database path
DB_PATH = Path(__file__).parent / "taco_restaurants.db"

def get_db_connection():
    """Get SQLite database connection"""
    return sqlite3.connect(str(DB_PATH))

def dict_factory(cursor, row):
    """Convert SQLite row to dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@mcp.tool()
async def search_tacos(query: str, context: Context, limit: int = 10) -> str:
    """Search for taco restaurants by name, location, or description.
    
    Args:
        query: Search term (restaurant name, location, or general search)
        limit: Maximum number of results to return (default: 10)
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            # Search restaurants by name or address
            search_query = f"%{query.lower()}%"
            cursor.execute("""
                SELECT r.id, r.name, r.address, r.hours, r.best_taco,
                       COUNT(rev.id) as review_count,
                       ROUND(AVG(rev.rating), 1) as avg_rating
                FROM taco_restaurants r
                LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                WHERE LOWER(r.name) LIKE ? OR LOWER(r.address) LIKE ?
                GROUP BY r.id, r.name, r.address, r.hours, r.best_taco
                ORDER BY avg_rating DESC, review_count DESC
                LIMIT ?
            """, (search_query, search_query, limit))
            
            results = cursor.fetchall()
            
            if not results:
                return f"No taco restaurants found matching '{query}'. Try searching for 'tacos', a restaurant name, or Austin area."
            
            # Format results for voice response
            response_parts = [f"Found {len(results)} taco restaurants for '{query}':"]
            
            for i, restaurant in enumerate(results, 1):
                name = restaurant['name']
                address = restaurant['address'].split(',')[0]  # Just street address
                rating = restaurant['avg_rating'] or "No rating"
                review_count = restaurant['review_count']
                best_taco = restaurant['best_taco'] if restaurant['best_taco'] != 'Unknown' else None
                
                # Parse hours for current availability
                try:
                    hours_data = json.loads(restaurant['hours']) if restaurant['hours'] else {}
                    # Simplified - could add current day/time logic
                    hours_info = "Hours available" if hours_data else "Hours unknown"
                except:
                    hours_info = "Hours unknown"
                
                restaurant_info = f"{i}. {name} - {address}"
                if rating != "No rating":
                    restaurant_info += f" (★{rating}"
                    if review_count > 0:
                        restaurant_info += f", {review_count} reviews)"
                    else:
                        restaurant_info += ")"
                
                if best_taco:
                    restaurant_info += f" - Best: {best_taco}"
                
                response_parts.append(restaurant_info)
            
            return "\n".join(response_parts)
            
    except Exception as e:
        return f"Error searching for tacos: {str(e)}"

@mcp.tool()
async def get_restaurant_details(restaurant_name: str, context: Context) -> str:
    """Get detailed information about a specific taco restaurant.
    
    Args:
        restaurant_name: Name of the restaurant to get details for
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            # Find restaurant by name (fuzzy match)
            search_name = f"%{restaurant_name.lower()}%"
            cursor.execute("""
                SELECT r.id, r.name, r.address, r.hours, r.best_taco,
                       COUNT(rev.id) as review_count,
                       ROUND(AVG(rev.rating), 1) as avg_rating
                FROM taco_restaurants r
                LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                WHERE LOWER(r.name) LIKE ?
                GROUP BY r.id, r.name, r.address, r.hours, r.best_taco
                ORDER BY LENGTH(r.name) ASC
                LIMIT 1
            """, (search_name,))
            
            restaurant = cursor.fetchone()
            
            if not restaurant:
                return f"Restaurant '{restaurant_name}' not found. Try searching with 'search_tacos' first."
            
            # Get recent reviews
            cursor.execute("""
                SELECT text, rating, date
                FROM reviews
                WHERE restaurant_id = ?
                ORDER BY date DESC
                LIMIT 3
            """, (restaurant['id'],))
            
            reviews = cursor.fetchall()
            
            # Format detailed response
            response_parts = [
                f"🌮 {restaurant['name']}",
                f"📍 {restaurant['address']}"
            ]
            
            if restaurant['avg_rating']:
                response_parts.append(f"⭐ {restaurant['avg_rating']}/5 ({restaurant['review_count']} reviews)")
            
            if restaurant['best_taco'] and restaurant['best_taco'] != 'Unknown':
                response_parts.append(f"🏆 Best Taco: {restaurant['best_taco']}")
            
            # Parse and format hours
            try:
                if restaurant['hours']:
                    hours_data = json.loads(restaurant['hours'])
                    hours_list = []
                    for day, hours in hours_data.items():
                        if hours:
                            hours_list.append(f"{day}: {hours}")
                        else:
                            hours_list.append(f"{day}: Closed")
                    if hours_list:
                        response_parts.append("🕒 Hours:")
                        response_parts.extend([f"  {h}" for h in hours_list])
            except:
                pass
            
            # Add recent reviews
            if reviews:
                response_parts.append("\n💬 Recent Reviews:")
                for review in reviews:
                    rating_stars = "⭐" * int(review['rating']) if review['rating'] else ""
                    review_text = review['text'][:100] + "..." if len(review['text']) > 100 else review['text']
                    response_parts.append(f"  {rating_stars} {review_text}")
            
            return "\n".join(response_parts)
            
    except Exception as e:
        return f"Error getting restaurant details: {str(e)}"

@mcp.tool()
async def get_top_rated_tacos(context: Context, limit: int = 5) -> str:
    """Get the top-rated taco restaurants in Austin.
    
    Args:
        limit: Number of top restaurants to return (default: 5)
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.name, r.address, r.best_taco,
                       COUNT(rev.id) as review_count,
                       ROUND(AVG(rev.rating), 1) as avg_rating
                FROM taco_restaurants r
                LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                GROUP BY r.id, r.name, r.address, r.best_taco
                HAVING review_count >= 3
                ORDER BY avg_rating DESC, review_count DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            
            if not results:
                return "No highly-rated taco restaurants found with sufficient reviews."
            
            response_parts = [f"🏆 Top {len(results)} Rated Taco Restaurants in Austin:"]
            
            for i, restaurant in enumerate(results, 1):
                name = restaurant['name']
                address = restaurant['address'].split(',')[0]
                rating = restaurant['avg_rating']
                review_count = restaurant['review_count']
                best_taco = restaurant['best_taco'] if restaurant['best_taco'] != 'Unknown' else None
                
                restaurant_info = f"{i}. {name} - ⭐{rating} ({review_count} reviews)"
                if best_taco:
                    restaurant_info += f" - {best_taco}"
                restaurant_info += f" - {address}"
                
                response_parts.append(restaurant_info)
            
            return "\n".join(response_parts)
            
    except Exception as e:
        return f"Error getting top-rated tacos: {str(e)}"

@mcp.tool()
async def search_by_area(area: str, context: Context, limit: int = 8) -> str:
    """Search for taco restaurants in a specific Austin area or neighborhood.
    
    Args:
        area: Area, neighborhood, or street name in Austin
        limit: Maximum number of results (default: 8)
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            search_area = f"%{area.lower()}%"
            cursor.execute("""
                SELECT r.id, r.name, r.address, r.best_taco,
                       COUNT(rev.id) as review_count,
                       ROUND(AVG(rev.rating), 1) as avg_rating
                FROM taco_restaurants r
                LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                WHERE LOWER(r.address) LIKE ?
                GROUP BY r.id, r.name, r.address, r.best_taco
                ORDER BY avg_rating DESC, review_count DESC
                LIMIT ?
            """, (search_area, limit))
            
            results = cursor.fetchall()
            
            if not results:
                return f"No taco restaurants found in '{area}' area. Try searching for a different Austin neighborhood or street."
            
            response_parts = [f"🌮 Taco restaurants in {area} area:"]
            
            for i, restaurant in enumerate(results, 1):
                name = restaurant['name']
                address = restaurant['address']
                rating = restaurant['avg_rating'] or "No rating"
                best_taco = restaurant['best_taco'] if restaurant['best_taco'] != 'Unknown' else None
                
                restaurant_info = f"{i}. {name} - {address}"
                if rating != "No rating":
                    restaurant_info += f" (⭐{rating})"
                if best_taco:
                    restaurant_info += f" - {best_taco}"
                
                response_parts.append(restaurant_info)
            
            return "\n".join(response_parts)
            
    except Exception as e:
        return f"Error searching by area: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
