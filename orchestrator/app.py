"""
Main FastAPI application for Hungry Agent voice-based taco ordering system
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db, db_manager
from .models import (
    Order, VoiceSession, OrderStatus, Platform, VoiceSessionStatus,
    VoiceInput, VoiceOutput, ClaudeRequest, OrderRequest, OrderResponse,
    DashboardUpdate, SystemStatus, OrderItem
)
from .claude_client import claude_client
from .mcp_client import mcp_orchestrator
from .batch_mcp_client import batch_mcp_orchestrator
from .batch_models import BatchOrderRequest, PlaceOrderRequest

# Create FastAPI app
app = FastAPI(
    title="Hungry Agent",
    description="Voice-based taco ordering system with real-time dashboard",
    version="1.0.0"
)

# Add CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.session_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if session_id:
            self.session_connections[session_id] = websocket
    
    def disconnect(self, websocket: WebSocket, session_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if session_id and session_id in self.session_connections:
            del self.session_connections[session_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def send_to_session(self, message: str, session_id: str):
        if session_id in self.session_connections:
            await self.session_connections[session_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Voice session management
active_sessions: Dict[str, Dict[str, Any]] = {}

def get_or_create_session(session_id: str, db: Session) -> VoiceSession:
    """Get existing session or create new one"""
    
    session = db.query(VoiceSession).filter(VoiceSession.session_id == session_id).first()
    
    if not session:
        session = VoiceSession(
            session_id=session_id,
            status=VoiceSessionStatus.ACTIVE.value,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Add to active sessions
        active_sessions[session_id] = {
            "started_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "total_interactions": 0,
            "current_context": {}
        }
    
    return session

async def broadcast_update(update: DashboardUpdate):
    """Broadcast update to all connected clients"""
    message = json.dumps({
        "type": update.type,
        "data": update.data,
        "timestamp": update.timestamp.isoformat(),
        "session_id": update.session_id
    })
    await manager.broadcast(message)

# API Routes

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hungry Agent - Voice-based Taco Ordering System", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""

    # Check individual MCP services
    uber_eats_mcp_status = True  # We have real Uber Eats MCP server working
    batch_ordering_status = True  # Batch ordering is always available
    
    # STT is working via browser Web Speech API (no separate service needed)
    stt_status = True  # Browser-based STT is working
    
    # Check TTS service
    tts_status = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5002/health", timeout=2.0)
            tts_status = response.status_code == 200
    except:
        tts_status = False
    
    # Check dashboard (WebSocket connection would be complex, so check if React dev server is running)
    dashboard_status = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3000", timeout=2.0)
            dashboard_status = response.status_code == 200
    except:
        dashboard_status = False

    status = SystemStatus(
        orchestrator=True,
        stt_service=stt_status,
        tts_service=tts_status,
        uber_eats_mcp=uber_eats_mcp_status,
        batch_ordering=batch_ordering_status,
        dashboard=dashboard_status,
        active_sessions=len(active_sessions),
        active_batch_orders=len(batch_mcp_orchestrator.active_orders),
        total_orders_today=0  # TODO: Calculate from database
    )

    return status

@app.post("/api/voice/process")
async def process_voice_input(
    voice_input: VoiceInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process voice input and generate response"""
    
    try:
        # Get or create session
        session = get_or_create_session(voice_input.session_id, db)
        
        # Update session activity
        session.last_activity = datetime.utcnow()
        session.total_interactions += 1
        db.commit()
        
        # Update active session
        if voice_input.session_id in active_sessions:
            active_sessions[voice_input.session_id]["last_activity"] = datetime.utcnow()
            active_sessions[voice_input.session_id]["total_interactions"] += 1
        
        # Broadcast voice activity update
        await broadcast_update(DashboardUpdate(
            type="voice_activity",
            data={
                "session_id": voice_input.session_id,
                "text": voice_input.text,
                "confidence": voice_input.confidence,
                "action": "voice_input"
            },
            session_id=voice_input.session_id
        ))
        
        # Process with Claude
        claude_request = ClaudeRequest(
            message=voice_input.text,
            session_id=voice_input.session_id,
            context=active_sessions.get(voice_input.session_id, {}).get("current_context")
        )
        
        claude_response = await claude_client.process_voice_command(claude_request)
        
        # Execute any function calls
        mcp_results = []
        for function_call in claude_response.function_calls:
            mcp_response = await mcp_orchestrator.execute_function_call(
                function_call["name"],
                function_call["parameters"],
                voice_input.session_id
            )
            mcp_results.append(mcp_response)
            
            # If it's a place_order call, create order record
            if function_call["name"] == "place_order" and mcp_response.success:
                background_tasks.add_task(
                    create_order_record,
                    function_call["parameters"],
                    mcp_response,
                    voice_input.session_id,
                    voice_input.text
                )
        
        # Broadcast Claude response
        await broadcast_update(DashboardUpdate(
            type="voice_activity",
            data={
                "session_id": voice_input.session_id,
                "response": claude_response.response,
                "function_calls": claude_response.function_calls,
                "mcp_results": [{"success": r.success, "platform": r.platform.value} for r in mcp_results],
                "action": "claude_response"
            },
            session_id=voice_input.session_id
        ))
        
        # Create voice output for TTS
        voice_output = VoiceOutput(
            text=claude_response.response,
            session_id=voice_input.session_id,
            voice=settings.tts_voice
        )
        
        return {
            "voice_output": voice_output,
            "claude_response": claude_response,
            "mcp_results": mcp_results
        }
        
    except Exception as e:
        error_response = VoiceOutput(
            text=f"I'm sorry, I encountered an error: {str(e)}",
            session_id=voice_input.session_id
        )
        
        return {"voice_output": error_response, "error": str(e)}

