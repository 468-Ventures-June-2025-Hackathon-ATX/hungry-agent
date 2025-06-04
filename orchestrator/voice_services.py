"""
Voice services for Speech-to-Text (STT) and Text-to-Speech (TTS)
Optimized for Apple Silicon with Core ML Whisper and Metal TTS
"""

import asyncio
import json
import subprocess
import tempfile
import wave
from typing import Optional, AsyncGenerator
from pathlib import Path

import sounddevice as sd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings


class STTRequest(BaseModel):
    """Request for speech-to-text conversion"""
    audio_data: bytes
    session_id: str
    format: str = "wav"
    sample_rate: int = 16000


class STTResponse(BaseModel):
    """Response from speech-to-text conversion"""
    text: str
    confidence: float
    session_id: str
    processing_time_ms: int


class TTSRequest(BaseModel):
    """Request for text-to-speech conversion"""
    text: str
    session_id: str
    voice: str = "en-US-rf1"
    speed: float = 1.0


class TTSResponse(BaseModel):
    """Response from text-to-speech conversion"""
    audio_data: bytes
    session_id: str
    format: str = "wav"
    sample_rate: int = 22050


class WhisperSTTService:
    """Speech-to-Text service using Core ML optimized Whisper"""
    
    def __init__(self):
        self.model_path = Path("submodules/whisper.cpp")
        self.model_name = settings.whisper_model
        self.executable = self.model_path / "main"
        
        # Check if Whisper.cpp is built
        if not self.executable.exists():
            raise RuntimeError(
                "Whisper.cpp not found. Run 'just build-whisper' to build it."
            )
    
    async def transcribe_audio(self, audio_data: bytes, session_id: str) -> STTResponse:
        """Transcribe audio data to text using Core ML Whisper"""
        
        import time
        start_time = time.time()
        
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            # Run Whisper.cpp with Core ML
            cmd = [
                str(self.executable),
                "-m", str(self.model_path / f"models/ggml-{self.model_name}.bin"),
                "-f", temp_path,
                "--output-txt",
                "--no-timestamps",
                "--language", "en"
            ]
            
            # Execute Whisper
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Whisper failed: {result.stderr}")
            
            # Parse output
            text = result.stdout.strip()
            confidence = 0.9  # Whisper doesn't provide confidence, use default
            
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return STTResponse(
                text=text,
                confidence=confidence,
                session_id=session_id,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"STT processing failed: {str(e)}"
            )


class MetalTTSService:
    """Text-to-Speech service using Apple Metal acceleration"""
    
    def __init__(self):
        self.voice = settings.tts_voice
        
        # Check if 'say' command is available (macOS built-in TTS)
        try:
            subprocess.run(["say", "--version"], capture_output=True, check=True)
            self.use_system_tts = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.use_system_tts = False
            print("Warning: macOS 'say' command not available, using fallback TTS")
    
    async def synthesize_speech(self, text: str, session_id: str) -> TTSResponse:
        """Synthesize speech from text using Metal-accelerated TTS"""
        
        try:
            if self.use_system_tts:
                return await self._synthesize_with_say(text, session_id)
            else:
                return await self._synthesize_fallback(text, session_id)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"TTS processing failed: {str(e)}"
            )
    
    async def _synthesize_with_say(self, text: str, session_id: str) -> TTSResponse:
        """Use macOS built-in 'say' command for TTS"""
        
        # Create temporary file for audio output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Use macOS 'say' command
            cmd = [
                "say",
                "-v", self.voice,
                "-o", temp_path,
                "--data-format=LEI16@22050",
                text
            ]
            
            # Execute TTS
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"TTS failed: {result.stderr}")
            
            # Read generated audio
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
            return TTSResponse(
                audio_data=audio_data,
                session_id=session_id,
                format="wav",
                sample_rate=22050
            )
            
        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            raise e
    
    async def _synthesize_fallback(self, text: str, session_id: str) -> TTSResponse:
        """Fallback TTS implementation"""
        
        # Simple fallback - generate silence (for testing)
        duration = len(text) * 0.1  # Rough estimate
        sample_rate = 22050
        samples = int(duration * sample_rate)
        
        # Generate silence
        audio_array = np.zeros(samples, dtype=np.int16)
        
        # Convert to WAV bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Write WAV file
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_array.tobytes())
            
            # Read back as bytes
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
            
            return TTSResponse(
                audio_data=audio_data,
                session_id=session_id,
                format="wav",
                sample_rate=sample_rate
            )
            
        except Exception as e:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            raise e


class VoiceStreamManager:
    """Manages real-time voice streaming"""
    
    def __init__(self):
        self.stt_service = WhisperSTTService()
        self.tts_service = MetalTTSService()
        self.active_streams = {}
    
    async def start_voice_stream(self, session_id: str):
        """Start a voice stream for a session"""
        
        if session_id in self.active_streams:
            return  # Already active
        
        self.active_streams[session_id] = {
            "recording": False,
            "audio_buffer": [],
            "sample_rate": 16000
        }
    
    async def stop_voice_stream(self, session_id: str):
        """Stop a voice stream for a session"""
        
        if session_id in self.active_streams:
            del self.active_streams[session_id]
    
    async def process_audio_chunk(
        self, 
        session_id: str, 
        audio_chunk: bytes
    ) -> Optional[STTResponse]:
        """Process an audio chunk and return transcription if complete"""
        
        if session_id not in self.active_streams:
            await self.start_voice_stream(session_id)
        
        stream = self.active_streams[session_id]
        stream["audio_buffer"].append(audio_chunk)
        
        # Check if we have enough audio for transcription
        total_size = sum(len(chunk) for chunk in stream["audio_buffer"])
        
        # Process if we have at least 1 second of audio
        min_size = stream["sample_rate"] * 2  # 16-bit samples
        
        if total_size >= min_size:
            # Combine audio chunks
            combined_audio = b"".join(stream["audio_buffer"])
            stream["audio_buffer"] = []  # Clear buffer
            
            # Transcribe
            return await self.stt_service.transcribe_audio(combined_audio, session_id)
        
        return None


# Global services
stt_service = WhisperSTTService()
tts_service = MetalTTSService()
voice_stream_manager = VoiceStreamManager()


# FastAPI app for voice services
voice_app = FastAPI(title="Hungry Agent Voice Services")


@voice_app.post("/stt", response_model=STTResponse)
async def speech_to_text(request: STTRequest):
    """Convert speech to text"""
    return await stt_service.transcribe_audio(request.audio_data, request.session_id)


@voice_app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech"""
    return await tts_service.synthesize_speech(request.text, request.session_id)


@voice_app.get("/health")
async def voice_health():
    """Health check for voice services"""
    return {
        "stt_available": True,
        "tts_available": tts_service.use_system_tts,
        "whisper_model": settings.whisper_model,
        "tts_voice": settings.tts_voice
    }


# CLI interface for running voice services
if __name__ == "__main__":
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="Hungry Agent Voice Services")
    parser.add_argument("--service", choices=["stt", "tts", "both"], default="both")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", default="127.0.0.1")
    
    args = parser.parse_args()
    
    print(f"🎤 Starting {args.service} service on {args.host}:{args.port}")
    
    uvicorn.run(
        "orchestrator.voice_services:voice_app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info"
    )
