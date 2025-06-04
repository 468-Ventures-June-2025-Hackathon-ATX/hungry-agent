# 🌮 Hungry Agent - Production Usage Guide

## 🚀 Quick Start

### Start the System
```bash
./scripts/start.sh
```

### Stop the System
```bash
./scripts/stop.sh
```

## 📊 Access Points

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎤 Voice Commands

### Supported Commands
- "Search for tacos"
- "Find pizza"
- "Look for burgers"
- "Search for Mexican food"

### Expected Flow
1. Open dashboard at http://localhost:3000
2. Click microphone button
3. Speak your command
4. Watch Chrome browser open and search UberEats
5. Results processed and ready for speech output

## 🔧 System Components

### Core Services
- **Orchestrator**: FastAPI server (port 8000)
- **Dashboard**: React app (port 3000)
- **MCP Servers**: Started on-demand via stdio
- **Browser Automation**: Chrome launched for real searches

### Voice Processing
- **Input**: Web Speech API (browser microphone)
- **Processing**: Claude 3.5 Sonnet via Anthropic API
- **Output**: Text-to-speech ready responses

## 📝 Logs

All logs are stored in `logs/` directory:
- `logs/orchestrator.log` - Main API server logs
- `logs/dashboard.log` - React app logs
- `logs/voice-services.log` - Voice processing logs

## 🔍 Health Check

```bash
curl http://localhost:8000/health
```

## 🛠️ Troubleshooting

### Port Conflicts
If ports are in use:
```bash
lsof -i :8000  # Check orchestrator
lsof -i :3000  # Check dashboard
```

### Force Stop
```bash
./scripts/stop.sh  # Graceful shutdown
```

### Restart Services
```bash
./scripts/stop.sh && ./scripts/start.sh
```

## 🎯 Production Features

✅ **Voice Commands**: Natural language processing
✅ **Browser Automation**: Visible Chrome searches
✅ **Real Integration**: Actual UberEats searches
✅ **Graceful Shutdown**: Clean service termination
✅ **Health Monitoring**: Service status checks
✅ **Error Handling**: Robust error recovery

## 🌮 Ready for Production

The system is fully operational for single taco orders with:
- Reliable voice command processing
- Real browser automation
- UberEats integration
- Production-ready architecture
