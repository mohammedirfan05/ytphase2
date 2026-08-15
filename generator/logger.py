import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from .config import AppConfig


class GenerationLogger:
    """Handles persistent logging and JSON export for approved scripts."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Absolute path resolution
        base_dir = Path(__file__).resolve().parent.parent
        
        log_p = Path(self.config.log_file)
        if not log_p.is_absolute():
            log_p = base_dir / self.config.log_file
        self.log_path = log_p
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        scripts_p = Path(self.config.generated_scripts_dir)
        if not scripts_p.is_absolute():
            scripts_p = base_dir / self.config.generated_scripts_dir
        self.scripts_dir = scripts_p
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def log_generation_run(self, topic: str, response_data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Appends all generated variants to the history log."""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "topic": topic,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "metadata": metadata or {},
            "response": response_data
        }
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def save_approved_script(self, topic: str, variant: Dict[str, Any]) -> str:
        """
        Saves the single approved script variant into a standardized JSON file
        formatted for Google TTS and video synthesis.
        """
        safe_topic = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower()).strip('_')
        filename = f"{safe_topic}.json"
        file_path = self.scripts_dir / filename
        
        # Build clean TTS segment breakdown
        tts_segments = []
        script_lines = variant.get("script_lines", [])
        for idx, line in enumerate(script_lines, 1):
            tts_segments.append({
                "segment_id": idx,
                "timing": line.get("second_marker", ""),
                "move": line.get("move_name", ""),
                "text": line.get("text", "")
            })
            
        approved_payload = {
            "topic": topic,
            "approved_variant_id": variant.get("variant_id", 1),
            "angle_name": variant.get("angle_name", ""),
            "title": variant.get("suggested_title", ""),
            "hashtags": variant.get("suggested_hashtags", []),
            "estimated_duration_seconds": variant.get("estimated_duration_seconds", 0),
            "word_count": variant.get("word_count", 0),
            "speaking_pace_wps": self.config.words_per_second,
            "full_script_text": variant.get("full_script_text", ""),
            "final_rule_outro": variant.get("final_rule_outro", ""),
            "stickman_visual": variant.get("first_frame_visual", ""),
            "patterns_used": variant.get("phase1_patterns_used", []),
            "script_lines": script_lines,
            "tts_segments": tts_segments,
            "created_at": datetime.now().isoformat(),
            "status": "ready_for_tts"
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(approved_payload, f, indent=2, ensure_ascii=False)
            
        return str(file_path)
