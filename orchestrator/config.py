"""
Configuration management for Hungry Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    
    # Service Ports
    orchestrator_port: int = Field(8000, env="ORCHESTRATOR_PORT")
    dashboard_port: int = Field(3000, env="DASHBOARD_PORT")
    stt_port: int = Field(5001, env="STT_PORT")
    tts_port: int = Field(5002, env="TTS_PORT")
    uber_mcp_port: int = Field(7001, env="UBER_MCP_PORT")
    doordash_mcp_port: int = Field(7002, env="DOORDASH_MCP_PORT")
    
    # Food Service Credentials
    uber_eats_email: str = Field(..., env="UBER_EATS_EMAIL")
    uber_eats_password: str = Field(..., env="UBER_EATS_PASSWORD")
    
    # DoorDash API Credentials
    doordash_developer_id: str = Field(..., env="DOORDASH_DEVELOPER_ID")
    doordash_key_id: str = Field(..., env="DOORDASH_KEY_ID")
    doordash_signing_secret: str = Field(..., env="DOORDASH_SIGNING_SECRET")
    
    # Optional legacy DoorDash credentials
    doordash_email: Optional[str] = Field(None, env="DOORDASH_EMAIL")
    doordash_password: Optional[str] = Field(None, env="DOORDASH_PASSWORD")
    
    # Voice Configuration
    whisper_model: str = Field("tiny", env="WHISPER_MODEL")
    tts_voice: str = Field("en-US-rf1", env="TTS_VOICE")
    wake_word_enabled: bool = Field(False, env="WAKE_WORD_ENABLED")
    
    # Local Configuration
    local_db_path: str = Field("./database/orders.db", env="LOCAL_DB_PATH")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # MCP Server URLs
    @property
    def uber_mcp_url(self) -> str:
        return f"http://localhost:{self.uber_mcp_port}"
    
    @property
    def doordash_mcp_url(self) -> str:
        return f"http://localhost:{self.doordash_mcp_port}"
    
    @property
    def stt_url(self) -> str:
        return f"http://localhost:{self.stt_port}"
    
    @property
    def tts_url(self) -> str:
        return f"http://localhost:{self.tts_port}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
