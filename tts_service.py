#!/usr/bin/env python3
"""
Text-to-Speech service for Hungry Agent
Uses system TTS capabilities
"""

import asyncio
import json
import subprocess
import tempfile
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Hungry Agent TTS Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-rf1"
    session_id: str

class TTSResponse(BaseModel):
    audio_url: str
    session_id: str
    timestamp: str

# Store generated audio files temporarily
audio_files = {}

@app.get("/")
async def root():
    return {"message": "Hungry Agent TTS Service", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tts"}

@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(request: TTSRequest):
    """Convert text to speech and return audio file URL"""
    
    try:
        # Create temporary file for audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        # Use macOS built-in 'say' command for TTS
        # You can replace this with other TTS engines like espeak, festival, etc.
        process = subprocess.run([
            'say', 
            '-o', temp_file.name,
            '--data-format=LEF32@22050',
            request.text
        ], capture_output=True, text=True)
        
        if process.returncode != 0:
            # Fallback: create a simple beep if TTS fails
            subprocess.run(['say', 'TTS service ready'], capture_output=True)
            raise HTTPException(status_code=500, detail="TTS synthesis failed")
        
        # Store file reference
        file_id = f"audio_{request.session_id}_{int(datetime.now().timestamp())}"
        audio_files[file_id] = temp_file.name
        
        # Clean up old files (keep only last 10)
        if len(audio_files) > 10:
            oldest_key = list(audio_files.keys())[0]
            old_file = audio_files.pop(oldest_key)
            try:
                os.unlink(old_file)
            except:
                pass
        
        return TTSResponse(
            audio_url=f"/audio/{file_id}",
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

@app.get("/audio/{file_id}")
async def get_audio(file_id: str):
    """Serve audio file"""
    
    if file_id not in audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    file_path = audio_files[file_id]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    return FileResponse(
        file_path,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline"}
    )

@app.post("/speak")
async def speak_text(request: TTSRequest):
    """Immediately speak text using system TTS (for testing)"""
    
    try:
        # Use macOS 'say' command to speak immediately
        process = subprocess.run(['say', request.text], capture_output=True, text=True)
        
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail="TTS speak failed")
        
        return {"message": "Text spoken successfully", "text": request.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS speak error: {str(e)}")

if __name__ == "__main__":
    print("🔊 Starting TTS Service on port 5002")
    uvicorn.run(
        "tts_service:app",
        host="127.0.0.1",
        port=5002,
        reload=True
    )
