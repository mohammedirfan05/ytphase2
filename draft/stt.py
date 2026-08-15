"""
Speech-to-Text & Word-Level Timestamp Extraction using faster-whisper
"""

import os
import re
import difflib
import wave
from pathlib import Path
from typing import List, Dict, Optional


def format_srt_timestamp(seconds: float) -> str:
    """Format float seconds to SRT timestamp string HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_timestamp(ts: str) -> float:
    """Parse SRT timestamp string HH:MM:SS,mmm to float seconds."""
    ts = ts.strip().replace('.', ',')
    hms, ms = ts.split(',')
    h, m, s = hms.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt_timestamp_to_us(ts: str) -> int:
    """Parse SRT timestamp to microseconds."""
    return int(round(parse_srt_timestamp(ts) * 1_000_000))


def get_wav_duration_us(wav_path: str) -> int:
    """Get exact WAV duration in microseconds via Python's standard wave library."""
    try:
        with wave.open(str(wav_path), 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return int((frames / float(rate)) * 1_000_000)
    except Exception:
        pass
    return 0


def sanitize_reference_script(raw_text: str) -> str:
    """Strips bracketed non-spoken tags from reference script."""
    if not raw_text:
        return ""
    text = re.sub(r'\[IMG:\s*[^\]]+?\]', '', raw_text)
    text = re.sub(r'\[[^\]]*\]|<[^>]*>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n\s*\n+', '\n', text).strip()


def transcribe_audio_words(audio_path: str, model_size: str = "base") -> List[Dict]:
    """
    Transcribes audio using faster-whisper to extract millisecond-accurate word timestamps.
    """
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(audio_path), word_timestamps=True)
        
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    cleaned_word = w.word.strip()
                    if cleaned_word:
                        words.append({
                            "word": cleaned_word,
                            "start": round(w.start, 3),
                            "end": round(w.end, 3)
                        })
        return words
    except Exception as e:
        # Fallback estimation if faster-whisper fails
        return []


def align_words_with_script(script_text: str, whisper_words: List[Dict], total_duration_s: float) -> List[Dict]:
    """
    Aligns exact script words with detected timestamps using SequenceMatcher.
    If no whisper timestamps, performs high-precision uniform distribution.
    """
    clean_script = sanitize_reference_script(script_text)
    raw_words = clean_script.split()
    
    if not raw_words:
        return whisper_words

    if not whisper_words:
        # Uniform fallback distribution
        dur_per_word = max(0.2, (total_duration_s / len(raw_words)) if total_duration_s > 0 else 0.35)
        aligned = []
        cur = 0.0
        for w in raw_words:
            aligned.append({
                "word": w,
                "start": round(cur, 3),
                "end": round(cur + dur_per_word, 3)
            })
            cur += dur_per_word
        return aligned

    ref_clean = [re.sub(r'[^\w]', '', w.lower()) for w in raw_words]
    w_clean = [re.sub(r'[^\w]', '', item["word"].lower()) for item in whisper_words]

    sm = difflib.SequenceMatcher(None, ref_clean, w_clean)
    opcodes = sm.get_opcodes()

    aligned_words = [{"word": rw, "start": None, "end": None} for rw in raw_words]

    for tag, i1, i2, j1, j2 in opcodes:
        if tag in ("equal", "replace"):
            for ref_i, w_j in zip(range(i1, i2), range(j1, j2)):
                if ref_i < len(aligned_words) and w_j < len(whisper_words):
                    w_item = whisper_words[w_j]
                    aligned_words[ref_i]["start"] = w_item["start"]
                    aligned_words[ref_i]["end"] = w_item["end"]

    # Fill missing gaps
    prev_end = 0.0
    for i, item in enumerate(aligned_words):
        if item["start"] is None:
            next_start = None
            for k in range(i + 1, len(aligned_words)):
                if aligned_words[k]["start"] is not None:
                    next_start = aligned_words[k]["start"]
                    break
            if next_start is None:
                next_start = prev_end + 0.3
            item["start"] = round(prev_end, 3)
            item["end"] = round(min(next_start, prev_end + 0.3), 3)
        else:
            if item["start"] < prev_end:
                item["start"] = prev_end
            if item["end"] <= item["start"]:
                item["end"] = round(item["start"] + 0.15, 3)
        prev_end = item["end"]

    return aligned_words


def chunk_words_to_raw_srt(words: List[Dict], max_words: int = 4, gap_buffer: float = 0.05) -> str:
    """
    Chunks words into <= max_words lines and creates standard SRT format.
    """
    if not words:
        return ""

    blocks = []
    curr = []
    for w in words:
        curr.append(w)
        if len(curr) >= max_words:
            blocks.append(curr)
            curr = []
    if curr:
        blocks.append(curr)

    srt_lines = []
    for idx, b in enumerate(blocks, 1):
        st = format_srt_timestamp(b[0]["start"])
        et = format_srt_timestamp(b[-1]["end"])
        txt = " ".join([w["word"] for w in b])
        srt_lines.append(f"{idx}\n{st} --> {et}\n{txt}\n")

    return "\n".join(srt_lines)
