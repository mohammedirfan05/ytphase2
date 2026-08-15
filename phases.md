# "Dont Mix This" — Optimization Roadmap (Phases 1–4)

A structured, 4-phase implementation roadmap designed to eliminate visual and auditory drop-offs, deepen script retention, and trigger algorithmic recommendation loops.

---

## Overview of Phases

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Audio Design & Sound Effects Layer (Immediate Retention Boost)     │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Visual Dynamics & Complete Mascot Activation (Visual Velocity)    │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Script Generator Intelligence & Title Engine (Hook & Lore Depth)  │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Cluster Engine & Topic Guardrails (Algorithmic Recommendation)    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Audio Design & Sound Effects Layer
**Goal:** Eliminate the 20-second audio dead zone between seconds 4 and 26 to maximize watch time and pacing.

* **1.1 Background Music (BGM) Track Integration**
  * Add a dedicated, looping background music audio track in `draft/builder.py`.
  * Set default volume to subtle background level (~ -18dB to -22dB) so voiceover remains crisp and dominant.
  * Store curated royalty-free tracks (upbeat lo-fi / hip-hop groove / suspense) in `assets/audio/bgm/`.

* **1.2 Mid-Video & Payoff SFX Expansion**
  * Expand `assets/sound_effects/` beyond the current 2 files (`mouse_click.mp3`, `pop.mp3`).
  * Add sound effects triggered by script moves in `draft/builder.py`:
    * **Move 3 (Misconception Flip):** Sub-bass drop, error buzzer, or subtle record scratch on `"They're not"`.
    * **Move 4 & 5 (Mechanisms):** Kinetic swooshes / impacts on physical action verbs (*absorbs*, *bursts*, *shatters*).
    * **Move 6 (Chiastic Payoff):** Clean ding / chime / riser on the takeaway rule.

* **1.3 TTS Micro-Pause & Pacing Refinement**
  * Enhance `tts/tts_client.py` prompt formatting to enforce natural dramatic micro-pauses (200–300ms) after the question (*"So what's the difference?"*) and the misconception flip (*"They're not."*).

---

## Phase 2: Visual Dynamics & Complete Mascot Activation
**Goal:** Prevent visual fatigue by ensuring the on-screen elements change dynamically every 2–3 seconds.

* **2.1 Activate All 13 Mascot Poses**
  * Update `draft/tagger.py` (`determine_clause_role`) to map and trigger the 5 currently unused poses:
    * `smug.png` (for confident canonical facts / superior specs)
    * `twohandsopen.png` (for dual-entity comparisons / weighing trade-offs)
    * `thinking.png` (for analytical breakdowns & mechanisms)
    * `victorious.png` (for winning entities / definitive conclusions)
    * `normal.png` / `profile.png` (for baseline stances and neutral transitions)

* **2.2 Eliminate 8-Second Mascot Freezes**
  * Introduce a maximum pose hold limit (~3.5 seconds) in `draft/tagger.py`.
  * If an explanation sentence runs long, dynamically shift the mascot from an active explanation stance (`left`/`right`) to a gesture (`thinking`/`smug`/`shocked`) on key action verbs.

* **2.3 Active Comparison Card Spotlight**
  * In `draft/builder.py` and `draft/patcher.py`, apply visual emphasis to `img1` and `img2`:
    * When Entity X is discussed (Move 4), scale Image 1 slightly up (`1.05x`) while Image 2 dims to `0.6` opacity.
    * When Entity Y is discussed (Move 5), scale Image 2 slightly up while Image 1 dims.
    * Return both to equal scale on Move 6 (Chiastic Payoff).

* **2.4 Smooth Coordinate Alignment**
  * Standardize horizontal positioning for all mascot poses in `draft/config.py` to prevent abrupt screen jumps when switching to `wtd.png`.

---

## Phase 3: Script Generator Intelligence & Title Engine
**Goal:** Deepen lore accuracy, eliminate formulaic script repetition, and maximize feed click-through rates.

* **3.1 Anti-Metronome Phrasing Diversity**
  * Update `generator/prompt_builder.py` to provide varied, natural phrasings for Move 3 instead of identical `"Most people think [X]. They're not"` across every video.
  * Allow natural variations: *"You'd think [X], but in canon, [Y]"*, *"The common belief is [X] — that's completely backwards"*.

* **3.2 Deeper Lore & Mechanical Trade-Offs**
  * Update prompt guidelines to force high-leverage canonical mechanics (e.g., energy saturation limits, specific comic storylines, thermodynamic trade-offs) rather than basic surface-level definitions.

* **3.3 High-CTR Causal Title Generator**
  * Upgrade `generator/prompt_builder.py` title output from generic `"X vs Y: The Real Difference"` to proven, high-retention causal formats:
    * *"Why [X] Beats [Y]"*
    * *"The Secret Flaw in [X]'s [Y]"*
    * *"One [X] Powers [A]. The Other Powers [B]."*

---

## Phase 4: Cluster Engine & Topic Guardrails
**Goal:** Harness YouTube's recommendation loops by linking related uploads and protecting audience niche focus.

* **4.1 3-Part Franchise Topic Cluster Mode**
  * Add a `--cluster` option to `generate.py` that generates 2 or 3 interconnected comparisons in one run (e.g., *Adamantium vs Vibranium* $\rightarrow$ *Uru vs Adamantium* $\rightarrow$ *Carbonadium vs Vibranium*).
  * Automatically link the forward tease in Video 1 to Video 2, creating algorithmic binge sessions.

* **4.2 Topic Niche & Guardrail Validator**
  * Add an optional topic warning/filter in the CLI if a topic falls outside high-performing fandoms (Marvel, DC, Shonen Anime, Star Wars, Gaming lore) to avoid low-view general knowledge traps.

* **4.3 Input Asset Validation & Ergonomics**
  * Add automated verification in `draft/image_processor.py` for image resolution and aspect ratios in `input/`, with clear terminal warnings if images are missing or distorted.
