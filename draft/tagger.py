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
    Activates all 13 mascot poses based on semantic meaning and narrative phase.
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
    misconception_cues = [
        "most people think", "they're not", "they are not", "they don't", "that's wrong",
        "that is wrong", "it's not", "it is not", "incorrect", "wrong", "backwards",
        "you'd think", "you would think", "common belief", "not even close",
        "fans assume", "in canon", "in reality", "myth is", "actually false",
        "on paper", "not the case", "not quite", "doesn't work", "he isn't",
        "she isn't", "they aren't"
    ]
    if any(neg in low for neg in misconception_cues):
        return "disagree", "Rule: Misconception Flip", f"Misconception/negation in '{clause_text}' -> disagree.png"

    # 4. Victorious / Definitive Dominance
    if any(vw in low for vw in ["beats", "wins", "dominates", "crushes", "superior", "destroy", "overwhelms", "victorious", "take down"]):
        return "victorious", "Rule: Definitive Dominance", f"Dominance/winner trigger in '{clause_text}' -> victorious.png"

    # 5. Smug / Unyielding Durability & Superior Specs (Entity X / Left oriented)
    if any(sw in low for sw in ["never bends", "pure, rigid", "rigid hardness", "indestructible", "invincible", "unbreakable", "can't pierce", "flawless", "effortless", "immune", "pure hardness", "shrugs off"]):
        return "smug", "Rule: Smug Superiority", f"Durability/superior specs in '{clause_text}' -> smug.png"

    # 6. Shock / High Intensity Destructive Power
    if any(sw in low for sw in ["shockwave", "insane", "wild", "massive", "shreds", "billion", "overheats", "explodes", "shatters", "blasts", "nullifying"]):
        return "shocked", "Rule: Shock / High Intensity", f"Intensity trigger in '{clause_text}' -> shocked.png"

    # 7. Dual-Entity Contrast / Weighing Trade-Offs
    if any(cw in low for cw in ["while", "whereas", "both", "instead", "unlike", "contrast", "trade-off", "trade off"]):
        return "twohandsopen", "Rule: Dual-Entity Contrast", f"Contrast/trade-off in '{clause_text}' -> twohandsopen.png"

    # 8. Takeaway / Final Rule Payoff (Position >= 65%)
    if position >= 0.65 and any(rw in low for rw in ["burns", "absorbs", "demands", "worthy", "rule", "remember", "takeaway", "key is", "comes down to"]):
        return "remember_this", "Rule: Takeaway Rule", f"Core rule takeaway in '{clause_text}' -> remember_this.png"

    # 9. Explicit Intro or Primary Discussion of Entity X
    if has_x and not has_y:
        return "left", "Rule: Entity X Discussion", f"Discussing Entity X in '{clause_text}' -> left.png"

    # 10. Explicit Intro or Primary Discussion of Entity Y
    if has_y and not has_x:
        return "right", "Rule: Entity Y Discussion", f"Discussing Entity Y in '{clause_text}' -> right.png"

    # 11. In-depth Material Property Analysis (Left-oriented)
    if any(pw in low for pw in ["alloy", "kinetic", "density", "stores", "absorbing", "absorbs", "properties", "extraterrestrial"]):
        return "profile", "Rule: Material Property Analysis", f"Material property analysis in '{clause_text}' -> profile.png"

    # 12. Analytical Inner Mechanism
    if any(tw in low for tw in ["because", "since", "inside", "channels", "engineered", "micro-bots", "atomic", "molecular", "restructures", "transforms", "converts", "housing pod"]):
        return "thinking", "Rule: Mechanism Explanation", f"Explaining mechanism in '{clause_text}' -> thinking.png"

    # 13. Opening Frame / Baseline Neutral Stance
    if position <= 0.15:
        return "normal", "Rule: Baseline Opening", f"Opening neutral stance for '{clause_text}' -> normal.png"

    return "left", "Rule: Neutral Context", f"Neutral context for '{clause_text}'"


