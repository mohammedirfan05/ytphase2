import json
import os
import re
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

from .config import AppConfig
from .prompt_builder import SYSTEM_PROMPT, build_user_prompt
from .validator import ScriptValidator


class ScriptGeneratorClient:
    """Client for generating scripts using Gemini Flash via the Google GenAI SDK."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set GEMINI_API_KEY in your environment or in a .env file."
            )
            
        self.client = genai.Client(api_key=self.api_key)
        self.validator = ScriptValidator(config)

    def generate(self, topic: str, num_variants: Optional[int] = None) -> Dict[str, Any]:
        """Generates script variants for a given topic and validates them."""
        user_prompt = build_user_prompt(topic, self.config, num_variants)
        
        # Configure Generation with system instructions and JSON response
        generate_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            response_mime_type="application/json"
        )
        
        response = self.client.models.generate_content(
            model=self.config.model,
            contents=user_prompt,
            config=generate_config
        )
        
        raw_text = response.text
        parsed_data = self._parse_json_response(raw_text)
        
        # Validate output against Phase 1 empirical benchmarks
        self.validator.validate_all(parsed_data)
        
        return parsed_data

    def _parse_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Safely parses JSON from LLM output, stripping markdown formatting if present."""
        text = raw_text.strip()
        # Strip markdown ```json ... ``` wrapper if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
            
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Fallback regex extraction of largest JSON object
            match = re.search(r'(\{[\s\S]*\})', text)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Failed to parse model JSON output: {e}\nRaw output:\n{raw_text}")
