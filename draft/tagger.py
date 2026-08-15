"""
Mascot Pose Tagger & Semantic Subtitle Chunking Engine
Enforces persistent entity-to-side mapping (X -> left.png, Y -> right.png),
sentence-level semantic context inheritance, meaning-preserving chunking (max 3 words),
and per-block audit logging.
"""

import re
import os
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

MAX_WORDS_PER_CHUNK = 3

TAG_RE = re.compile(r"\[IMG:[^\]]+\]")

# Punctuation marks for boundary detection
_CLAUSE_PUNCT = {",", ";", ":", "-", "—"}
_SENTENCE_PUNCT = {".", "!", "?"}

# Conjunctions / switchers where a new clause / subject starts
_SWITCH_CONJUNCTIONS = {
    "while", "whereas", "but", "however", "unlike", "instead", "although"
}

_STOP_WORDS = {
    "this", "that", "these", "those", "there", "their", "they", "them",
    "is", "are", "was", "were", "be", "been", "being",
    "the", "a", "an", "and", "or", "if", "because", "as", "until",
    "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
    "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "just", "only", "both", "all", "what", "whats", "most", "people", "think", "its"
}


@dataclass
class TaggedSubtitle:
    index: int
    start_ms: int
    end_ms: int
    start_us: int
    end_us: int
    duration_us: int
    text: str
    tag: str
    pose: str
    rule_name: str
    reason: str
    is_emphasis: bool = False


def _clean_token(w: str) -> str:
    """Normalize a word token for matching."""
    w = w.lower().strip(".,!?;:'\"-—()[]{}")
    if w.endswith("'s"):
        w = w[:-2]
    return w


def extract_distinctive_entity_keywords(concept_x: str, concept_y: str) -> Tuple[Set[str], Set[str]]:
    """
    Extracts distinctive keywords for X and Y, removing stopwords and common overlap
    (e.g., 'suit' in 'Nanotech Suit' vs 'Vibranium Suit').
    """
    toks_x = {_clean_token(t) for t in (concept_x or "").lower().split() if len(_clean_token(t)) > 1 and _clean_token(t) not in _STOP_WORDS}
    toks_y = {_clean_token(t) for t in (concept_y or "").lower().split() if len(_clean_token(t)) > 1 and _clean_token(t) not in _STOP_WORDS}

    common = toks_x & toks_y
    distinct_x = (toks_x - common) if (toks_x - common) else toks_x
    distinct_y = (toks_y - common) if (toks_y - common) else toks_y

    return distinct_x, distinct_y


def split_text_into_sentences_and_clauses(words: List[Dict], x_tokens: Set[str], y_tokens: Set[str]) -> List[List[Dict]]:
    """
    Groups words into coherent clauses/sentences first, so each clause carries a unified topic.
    Splits when:
    - Sentence end punctuation (. ? !)
    - Clause punctuation (, ; : —) followed by a transition/conjunction
    - Explicit subject switch (e.g. 'while Vibranium')
    - 'This is' introducing a new entity
    - 'So what's the difference'
    """
    if not words:
        return []

    clauses: List[List[Dict]] = []
    current_clause: List[Dict] = []
    current_subject: Optional[str] = None

    for i, w_dict in enumerate(words):
        raw_word = w_dict["word"]
        clean_w = _clean_token(raw_word)
        lower_w = raw_word.lower().strip()

        # Lookahead: is this a 'This is' intro for X or Y?
        is_intro = lower_w == "this" and i + 1 < len(words) and words[i + 1]["word"].lower().startswith("is")
        
        # Lookahead: is this 'So what's the difference'?
        is_wtd = (lower_w == "so" and i + 1 < len(words) and "what" in words[i + 1]["word"].lower()) or ("difference" in lower_w)

        # Lookahead: is this 'while / but [Entity]'?
        is_switch_conj = lower_w in _SWITCH_CONJUNCTIONS

        word_subject = None
        if clean_w in x_tokens:
            word_subject = "x"
        elif clean_w in y_tokens:
            word_subject = "y"

        should_split = False

        # If previous word ended with sentence punctuation
        if current_clause and current_clause[-1]["word"] and current_clause[-1]["word"][-1] in _SENTENCE_PUNCT:
            should_split = True

        # If we encounter a new 'This is' or 'So what's'
        elif (is_intro or is_wtd) and len(current_clause) > 0:
            should_split = True

        # If we encounter a switch conjunction (e.g. 'while') with preceding clause ending in punctuation or having >= 2 words
        elif is_switch_conj and len(current_clause) >= 2:
            should_split = True

        # If subject changes mid-sentence (e.g. from X to Y)
        elif word_subject and current_subject and word_subject != current_subject and len(current_clause) >= 2:
            should_split = True

        if should_split and current_clause:
            clauses.append(current_clause)
            current_clause = []
            current_subject = None

        current_clause.append(w_dict)
        if word_subject:
            current_subject = word_subject

    if current_clause:
        clauses.append(current_clause)

    return clauses


