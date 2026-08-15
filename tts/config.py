from pydantic import BaseModel, Field
from typing import Optional


class TTSConfig(BaseModel):
    model: str = Field(default="gemini-3.1-flash-tts-preview", description="Gemini TTS Model")
    voice_name: str = Field(default="Puck", description="Prebuilt voice name")
    temperature: float = Field(default=0.9, description="Strict temperature for TTS from playground settings")
    
    scene: str = Field(
        default="A fast-paced educational explainer breaking down story terminology, direct-to-camera style",
        description="Scene direction prompt for Gemini TTS"
    )
    sample_context: str = Field(
        default="Energetic YouTube Shorts narration, quick pacing, conversational but confident tone",
        description="Sample context direction for Gemini TTS"
    )
    speaker_label: str = Field(
        default="Speaker 1 - Puck",
        description="Speaker block header"
    )
    
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Audio channels (mono)")
    sample_width: int = Field(default=2, description="16-bit audio sample width in bytes")
