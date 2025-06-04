"""
Anthropic Claude API client for processing voice commands and generating responses
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime

import anthropic
from anthropic import AsyncAnthropic

from .config import settings
from .models import ClaudeRequest, ClaudeResponse, OrderItem, Platform


class ClaudeClient:
    """Client for interacting with Anthropic Claude API"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"
        
        # System prompt for taco ordering
        self.system_prompt = """You are a friendly taco ordering assistant. Keep responses conversational but brief - 1 to 2 sentences maximum.

RESPONSE STYLE:
- Sound natural and helpful
- 1-2 sentences only
- Be conversational but efficient
- Acknowledge what they want clearly

EXAMPLES:
User: "I want three al pastor tacos"
You: "Great choice! Let me search for al pastor tacos for you."

User: "Search for tacos"
You: "Perfect! Searching for delicious taco options now."

User: "Find pizza"
You: "I'll find some great pizza places for you!"

User: "Check my order status"
You: "Sure thing! What's your order number?"

Keep it friendly and conversational but concise!"""
    
    async def process_voice_command(
        self, 
        request: ClaudeRequest
    ) -> ClaudeResponse:
        """Process a voice command and generate response with potential function calls"""
        
        try:
            # Prepare messages for Claude
            messages = [
                {
                    "role": "user",
                    "content": request.message
                }
            ]
            
            # Add context if available
            if request.context:
                context_msg = f"Context: {json.dumps(request.context)}"
                messages.insert(0, {
                    "role": "system", 
                    "content": context_msg
                })
            
            # Define available tools/functions
            tools = [
                {
                    "name": "search_restaurants",
                    "description": "Search for taco restaurants on Uber Eats",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'tacos', 'Mexican food')"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_menu",
                    "description": "Get menu items from a specific restaurant on Uber Eats",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "restaurant_id": {
                                "type": "string",
                                "description": "Restaurant identifier"
                            },
                            "restaurant_name": {
                                "type": "string",
                                "description": "Restaurant name"
                            }
                        },
                        "required": ["restaurant_name"]
                    }
                },
                {
                    "name": "place_order",
                    "description": "Place a taco order at a restaurant on Uber Eats",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "restaurant_name": {
                                "type": "string",
                                "description": "Name of the restaurant"
                            },
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "quantity": {"type": "integer", "minimum": 1},
                                        "customizations": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "notes": {"type": "string"}
                                    },
                                    "required": ["name", "quantity"]
                                }
                            },
                            "delivery_address": {
                                "type": "string",
                                "description": "Delivery address"
                            },
                            "special_instructions": {
                                "type": "string",
                                "description": "Special delivery instructions"
                            }
                        },
                        "required": ["restaurant_name", "items"]
                    }
                },
                {
                    "name": "check_order_status",
                    "description": "Check the status of an existing order on Uber Eats",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID to check"
                            }
                        },
                        "required": ["order_id"]
                    }
                },
                {
                    "name": "create_batch_orders",
                    "description": "Create multiple simultaneous orders from different restaurants on Uber Eats. Use this when the user wants to order from multiple restaurants at once.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "restaurant_queries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of restaurant search queries (e.g., ['tacos', 'pizza', 'burgers'])"
                            },
                            "items_per_restaurant": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "description": "List of items to order from each restaurant (e.g., [['beef tacos'], ['pepperoni pizza'], ['cheeseburger']])"
                            },
                            "location": {
                                "type": "string",
                                "description": "Delivery location (e.g., 'Austin, TX')"
                            }
                        },
                        "required": ["restaurant_queries", "items_per_restaurant", "location"]
                    }
                }
            ]
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=100,  # Allow for 1-2 sentence responses
                system=self.system_prompt,
                messages=messages,
                tools=tools
            )
            
            # Extract response text and function calls
            response_text = ""
            function_calls = []
            
            for content in response.content:
                if content.type == "text":
                    response_text += content.text
                elif content.type == "tool_use":
                    function_calls.append({
                        "id": content.id,
                        "name": content.name,
                        "parameters": content.input
                    })
            
            return ClaudeResponse(
                response=response_text,
                function_calls=function_calls,
                session_id=request.session_id,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            # Return error response
            return ClaudeResponse(
                response=f"I'm sorry, I encountered an error processing your request: {str(e)}",
                function_calls=[],
                session_id=request.session_id,
                timestamp=datetime.utcnow()
            )
    
    async def stream_response(
        self, 
        request: ClaudeRequest
    ) -> AsyncGenerator[str, None]:
        """Stream Claude's response for real-time TTS"""
        
        try:
            messages = [{"role": "user", "content": request.message}]
            
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=1000,
                system=self.system_prompt,
                messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            yield f"I'm sorry, I encountered an error: {str(e)}"
    
    def extract_order_intent(self, text: str) -> Dict[str, Any]:
        """Extract order intent from voice command using simple parsing"""
        
        # Simple intent extraction (could be enhanced with NLP)
        intent = {
            "action": "unknown",
            "items": [],
            "platform": None,
            "restaurant": None,
            "quantity_total": 0
        }
        
        text_lower = text.lower()
        
        # Detect action
        if any(word in text_lower for word in ["order", "get", "buy", "want"]):
            intent["action"] = "place_order"
        elif any(word in text_lower for word in ["status", "check", "where"]):
            intent["action"] = "check_status"
        elif any(word in text_lower for word in ["search", "find", "look"]):
            intent["action"] = "search"
        
        # Detect platform
        if "uber" in text_lower or "uber eats" in text_lower:
            intent["platform"] = "uber_eats"
        elif "doordash" in text_lower or "door dash" in text_lower:
            intent["platform"] = "doordash"
        
        # Extract taco types and quantities
        taco_types = [
            "al pastor", "carnitas", "carne asada", "chicken", "beef", 
            "fish", "shrimp", "veggie", "bean", "cheese"
        ]
        
        for taco_type in taco_types:
            if taco_type in text_lower:
                # Try to find quantity
                import re
                pattern = rf"(\d+)\s*{taco_type}"
                match = re.search(pattern, text_lower)
                quantity = int(match.group(1)) if match else 1
                
                intent["items"].append({
                    "name": f"{taco_type} taco",
                    "quantity": quantity
                })
                intent["quantity_total"] += quantity
        
        # If no specific tacos found but "taco" mentioned
        if not intent["items"] and "taco" in text_lower:
            import re
            quantity_match = re.search(r"(\d+)\s*taco", text_lower)
            quantity = int(quantity_match.group(1)) if quantity_match else 1
            
            intent["items"].append({
                "name": "taco",
                "quantity": quantity
            })
            intent["quantity_total"] = quantity
        
        return intent


# Global Claude client instance
claude_client = ClaudeClient()
