"""
Data models for the Hungry Agent system
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import JSON

Base = declarative_base()


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Platform(str, Enum):
    """Food delivery platform enumeration"""
    UBER_EATS = "uber_eats"


class VoiceSessionStatus(str, Enum):
    """Voice session status"""
    ACTIVE = "active"
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


# SQLAlchemy Models
class Order(Base):
    """Database model for orders"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    platform = Column(String)  # Platform enum
    status = Column(String)    # OrderStatus enum
    
    # Order details
    items = Column(JSON)  # List of ordered items
    restaurant_name = Column(String)
    total_amount = Column(Float)
    delivery_address = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)
    
    # External IDs
    external_order_id = Column(String, nullable=True)
    tracking_url = Column(String, nullable=True)
    
    # Voice interaction
    original_voice_command = Column(Text)
    processed_intent = Column(JSON)


class VoiceSession(Base):
    """Database model for voice sessions"""
    __tablename__ = "voice_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    status = Column(String)  # VoiceSessionStatus enum
    
    # Session details
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Voice data
    total_interactions = Column(Integer, default=0)
    successful_orders = Column(Integer, default=0)
    failed_orders = Column(Integer, default=0)


# Pydantic Models for API
class OrderItem(BaseModel):
    """Individual order item"""
    name: str
    quantity: int = 1
    price: Optional[float] = None
    customizations: List[str] = []
    notes: Optional[str] = None


class OrderRequest(BaseModel):
    """Request to create a new order"""
    platform: Platform
    restaurant_name: Optional[str] = None
    items: List[OrderItem]
    delivery_address: Optional[str] = None
    voice_command: str
    session_id: str


class OrderResponse(BaseModel):
    """Response for order operations"""
    id: int
    session_id: str
    platform: Platform
    status: OrderStatus
    items: List[OrderItem]
    restaurant_name: Optional[str] = None
    total_amount: Optional[float] = None
    delivery_address: Optional[str] = None
    created_at: datetime
    estimated_delivery: Optional[datetime] = None
    external_order_id: Optional[str] = None
    tracking_url: Optional[str] = None


class VoiceInput(BaseModel):
    """Voice input from STT"""
    text: str
    confidence: float
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    delivery_address: Optional[str] = None


class VoiceOutput(BaseModel):
    """Voice output for TTS"""
    text: str
    session_id: str
    voice: str = "en-US-rf1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClaudeRequest(BaseModel):
    """Request to Claude API"""
    message: str
    session_id: str
    context: Optional[Dict[str, Any]] = None


class ClaudeResponse(BaseModel):
    """Response from Claude API"""
    response: str
    function_calls: List[Dict[str, Any]] = []
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPRequest(BaseModel):
    """Request to MCP server"""
    action: str
    parameters: Dict[str, Any]
    platform: Platform
    session_id: str


class MCPResponse(BaseModel):
    """Response from MCP server"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    platform: Platform
    session_id: str


class DashboardUpdate(BaseModel):
    """Real-time update for dashboard"""
    type: str  # "order_update", "voice_activity", "system_status"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class SystemStatus(BaseModel):
    """System health status"""
    orchestrator: bool = True
    stt_service: bool = False
    tts_service: bool = False
    uber_eats_mcp: bool = False
    taco_search_mcp: bool = False
    batch_ordering: bool = False
    dashboard: bool = False
    active_sessions: int = 0
    active_batch_orders: int = 0
    total_orders_today: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
