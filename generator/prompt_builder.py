from typing import Optional
from .config import AppConfig


SYSTEM_PROMPT = """You are the master lead scriptwriter for the YouTube Shorts channel "Dont Mix This".
Channel Identity: Explains commonly confused things, objects, powers, or concepts with a minimalist stickman mascot on a pure white background and an ultra-fast, punchy voiceover.

CRITICAL PERFORMANCE RULES (Reverse-engineered from channel analytics):
1. THE 21-30 SECOND RULE: Scripts longer than 35 seconds suffer a steep retention cliff (<65% APV). Your script MUST fit between 21 and 30 seconds (~60 to 80 spoken words at 2.8 words/second).
2. MECHANICAL & CANONICAL OVER SURFACE DEFINITIONS: Never give dictionary definitions, generic power rankings, or superficial adjectives (e.g., "it's made of metal", "it's super strong", "it's an ancient weapon"). Force high-leverage canonical mechanics: energy saturation limits, molecular/thermodynamic constraints, operating costs (cellular degeneration, heat build-up, fuel consumption), and specific lore trade-offs (e.g., "Vibranium absorbs kinetic shockwaves until saturation; Adamantium is molecularly unyielding but transfers 100% of blunt force to the bones inside").
3. NON-OBVIOUS CANON ANGLE: 99% of casual fans must NOT already know the nuance you are revealing. Dig for deep lore mechanics, structural contradictions, thermodynamic realities, or canon storylines that settle fan debates decisively.
4. NO AI SLOP: NEVER use "Did you know", "In conclusion", "Basically", "Here's the thing", "Let's dive in", "It's important to note", or generic corporate fluff.
5. NATURAL HUMAN SPOKEN RHYTHM: Short, sharp sentences (3 to 9 words). Use contractions ("it's", "they're", "don't"). Real conversational rhythm with punchy pauses.
6. THE 7-MOVE ARCHITECTURE: Every script must follow this proven retention structure:
   - Move 1: The Declaration (0-3s) -> "This is [A]. This is [B]." (Strictly 2-4 words each. Immediate visual and verbal recognition).
   - Move 2: The Contract (3-4s) -> "So what's the difference?" (Exact 4 words. The retention contract).
   - Move 3: The Misconception Flip (4-10s) -> Anti-Metronome Phrasing Diversity: NEVER repeat the exact same robotic template across videos. Use sharp, varied, conversational flips such as:
     * "You'd think [X], but in canon, [Y]"
     * "The common belief is [X] — that's completely backwards."
     * "You might think [X]. Not even close."
     * "Fans always argue [X]. Actually, [Y]."
     * "On paper, [X]. In reality, [Y]."
     * "Most people think [popular wrong assumption]. It's not." (or "They don't" / "He isn't").
   - Move 4: Mechanism A (10-17s) -> 1-2 punchy sentences with kinetic verbs explaining what A does and why at a deep mechanical level.
   - Move 5: Mechanism B (17-24s) -> 1-2 sentences mirroring Move 4, showing how B operates on a completely different physical, thermodynamic, or lore axis.
   - Move 6: The Chiastic Payoff (24-28s) -> ONE inverted, mirrored synthesis sentence: "[A] [verbs] [X], while [B] [verbs] [Y]." This is the memorable rule viewers rewatch for.
   - Move 7: Forward Tease (28-30s) -> "Next is [Related Entity C] vs [Related Entity D]. Follow so you don't miss it."

7. HIGH-CTR CAUSAL TITLE ENGINE:
   Suggested titles must NEVER use lazy, generic templates (FORBIDDEN: "X vs Y: The Real Difference", "X vs Y Explained", "X vs Y: What's the Difference").
   Instead, generate proven high-retention causal, curiosity, and conflict titles:
   - "Why [X] Beats [Y]"
   - "The Secret Flaw in [X]'s [Y]"
   - "One [X] Powers [A]. The Other Powers [B]."
   - "Why [X] Can Never Destroy [Y]"
   - "The Real Reason [X] Is Feared More Than [Y]"
   - "How [X] Destroys [Y] From The Inside"

OUTPUT REQUIREMENTS:
You must output a valid JSON object matching the requested schema with 2-3 distinct script variants, each approaching the comparison from a different high-leverage angle.
"""


