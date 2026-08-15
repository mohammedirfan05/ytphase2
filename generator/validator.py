import re
from typing import Dict, List, Any
from .config import AppConfig


class ScriptValidator:
    """Validates generated scripts against empirical channel retention rules."""
    
    def __init__(self, config: AppConfig):
        self.config = config

    def validate_variant(self, variant: Dict[str, Any]) -> Dict[str, Any]:
        """Runs linting and validation on a single script variant."""
        full_text = variant.get("full_script_text", "")
        if not full_text and "script_lines" in variant:
            full_text = " ".join(line.get("text", "") for line in variant["script_lines"])
            
        words = full_text.split()
        word_count = len(words)
        
        # Calculate spoken duration based on channel delivery rate (2.8 wps)
        duration_seconds = round(word_count / self.config.words_per_second, 1)
        
        issues = []
        warnings = []
        
        # 1. Word count & duration checks
        if duration_seconds > self.config.max_duration_seconds:
            issues.append(
                f"Duration ({duration_seconds}s) exceeds max ceiling of {self.config.max_duration_seconds}s. (Word count: {word_count})"
            )
        elif duration_seconds < self.config.min_duration_seconds:
            warnings.append(
                f"Duration ({duration_seconds}s) is below recommended {self.config.min_duration_seconds}s minimum."
            )
            
        if word_count > self.config.max_word_count:
            issues.append(
                f"Word count ({word_count}) exceeds hard limit of {self.config.max_word_count} words."
            )
            
        # 2. Forbidden phrases / AI slop check
        text_lower = full_text.lower()
        for phrase in self.config.forbidden_phrases:
            if phrase in text_lower:
                issues.append(f"Contains forbidden AI slop phrase: '{phrase}'")
                
        # 3. Sentence length check
        sentences = [s.strip() for s in re.split(r'[.!?]+', full_text) if s.strip()]
        long_sentences = []
        for s in sentences:
            s_words = len(s.split())
            if s_words > self.config.max_single_allowed_long_sentence:
                long_sentences.append((s, s_words))
                
        if long_sentences:
            for s, s_words in long_sentences:
                warnings.append(
                    f"Sentence exceeds max allowed length ({s_words} words): '{s}'"
                )
                
        # 4. Check for Move 1 (Declaration) & Move 2 (Contract)
        script_lines = variant.get("script_lines", [])
        if script_lines:
            first_line = script_lines[0].get("text", "").lower()
            if not ("this is" in first_line):
                warnings.append("First line does not start with standard 'This is [A]. This is [B].' declaration.")
                
            if len(script_lines) > 1:
                second_line = script_lines[1].get("text", "").lower()
                if "what's the difference" not in second_line and "what is the difference" not in second_line:
                    warnings.append("Second line does not contain the 'So what's the difference?' contract.")

        # Update computed fields in the variant dict
        variant["word_count"] = word_count
        variant["estimated_duration_seconds"] = duration_seconds
        
        is_valid = len(issues) == 0
        return {
            "is_valid": is_valid,
            "issues": issues,
            "warnings": warnings,
            "word_count": word_count,
            "estimated_duration_seconds": duration_seconds,
            "compliance_score": max(0, 100 - (len(issues) * 25) - (len(warnings) * 10))
        }

    def validate_all(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates all variants in a generation response."""
        results = []
        all_valid = True
        for v in response_data.get("variants", []):
            res = self.validate_variant(v)
            v["validation"] = res
            results.append(res)
            if not res["is_valid"]:
                all_valid = False
                
        return {
            "all_valid": all_valid,
            "variant_results": results
        }