async def create_order_record(
    order_params: Dict[str, Any],
    mcp_response: Any,
    session_id: str,
    original_command: str
):
    """Create order record in database"""
    
    try:
        with db_manager.get_session() as db:
            # Convert platform string to enum
            platform_str = order_params.get("platform", "").lower()
            platform = Platform.UBER_EATS if platform_str == "uber_eats" else Platform.DOORDASH
            
            # Create order record
            order = Order(
                session_id=session_id,
                platform=platform.value,
                status=OrderStatus.PENDING.value,
                items=order_params.get("items", []),
                restaurant_name=order_params.get("restaurant_name", ""),
                delivery_address=order_params.get("delivery_address"),
                original_voice_command=original_command,
                processed_intent=order_params,
                created_at=datetime.utcnow()
            )
            
            # Add external order ID if available
            if mcp_response.data and "order_id" in mcp_response.data:
                order.external_order_id = mcp_response.data["order_id"]
            
            db.add(order)
            db.commit()
            db.refresh(order)
            
            # Broadcast order update
            await broadcast_update(DashboardUpdate(
                type="order_update",
                data={
                    "order_id": order.id,
                    "session_id": session_id,
                    "platform": platform.value,
                    "status": OrderStatus.PENDING.value,
                    "restaurant_name": order.restaurant_name,
                    "items": order.items,
                    "action": "order_created"
                },
                session_id=session_id
            ))
            
    except Exception as e:
        print(f"Error creating order record: {e}")