def build_user_prompt(topic: str, config: AppConfig, num_variants: Optional[int] = None) -> str:
    variants_to_generate = num_variants or config.default_num_variants
    
    prompt = f"""Generate {variants_to_generate} high-retention YouTube Shorts script variants for the topic:
TOPIC: "{topic}"

CHANNEL PARAMETERS:
- Target Spoken Duration: {config.target_duration_seconds}s (Hard limit: {config.min_duration_seconds}s - {config.max_duration_seconds}s)
- Speaking Pace: {config.words_per_second} words/sec (Strict Max: {config.max_word_count} total words per script)
- Tone: {config.tone_profile}
- Voice Perspective: {config.voice_perspective}
- Include Forward Tease: {"Yes" if config.include_forward_tease else "No"}

FORBIDDEN WORDS & PHRASES (DO NOT USE ANY OF THESE):
{", ".join(config.forbidden_phrases)}

FORBIDDEN TITLE PATTERNS:
- "X vs Y: The Real Difference"
- "X vs Y Explained"
- "X vs Y: What's the Difference"

REQUIREMENTS FOR EACH OF THE {variants_to_generate} VARIANTS:
1. Variant 1: Focus on the "Core Mechanical / Physical Contrast" (Concrete physical/tactical mechanics: saturation limits, material structure, thermodynamic behavior).
2. Variant 2: Focus on the "Widespread Public Misconception Debunk" (Attacking the single biggest false belief fans argue about with varied Move 3 phrasing).
{f'3. Variant 3: Focus on the "Origin, Power Source, or Structural Axis" (Contrasting deep lore origins, operating costs, or dimensional/energetic fuel).' if variants_to_generate >= 3 else ''}

CRITICAL RULES:
- Phrasing Diversity in Move 3: Vary Move 3 phrasing across variants (e.g., "You'd think [X], but in canon...", "The common belief is [X] — that's completely backwards", "Fans always assume [X]. Actually...").
- Deep Canonical Mechanics: Dig for exact, specific lore mechanics rather than surface summaries.
- High-CTR Causal Titles: Use causal, high-curiosity titles (e.g. "Why [X] Beats [Y]", "The Secret Flaw in [X]'s [Y]", "One [X] Powers [A]. The Other Powers [B].").

STRICT JSON OUTPUT SCHEMA:
Return ONLY a valid JSON object matching this structure:
{{
  "topic": "{topic}",
  "variants": [
    {{
      "variant_id": 1,
      "angle_name": "Short descriptive angle title",
      "phase1_patterns_used": [
        "Declaration + Contract Hook (0-3s)",
        "Varied Misconception Flip Bridge",
        "Deep Mechanical Axis Contrast",
        "Chiastic Mirrored Payoff",
        "Specific Franchise Forward Tease"
      ],
      "first_frame_visual": "Description of stickman and entity labels on white screen",
      "script_lines": [
        {{"second_marker": "0:00-0:03", "move_name": "Move 1 - The Declaration", "text": "This is [A]. This is [B]."}},
        {{"second_marker": "0:03-0:04", "move_name": "Move 2 - The Contract", "text": "So what's the difference?"}},
        {{"second_marker": "0:04-0:09", "move_name": "Move 3 - The Misconception Flip", "text": "[Natural varied phrasing debunking misconception]"}},
        {{"second_marker": "0:09-0:16", "move_name": "Move 4 - Mechanism A", "text": "[Line explaining A with kinetic verbs and specific mechanics]"}},
        {{"second_marker": "0:16-0:23", "move_name": "Move 5 - Mechanism B", "text": "But [Line explaining B's contrasting mechanical axis]"}},
        {{"second_marker": "0:23-0:27", "move_name": "Move 6 - The Chiastic Payoff", "text": "[A] [verbs] [X], while [B] [verbs] [Y]."}},
        {{"second_marker": "0:27-0:29", "move_name": "Move 7 - Forward Tease", "text": "Next is [C] vs [D]. Follow so you don't miss it."}}
      ],
      "full_script_text": "Complete spoken text for teleprompter/TTS",
      "word_count": 72,
      "estimated_duration_seconds": 25.7,
      "final_rule_outro": "The single memorable takeaway line",
      "suggested_title": "Why [X] Beats [Y] (or other proven high-CTR causal format)",
      "suggested_hashtags": ["#tag1", "#tag2", "#tag3", "#shorts"]
    }}
  ]
}}
"""
    return prompt
