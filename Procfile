# Hungry Agent Voice-Based Taco Ordering System
# Process definitions for foreman

# Core voice processing services
stt: python -m orchestrator.voice_services --service stt --port $STT_PORT
tts: python -m orchestrator.voice_services --service tts --port $TTS_PORT

# Main orchestrator with Claude integration
orchestrator: uvicorn orchestrator.app:app --host 127.0.0.1 --port $ORCHESTRATOR_PORT --reload

# MCP servers for food ordering
uber-mcp: cd submodules/uber-eats-mcp-server && python server.py --port $UBER_MCP_PORT
doordash-mcp: cd submodules/doordash-mcp-server && node index.js --port $DOORDASH_MCP_PORT

# Optional real-time dashboard
dashboard: cd dashboard && npm run dev -- --port $DASHBOARD_PORT
