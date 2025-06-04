"""
Pydantic models for batch ordering
"""

from typing import List
from pydantic import BaseModel


class BatchOrderRequest(BaseModel):
    restaurant_queries: List[str]
    items_per_restaurant: List[List[str]]
    location: str
    session_id: str


class PlaceOrderRequest(BaseModel):
    item_url: str
    item_name: str