def chunk_clause_into_max_3_words(clause_words: List[Dict]) -> List[List[Dict]]:
    """
    Splits a clause into balanced chunks of MAXIMUM 3 words (<= 3 words).
    Ensures natural phrasing without dangling 1-word orphans.
    """
    n = len(clause_words)
    if n <= MAX_WORDS_PER_CHUNK:
        return [clause_words]

    if n == 4:
        return [clause_words[:2], clause_words[2:]]
    elif n == 5:
        # e.g. "This is a Nanotech suit." -> "This is a" (3) + "Nanotech suit." (2)
        return [clause_words[:3], clause_words[3:]]
    elif n == 6:
        return [clause_words[:3], clause_words[3:]]

    # For n > 6, split greedily into 2-3 word chunks avoiding orphans
    chunks = []
    rem = list(clause_words)
    while len(rem) > MAX_WORDS_PER_CHUNK:
        cut = MAX_WORDS_PER_CHUNK
        if len(rem) - cut == 1:
            cut = 2
        chunks.append(rem[:cut])
        rem = rem[cut:]
    if rem:
        chunks.append(rem)

    return chunks


def determine_clause_role(
    clause_text: str,
    x_tokens: Set[str],
    y_tokens: Set[str],
    position: float
) -> Tuple[str, str, str]:
    """
    Determines the unified topic and mascot pose for an entire clause/sentence.
    """
    low = clause_text.lower().strip()
    words = low.split()
    tokens = {_clean_token(w) for w in words}

    has_x = bool(tokens & x_tokens) or any(tok in low for tok in x_tokens if len(tok) >= 3)
    has_y = bool(tokens & y_tokens) or any(tok in low for tok in y_tokens if len(tok) >= 3)

    # 1. Outro / Call to Action / Forward Tease (Position >= 75%)
    if position >= 0.75 and any(kw in low for kw in ["follow", "subscribe", "next is", "don't miss", "comment", "for more", "vs"]):
        return "final_end", "Rule: Outro / CTA", f"Outro/CTA in '{clause_text}' -> final_end.png"

    # 2. Core Question (WTD)
    if "difference" in low or "what's the difference" in low or "so what's the" in low or ("?" in clause_text and position < 0.35):
        return "wtd", "Rule: Core Question (WTD)", f"Question/contrast in '{clause_text}' -> wtd.png"

    # 3. Misconception / Negation Flip
    if any(neg in low for neg in ["most people think", "they're not", "they are not", "they don't", "that's wrong", "that is wrong", "incorrect", "armors"]):
        return "disagree", "Rule: Misconception Flip", f"Misconception/negation in '{clause_text}' -> disagree.png"

    # 4. Explicit Intro or Primary Discussion of Entity X
    if has_x and not has_y:
        return "left", "Rule: Entity X Discussion", f"Discussing Entity X in '{clause_text}' -> left.png"

    # 5. Explicit Intro or Primary Discussion of Entity Y
    if has_y and not has_x:
        return "right", "Rule: Entity Y Discussion", f"Discussing Entity Y in '{clause_text}' -> right.png"

    # 6. Shock / High Intensity
    if any(sw in low for sw in ["shockwave", "insane", "wild", "massive", "shreds", "billion"]):
        return "shocked", "Rule: Shock / High Intensity", f"Intensity trigger in '{clause_text}' -> shocked.png"

    # 7. Takeaway / Final Rule Payoff (Position >= 65%)
    if position >= 0.65 and any(rw in low for rw in ["burns", "absorbs", "demands", "worthy", "rule", "remember"]):
        if has_x and not has_y:
            return "left", "Rule: Entity X Payoff", f"Entity X payoff in '{clause_text}' -> left.png"
        if has_y and not has_x:
            return "right", "Rule: Entity Y Payoff", f"Entity Y payoff in '{clause_text}' -> right.png"
        return "remember_this", "Rule: Takeaway Rule", f"Core rule takeaway in '{clause_text}' -> remember_this.png"

    # 8. Analytical Mechanism
    if any(tw in low for tw in ["because", "since", "inside", "channels", "forged", "damaged"]):
        return "thinking", "Rule: Mechanism Explanation", f"Explaining mechanism in '{clause_text}' -> thinking.png"

    return "left", "Rule: Neutral Context", f"Neutral context for '{clause_text}'"


