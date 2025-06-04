#!/usr/bin/env python3
"""
Fast Taco Search MCP Server
Provides lightning-fast taco restaurant and menu searches using pre-compiled SQLite database
"""

import sqlite3
import json
import sys
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP, Context
import anthropic

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

# Initialize Anthropic client
anthropic_client = None
try:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        anthropic_client = anthropic.Anthropic(api_key=api_key)
    else:
        print("Warning: ANTHROPIC_API_KEY not found. Intelligent search will be disabled.")
except Exception as e:
    print(f"Warning: Could not initialize Anthropic client: {e}")

def get_db_connection():
    """Get SQLite database connection"""
    return sqlite3.connect(str(DB_PATH))

def dict_factory(cursor, row):
    """Convert SQLite row to dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_full_database_context():
    """Get all restaurants and reviews for Claude analysis"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            # Get all restaurants with aggregated review data
            cursor.execute("""
                SELECT r.id, r.name, r.address, r.hours, r.best_taco,
                       COUNT(rev.id) as review_count,
                       ROUND(AVG(rev.rating), 1) as avg_rating,
                       GROUP_CONCAT(rev.text, ' | ') as all_reviews
                FROM taco_restaurants r
                LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                GROUP BY r.id, r.name, r.address, r.hours, r.best_taco
                ORDER BY avg_rating DESC, review_count DESC
            """)
            
            restaurants = cursor.fetchall()
            
            # Format for Claude
            formatted_data = []
            for restaurant in restaurants:
                restaurant_data = {
                    "name": restaurant['name'],
                    "address": restaurant['address'],
                    "rating": restaurant['avg_rating'],
                    "review_count": restaurant['review_count'],
                    "best_taco": restaurant['best_taco'],
                    "reviews": restaurant['all_reviews'][:1000] if restaurant['all_reviews'] else ""  # Limit review text
                }
                formatted_data.append(restaurant_data)
            
            return formatted_data
            
    except Exception as e:
        print(f"Error getting database context: {e}")
        return []

async def intelligent_search_with_claude(query: str, limit: int = 10) -> str:
    """Use Claude to intelligently search the entire database"""
    
    if not anthropic_client:
        # Fallback to regular search if Claude not available
        return await search_tacos_fallback(query, limit)
    
    try:
        # Get full database context
        database_context = get_full_database_context()
        
        if not database_context:
            return "Error: Could not load restaurant database."
        
        # Prepare context for Claude
        context_json = json.dumps(database_context, indent=2)
        
        # Create prompt for Claude
        prompt = f"""You are a taco restaurant expert analyzing a database of Austin, TX taco restaurants. 

DATABASE CONTEXT:
{context_json}

USER QUERY: "{query}"

Please analyze the database and find the best {limit} restaurants that match the user's query. Consider:
- Restaurant names and specialties
- Menu items mentioned in reviews
- Review content and sentiment
- Ratings and popularity
- Semantic matching (e.g., "steak tacos" should match "carne asada", "beef", "bistec")

Return your response in this exact format:
RESULTS: [number] restaurants found for "{query}"

1. [Restaurant Name] - [Address] (★[Rating], [Review Count] reviews)
   Best Match: [Why this restaurant matches the query]
   Specialty: [Best taco or specialty item]

2. [Restaurant Name] - [Address] (★[Rating], [Review Count] reviews)
   Best Match: [Why this restaurant matches the query]
   Specialty: [Best taco or specialty item]

[Continue for all results...]

Focus on semantic understanding and provide clear explanations for why each restaurant matches the query."""

        # Call Claude
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract and return Claude's response
        claude_result = response.content[0].text
        return claude_result
        
    except Exception as e:
        print(f"Error with Claude intelligent search: {e}")
        # Fallback to regular search
        return await search_tacos_fallback(query, limit)

async def search_tacos_fallback(query: str, limit: int = 10) -> str:
    """Fallback search function when Claude is not available"""
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
async def search_tacos(query: str, context: Context, limit: int = 10) -> str:
    """Search for taco restaurants using AI-powered semantic search with full database context.
    
    Args:
        query: Search term (restaurant name, location, or general search like 'steak tacos', 'spicy tacos')
        limit: Maximum number of results to return (default: 10)
    """
    # Use intelligent search with Claude if available, fallback to basic search
    return await intelligent_search_with_claude(query, limit)

@mcp.tool()
async def intelligent_search(query: str, context: Context, limit: int = 10) -> str:
    """Advanced AI-powered search that analyzes the entire database including reviews for semantic matching.
    
    Args:
        query: Natural language search query (e.g., 'best steak tacos', 'spicy beef tacos', 'carne asada')
        limit: Maximum number of results to return (default: 10)
    """
    return await intelligent_search_with_claude(query, limit)

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
