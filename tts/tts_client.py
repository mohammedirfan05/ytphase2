import os
import wave
import io
from pathlib import Path
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from .config import TTSConfig


class GeminiTTSClient:
    """TTS Client implementing exact Gemini 3.1 Flash TTS settings from playground."""

    def __init__(self, config: Optional[TTSConfig] = None, api_key: Optional[str] = None):
        self.config = config or TTSConfig()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your .env file or environment."
            )
            
        self.client = genai.Client(api_key=self.api_key)

    def format_tts_prompt(self, script_text: str) -> str:
        """Formats the input prompt matching the exact Gemini TTS playground structure."""
        return (
            f"Scene: {self.config.scene}\n"
            f"Sample Context: {self.config.sample_context}\n\n"
            f"{self.config.speaker_label}:\n"
            f"{script_text.strip()}"
        )

    def generate_audio(self, script_text: str, output_path: str) -> Dict[str, Any]:
        """
        Generates voiceover audio for script_text using Gemini 3.1 Flash TTS (Puck voice, temp 0.9)
        and saves it to output_path.
        """
        prompt = self.format_tts_prompt(script_text)
        
        generate_config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.config.voice_name
                    )
                )
            )
        )
        
        response = self.client.models.generate_content(
            model=self.config.model,
            contents=prompt,
            config=generate_config
        )
        
        # Extract audio bytes
        audio_data = None
        mime_type = ""
        
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    audio_data = part.inline_data.data
                    mime_type = part.inline_data.mime_type or ""
                    break
                    
        if not audio_data:
            raise RuntimeError("No audio data returned from Gemini TTS API.")

        # Ensure output directory exists
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if already a valid RIFF/WAV file or raw PCM
        if audio_data.startswith(b'RIFF'):
            with open(out_file, "wb") as f:
                f.write(audio_data)
        else:
            # Raw PCM (L16, 24000Hz, mono, 16-bit) -> write standard WAV container
            with wave.open(str(out_file), "wb") as wav_file:
                wav_file.setnchannels(self.config.channels)
                wav_file.setsampwidth(self.config.sample_width)
                wav_file.setframerate(self.config.sample_rate)
                wav_file.writeframes(audio_data)

        file_size_kb = round(os.path.getsize(out_file) / 1024, 2)
        
        # Calculate actual audio duration
        duration_seconds = 0.0
        try:
            with wave.open(str(out_file), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration_seconds = round(frames / float(rate), 2)
        except Exception:
            pass

        return {
            "output_path": str(out_file),
            "file_size_kb": file_size_kb,
            "duration_seconds": duration_seconds,
            "voice": self.config.voice_name,
            "temperature": self.config.temperature,
            "mime_type": mime_type
        }