def build_semantic_tagged_subtitles(
    aligned_words: List[Dict],
    concept_x: str,
    concept_y: str
) -> Tuple[List[TaggedSubtitle], List[str]]:
    """
    Main pipeline:
    1. Splits word stream into semantic sentences/clauses.
    2. Determines clause-level role and pose (guaranteeing X -> left, Y -> right, WTD -> wtd).
    3. Chunks clauses into units of max 3 words inheriting the clause role.
    4. Runs self-check pass to guarantee zero violations.
    5. Formats detailed audit log.
    """
    if not aligned_words:
        return [], []

    x_tokens, y_tokens = extract_distinctive_entity_keywords(concept_x, concept_y)

    # 1. Split into coherent clauses
    clauses = split_text_into_sentences_and_clauses(aligned_words, x_tokens, y_tokens)
    total_clauses = len(clauses)

    clause_data = []
    prev_pose = "left"

    for c_idx, c_words in enumerate(clauses, 1):
        clause_text = " ".join(w["word"] for w in c_words).strip()
        pos = c_idx / total_clauses

        pose, rule_name, reason = determine_clause_role(
            clause_text=clause_text,
            x_tokens=x_tokens,
            y_tokens=y_tokens,
            position=pos
        )

        # Stance continuity fallback
        if rule_name.startswith("Rule: Neutral Context"):
            if prev_pose in {"left", "right"}:
                pose = prev_pose
                rule_name = f"Rule: Stance Continuity ({prev_pose})"
                reason = f"Continuing active explanation stance ({prev_pose})"

        prev_pose = pose
        clause_data.append({
            "words": c_words,
            "text": clause_text,
            "pose": pose,
            "rule_name": rule_name,
            "reason": reason
        })

    # 2. Sub-chunk each clause into <= 3 words inheriting clause role & pose
    tagged_subtitles: List[TaggedSubtitle] = []
    audit_logs: List[str] = []
    chunk_index = 1

    for c_info in clause_data:
        sub_chunks = chunk_clause_into_max_3_words(c_info["words"])
        c_pose = c_info["pose"]
        c_rule = c_info["rule_name"]
        c_reason = c_info["reason"]

        for chunk in sub_chunks:
            chunk_text = " ".join(w["word"] for w in chunk).strip()
            st_s = chunk[0]["start"]
            et_s = chunk[-1]["end"]

            # Per-chunk self-check:
            # Check if this specific chunk contains distinct X or Y directly
            ch_low = chunk_text.lower()
            ch_toks = {_clean_token(w) for w in ch_low.split()}
            ch_has_x = bool(ch_toks & x_tokens) or any(t in ch_low for t in x_tokens if len(t) >= 3)
            ch_has_y = bool(ch_toks & y_tokens) or any(t in ch_low for t in y_tokens if len(t) >= 3)

            chunk_pose = c_pose
            chunk_rule = c_rule
            chunk_reason = c_reason

            if ch_has_x and not ch_has_y:
                chunk_pose = "left"
                chunk_rule = "Rule: Entity X Discussion"
                chunk_reason = f"Entity X ('{concept_x}') -> left.png"
            elif ch_has_y and not ch_has_x:
                chunk_pose = "right"
                chunk_rule = "Rule: Entity Y Discussion"
                chunk_reason = f"Entity Y ('{concept_y}') -> right.png"

            # Strict self-check enforcement (X is never right.png, Y is never left.png):
            if ch_has_x and not ch_has_y and chunk_pose == "right":
                chunk_pose = "left"
                chunk_rule = "Rule: Self-Check Auto-Correction (X -> left)"
                chunk_reason = f"[AUDIT CORRECTION] Entity X was mapped to right.png! Fixed to left.png."
            elif ch_has_y and not ch_has_x and chunk_pose == "left":
                chunk_pose = "right"
                chunk_rule = "Rule: Self-Check Auto-Correction (Y -> right)"
                chunk_reason = f"[AUDIT CORRECTION] Entity Y was mapped to left.png! Fixed to right.png."

            st_us = int(round(st_s * 1_000_000))
            et_us = int(round(et_s * 1_000_000))
            dur_us = max(100_000, et_us - st_us)

            is_emp = "?" in chunk_text or any(kw in chunk_text.lower() for kw in ["difference", "wrong", "remember", "winner", "burst", "absorbs"])

            tagged_sub = TaggedSubtitle(
                index=chunk_index,
                start_ms=int(round(st_s * 1000)),
                end_ms=int(round(et_s * 1000)),
                start_us=st_us,
                end_us=et_us,
                duration_us=dur_us,
                text=chunk_text,
                tag=f"[IMG:{chunk_pose}]",
                pose=chunk_pose,
                rule_name=chunk_rule,
                reason=chunk_reason,
                is_emphasis=is_emp
            )
            tagged_subtitles.append(tagged_sub)

            log_entry = (
                f"[Block {chunk_index:02d}] ({st_s:5.2f}s - {et_s:5.2f}s) "
                f"\"{chunk_text:<26}\" -> {chunk_rule:<36} -> {chunk_pose}.png ({chunk_reason})"
            )
            audit_logs.append(log_entry)
            chunk_index += 1

    return tagged_subtitles, audit_logs


def generate_tagged_subtitles(
    raw_srt: str,
    concept_x: str = "",
    concept_y: str = "",
    max_words: int = 3
) -> List[TaggedSubtitle]:
    """
    Backwards compatibility helper.
    """
    from draft.stt import parse_srt_timestamp
    blocks = re.split(r"\n\s*\n", raw_srt.strip().replace("\r\n", "\n"))
    words: List[Dict] = []
    for b in blocks:
        lines = [l.strip() for l in b.strip().splitlines() if l.strip()]
        if len(lines) < 3 or not lines[0].isdigit():
            continue
        m = re.match(r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})", lines[1])
        if not m:
            continue
        st_s = parse_srt_timestamp(m.group(1))
        et_s = parse_srt_timestamp(m.group(2))
        clean_text = TAG_RE.sub("", " ".join(lines[2:])).strip()
        b_words = clean_text.split()
        if not b_words:
            continue
        dur_w = (et_s - st_s) / len(b_words)
        cur = st_s
        for w in b_words:
            words.append({"word": w, "start": round(cur, 3), "end": round(cur + dur_w, 3)})
            cur += dur_w

    tagged, _ = build_semantic_tagged_subtitles(words, concept_x, concept_y)
    return tagged
