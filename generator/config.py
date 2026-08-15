import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv

# Automatically locate and load .env file
load_dotenv(find_dotenv(usecwd=True))


class AppConfig(BaseModel):
    model: str = Field(default="gemini-3.6-flash", description="Gemini model identifier")
    temperature: float = Field(default=0.7, description="Generation temperature")
    max_output_tokens: int = Field(default=8192, description="Maximum tokens for generation")
    
    target_duration_seconds: int = Field(default=26, description="Target duration in seconds")
    min_duration_seconds: int = Field(default=21, description="Minimum duration in seconds")
    max_duration_seconds: int = Field(default=30, description="Maximum duration in seconds")
    words_per_second: float = Field(default=2.8, description="Voiceover speaking rate")
    max_word_count: int = Field(default=85, description="Maximum total word count per script")
    
    default_num_variants: int = Field(default=3, description="Number of script variants generated")
    include_forward_tease: bool = Field(default=True, description="Whether to include a forward tease outro")
    
    tone_profile: str = Field(
        default="confident referee, fast-paced, high energy, crisp, zero throat-clearing",
        description="Tone profile descriptor"
    )
    voice_perspective: str = Field(
        default="objective third-person referee settling a heated fan debate",
        description="Voice perspective"
    )
    
    forbidden_phrases: List[str] = Field(
        default_factory=lambda: [
            "did you know", "in conclusion", "basically", "here's the thing",
            "let's dive in", "in today's video", "it's important to note",
            "some might say", "at the end of the day", "without further ado",
            "mind-blowing", "game-changer", "fascinating", "have you ever wondered"
        ]
    )
    
    max_sentence_words: int = Field(default=9, description="Target maximum words per sentence")
    max_single_allowed_long_sentence: int = Field(default=12, description="Absolute maximum allowed words for a single sentence")
    
    generated_scripts_dir: str = Field(default="generated_scripts", description="Directory to save approved JSON scripts")
    log_file: str = Field(default="logs/generations_log.jsonl", description="Path to generation log file")
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API Key from env")


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Loads configuration from YAML file and merges with environment variables."""
    cfg_data = {}
    
    p = Path(config_path)
    if not p.exists():
        fallback = Path(__file__).resolve().parent.parent / config_path
        if fallback.exists():
            p = fallback
            
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            cfg_data = yaml.safe_load(f) or {}
            
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        cfg_data["gemini_api_key"] = api_key
        
    return AppConfig(**cfg_data)