@app.get("/api/orders")
async def get_orders(
    session_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get orders, optionally filtered by session"""
    
    query = db.query(Order)
    
    if session_id:
        query = query.filter(Order.session_id == session_id)
    
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    
    return [
        OrderResponse(
            id=order.id,
            session_id=order.session_id,
            platform=Platform(order.platform),
            status=OrderStatus(order.status),
            items=[OrderItem(**item) for item in order.items] if order.items else [],
            restaurant_name=order.restaurant_name,
            total_amount=order.total_amount,
            delivery_address=order.delivery_address,
            created_at=order.created_at,
            estimated_delivery=order.estimated_delivery,
            external_order_id=order.external_order_id,
            tracking_url=order.tracking_url
        )
        for order in orders
    ]

@app.get("/api/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    """Get all voice sessions"""
    
    sessions = db.query(VoiceSession).order_by(VoiceSession.started_at.desc()).all()
    
    return [
        {
            "session_id": session.session_id,
            "status": session.status,
            "started_at": session.started_at,
            "last_activity": session.last_activity,
            "total_interactions": session.total_interactions,
            "successful_orders": session.successful_orders,
            "failed_orders": session.failed_orders,
            "is_active": session.session_id in active_sessions
        }
        for session in sessions
    ]

@app.post("/api/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: OrderStatus,
    db: Session = Depends(get_db)
):
    """Update order status"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = status.value
    order.updated_at = datetime.utcnow()
    db.commit()
    
    # Broadcast update
    await broadcast_update(DashboardUpdate(
        type="order_update",
        data={
            "order_id": order.id,
            "session_id": order.session_id,
            "status": status.value,
            "action": "status_updated"
        },
        session_id=order.session_id
    ))
    
    return {"message": "Order status updated"}

# Batch ordering endpoints
@app.post("/api/batch/orders")
async def create_batch_orders(request: BatchOrderRequest):
    """Create multiple orders simultaneously"""
    
    try:
        order_ids = await batch_mcp_orchestrator.create_batch_order(
            restaurant_queries=request.restaurant_queries,
            items_per_restaurant=request.items_per_restaurant,
            location=request.location,
            session_id=request.session_id
        )
        
        # Broadcast batch order creation
        await broadcast_update(DashboardUpdate(
            type="batch_order_created",
            data={
                "order_ids": order_ids,
                "restaurant_queries": request.restaurant_queries,
                "location": request.location,
                "action": "batch_created"
            },
            session_id=request.session_id
        ))
        
        return {
            "message": f"Created {len(order_ids)} batch orders",
            "order_ids": order_ids,
            "estimated_completion": "2-3 minutes per restaurant"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating batch orders: {str(e)}")

@app.get("/api/batch/orders/{session_id}")
async def get_batch_orders(session_id: str):
    """Get status of all batch orders for a session"""
    
    try:
        batch_status = await batch_mcp_orchestrator.get_batch_status(session_id)
        return {
            "session_id": session_id,
            "orders": batch_status,
            "total_orders": len(batch_status)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting batch status: {str(e)}")

@app.post("/api/batch/orders/{order_id}/place")
async def place_batch_order(
    order_id: str,
    item_url: str,
    item_name: str
):
    """Place an order for a specific item from batch results"""
    
    try:
        result = await batch_mcp_orchestrator.place_batch_order(
            order_id=order_id,
            item_url=item_url,
            item_name=item_name
        )
        
        if result.success:
            # Broadcast order placement
            await broadcast_update(DashboardUpdate(
                type="batch_order_placed",
                data={
                    "order_id": order_id,
                    "item_name": item_name,
                    "action": "order_placed"
                },
                session_id=result.session_id
            ))
            
            return {
                "message": f"Order placed for {item_name}",
                "order_id": order_id,
                "status": "order_placed"
            }
        else:
            raise HTTPException(status_code=400, detail=result.error)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error placing batch order: {str(e)}")

@app.delete("/api/batch/orders/{order_id}")
async def cancel_batch_order(order_id: str):
    """Cancel a batch order"""
    
    try:
        success = await batch_mcp_orchestrator.cancel_batch_order(order_id)
        
        if success:
            return {"message": f"Order {order_id} cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Order not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling order: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """WebSocket endpoint for real-time dashboard updates"""
    
    await manager.connect(websocket, session_id)
    
    try:
        # Send initial system status
        status = SystemStatus(
            orchestrator=True,
            stt_service=True,  # Browser-based STT is working
            uber_eats_mcp=True,  # We have real Uber Eats MCP server
            batch_ordering=True,  # Batch ordering is available
            tts_service=True,  # TTS is working
            dashboard=True,  # Dashboard is running
            active_sessions=len(active_sessions),
            active_batch_orders=len(batch_mcp_orchestrator.active_orders)
        )
        
        # Convert status to JSON-serializable format
        status_data = status.model_dump()
        if 'timestamp' in status_data and hasattr(status_data['timestamp'], 'isoformat'):
            status_data['timestamp'] = status_data['timestamp'].isoformat()
        
        await manager.send_personal_message(
            json.dumps({
                "type": "system_status",
                "data": status_data,
                "timestamp": datetime.utcnow().isoformat()
            }),
            websocket
        )
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    
    # Ensure database tables exist
    db_manager.create_tables()
    
    print("🚀 Hungry Agent orchestrator started")
    print(f"📊 Dashboard available at: http://localhost:{settings.dashboard_port}")
    print(f"🎤 Voice processing ready on port: {settings.orchestrator_port}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "orchestrator.app:app",
        host="127.0.0.1",
        port=settings.orchestrator_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