def build_semantic_tagged_subtitles(
    aligned_words: List[Dict],
    concept_x: str,
    concept_y: str
) -> Tuple[List[TaggedSubtitle], List[str]]:
    """
    Main pipeline:
    1. Splits word stream into semantic sentences/clauses.
    2. Determines clause-level role and pose (activating all 13 poses).
    3. Chunks clauses into units of max 3 words inheriting the clause role.
    4. Enforces strict entity orientation (Entity X -> left/smug/thinking, Entity Y -> strictly right).
    5. Runs self-check pass to guarantee entity mapping integrity.
    6. Formats detailed audit log.
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
            if prev_pose in {"left", "right", "thinking", "profile", "smug"}:
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
    raw_sub_chunks = []

    for c_info in clause_data:
        sub_chunks = chunk_clause_into_max_3_words(c_info["words"])
        c_pose = c_info["pose"]
        c_rule = c_info["rule_name"]
        c_reason = c_info["reason"]

        for chunk in sub_chunks:
            chunk_text = " ".join(w["word"] for w in chunk).strip()
            st_s = chunk[0]["start"]
            et_s = chunk[-1]["end"]

            ch_low = chunk_text.lower()
            ch_toks = {_clean_token(w) for w in ch_low.split()}
            ch_has_x = bool(ch_toks & x_tokens) or any(t in ch_low for t in x_tokens if len(t) >= 3)
            ch_has_y = bool(ch_toks & y_tokens) or any(t in ch_low for t in y_tokens if len(t) >= 3)

            chunk_pose = c_pose
            chunk_rule = c_rule
            chunk_reason = c_reason

            # If clause is Entity Y (or discussing Y), NEVER override with left-pointing poses
            is_y_context = c_pose == "right" or "entity y" in c_rule.lower() or ch_has_y

            if is_y_context:
                if any(hw in ch_low for hw in ["shockwave", "insane", "massive", "shatters", "bursts", "explodes"]):
                    chunk_pose = "shocked"
                    chunk_rule = "Rule: Micro High Intensity (Y)"
                    chunk_reason = f"Intensity keywords in '{chunk_text}' -> shocked.png"
                elif any(tw in ch_low for tw in ["while", "whereas", "both", "instead"]):
                    chunk_pose = "twohandsopen"
                    chunk_rule = "Rule: Micro Contrast"
                    chunk_reason = f"Contrast keyword in '{chunk_text}' -> twohandsopen.png"
                else:
                    # Keep pointing firmly right at Entity Y
                    chunk_pose = "right"
                    chunk_rule = "Rule: Entity Y Discussion"
                    chunk_reason = f"Entity Y ('{concept_y}') -> right.png"
            else:
                # Entity X / General context: can use left-oriented expressive gestures
                if any(sw in ch_low for sw in ["never bends", "pure, rigid", "indestructible", "invincible", "pure hardness", "shrugs off"]):
                    chunk_pose = "smug"
                    chunk_rule = "Rule: Micro Smug Superiority"
                    chunk_reason = f"Durability keywords in '{chunk_text}' -> smug.png"
                elif any(hw in ch_low for hw in ["shockwave", "insane", "massive", "shatters", "bursts", "explodes"]):
                    chunk_pose = "shocked"
                    chunk_rule = "Rule: Micro High Intensity"
                    chunk_reason = f"Intensity keywords in '{chunk_text}' -> shocked.png"
                elif any(tw in ch_low for tw in ["while", "whereas", "both", "instead"]):
                    chunk_pose = "twohandsopen"
                    chunk_rule = "Rule: Micro Contrast"
                    chunk_reason = f"Contrast keyword in '{chunk_text}' -> twohandsopen.png"
                elif any(mw in ch_low for mw in ["engineered", "atomic", "molecular", "micro-bots", "channels", "because"]):
                    chunk_pose = "thinking"
                    chunk_rule = "Rule: Micro Mechanism Explanation"
                    chunk_reason = f"Technical mechanics in '{chunk_text}' -> thinking.png"
                elif any(pw in ch_low for pw in ["absorbs", "stores", "alloy", "density", "properties"]):
                    chunk_pose = "profile"
                    chunk_rule = "Rule: Micro Material Property"
                    chunk_reason = f"Material property in '{chunk_text}' -> profile.png"
                elif any(vw in ch_low for vw in ["beats", "wins", "dominates", "crushes", "superior"]):
                    chunk_pose = "victorious"
                    chunk_rule = "Rule: Micro Dominance"
                    chunk_reason = f"Dominance keyword in '{chunk_text}' -> victorious.png"

            # Strict entity anchor override (Naming X is ALWAYS left, Naming Y is ALWAYS right)
            if ch_has_x and not ch_has_y:
                chunk_pose = "left"
                chunk_rule = "Rule: Entity X Discussion"
                chunk_reason = f"Entity X ('{concept_x}') -> left.png"
            elif ch_has_y and not ch_has_x:
                chunk_pose = "right"
                chunk_rule = "Rule: Entity Y Discussion"
                chunk_reason = f"Entity Y ('{concept_y}') -> right.png"

            raw_sub_chunks.append({
                "chunk": chunk,
                "text": chunk_text,
                "st_s": st_s,
                "et_s": et_s,
                "pose": chunk_pose,
                "rule": chunk_rule,
                "reason": chunk_reason,
                "has_x": ch_has_x,
                "has_y": ch_has_y
            })

    # 3. Maximum Pose Hold Limit Pass (<= 3.5 seconds) for Entity X
    # For Entity X, shift intermediate chunks to thinking/smug to break long holds
    # For Entity Y, keep firmly right.png so it always points at Entity Y (top-right)
    MAX_POSE_HOLD_S = 3.5
    i = 0
    while i < len(raw_sub_chunks):
        curr_pose = raw_sub_chunks[i]["pose"]
        run_end = i
        while run_end + 1 < len(raw_sub_chunks) and raw_sub_chunks[run_end + 1]["pose"] == curr_pose:
            run_end += 1

        run_dur = raw_sub_chunks[run_end]["et_s"] - raw_sub_chunks[i]["st_s"]
        if run_dur > MAX_POSE_HOLD_S and (run_end - i) >= 2:
            if curr_pose == "left":
                for mid_idx in range(i + 1, run_end):
                    if not raw_sub_chunks[mid_idx]["has_x"] and not raw_sub_chunks[mid_idx]["has_y"]:
                        raw_sub_chunks[mid_idx]["pose"] = "thinking"
                        raw_sub_chunks[mid_idx]["rule"] = "Rule: Dynamic Freeze Breaker (thinking)"
                        raw_sub_chunks[mid_idx]["reason"] = "Broke >3.5s static pose with analytical thinking gesture"

        i = run_end + 1

    # 4. Final Assembly & Audit Logging
    tagged_subtitles: List[TaggedSubtitle] = []
    audit_logs: List[str] = []

    for chunk_index, item in enumerate(raw_sub_chunks, 1):
        chunk_text = item["text"]
        st_s = item["st_s"]
        et_s = item["et_s"]
        chunk_pose = item["pose"]
        chunk_rule = item["rule"]
        chunk_reason = item["reason"]

        # Final audit correction check
        if item["has_x"] and not item["has_y"] and chunk_pose == "right":
            chunk_pose = "left"
            chunk_rule = "Rule: Self-Check Auto-Correction (X -> left)"
            chunk_reason = f"[AUDIT CORRECTION] Entity X was mapped to right.png! Fixed to left.png."
        elif item["has_y"] and not item["has_x"] and chunk_pose == "left":
            chunk_pose = "right"
            chunk_rule = "Rule: Self-Check Auto-Correction (Y -> right)"
            chunk_reason = f"[AUDIT CORRECTION] Entity Y was mapped to left.png! Fixed to right.png."

        st_us = int(round(st_s * 1_000_000))
        et_us = int(round(et_s * 1_000_000))
        dur_us = max(100_000, et_us - st_us)

        is_emp = "?" in chunk_text or any(kw in chunk_text.lower() for kw in ["difference", "wrong", "remember", "winner", "burst", "absorbs", "shatters", "beats"])

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
