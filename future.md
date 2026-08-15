# Visual Evolution & Retention Strategy: "Dont Mix This"

## 1. Codebase & Pipeline Architectural Breakdown

To ground all visual proposals in the actual implementation, here is how a video is assembled today:

```
[User Input: Entity X vs Y + Images in input/]
           │
           ▼
[Generator: gemini-3.6-flash] ──► 3 Script Variants (7-Move Architecture, 21-30s)
           │
           ▼
[TTS: gemini-3.1-flash-tts-preview] ──► Studio WAV (Puck Voice, Temp 0.9, 24kHz)
           │
           ▼
[STT & Alignment: Whisper Base + Levenshtein Alignment] ──► Word-level Timestamps
           │
           ▼
[Tagger: draft/tagger.py] ──► Semantic Clause Chunking (<=3 words), 13 Mascot Poses, Left(X)/Right(Y) Anchoring
           │
           ▼
[Draft Builder: draft/builder.py via pycapcut]
  ├── Track 1 (Audio): Voiceover + SFX (Clicks at 0s & Img2 entry, Pop at Q, Whooshes on side swaps)
  ├── Track 2 (Video): Background dotgrid.png (1080x1920 static)
  ├── Track 3 (Video): Image 1 (Top-left, scale 0.40, pos [-0.465, 0.470], Move 4 spotlight 1.06x / Move 5 dim 0.55x)
  ├── Track 4 (Video): Image 2 (Top-right, scale 0.40, pos [0.510, 0.473], enters at Y intro, Move 5 spotlight 1.06x / Move 4 dim 0.55x)
  ├── Track 5 (Video): Mascot (Center-bottom, scale 0.42, gapless pose continuity, shrinks to 0.28 on emphasis)
  ├── Track 6 (Text):  Title X (Red #FF1E40, LuckiestGuy-Rg, pos [-0.448, 0.781])
  ├── Track 7 (Text):  Title Y (Blue #0088FF, LuckiestGuy-Rg, pos [0.476, 0.778], enters at Img2 intro)
  └── Track 8 (Text):  Subtitles (LuckiestGuy-Rg, pos [0.0, 0.042], scale 1.0 / 1.4 on emphasis)
           │
           ▼
[JSON Patcher: draft/patcher.py] ──► Direct draft_content.json injection:
  ├── Font caching & resource UUID binding
  ├── Rich-text keyword highlighting in Electric Sunset Orange (#FF5500)
  ├── PIP track flags (flag=2)
  └── Jitter Beat 600ms entry effect on Image 1 and Image 2
```

### Automation vs. Manual Boundary
- **Fully Automated:** Script generation, TTS audio synthesis, word-level STT timestamping, semantic clause-to-pose mapping, image 1:1 square cropping, multi-track timeline construction with gapless continuity, font/highlight JSON patching, and SFX cueing.
- **Manual Touchpoints:** Putting 2 images in `input/`, selecting the script variant in CLI (`run.py`), and opening the auto-generated CapCut draft to render.

---

## 2. Analysis of the Past "Slam-Card" Experiment vs. "Text Bomb" Success

### Why the Slam-Card Experiment Failed
1. **Loss of the Dual-Anchor Mental Model:** "Dont Mix This" relies on simultaneous visual contrast (X on the left, Y on the right). When a comparison card slammed full-screen, it destroyed the spatial mental model, making the video feel like a chaotic montage rather than a structured comparison.
2. **Visual Hierarchy Collision:** Slam cards competed directly with the stickman mascot and center subtitles for the viewer's focal point.
3. **CapCut Draft Keyframe Fragility:** Programmatic keyframe interpolation in CapCut draft JSONs lacks native spring/bounce physics curves, causing programmatic transforms to feel jarring, clunky, or misaligned with audio transients.

### Why the "Text Bomb" Succeeded
- **Respects Spatial Hierarchy:** The mascot dynamically shrinks (`scale: 0.42 -> 0.28`) and shifts out of the way, giving the center-stage to the enlarged subtitle (`scale: 1.0 -> 1.4`). The cards stay anchored at the top, maintaining context without visual clutter.

---

## 3. Top 8 Visual Recommendations (Ranked by Retention & Engagement Impact)

---

### Rank 1: Pre-Composited Comic Card Frames with Dynamic Red/Blue Accent Borders
1. **Idea:** Automatically composite thick black comic-book stroke borders with colored accent tags (Red for Entity X, Blue for Entity Y) onto comparison images during preprocessing.
2. **Why it helps retention:** In the 0–3s feed swipe window, raw unbordered PNGs blend into the white dotgrid background, creating visual delay. A high-contrast comic frame with Red/Blue color tagging establishes an immediate visual anchor in <200ms, raising the initial "Stayed to Watch" % by making the two entities instantly readable.
3. **Implementation:** Update `draft/image_processor.py` to composite a 12px rounded black stroke border and top color-accent pill (Red `#FF1E40` for X, Blue `#0088FF` for Y) using Pillow before passing to `builder.py`. Zero change required in CapCut JSON.
4. **Effort:** **Low**
5. **Risk of looking bad:** **Zero Risk.** Fully pre-rendered in Python/Pillow; no CapCut keyframe or track timing dependencies.

---

### Rank 2: Move 3 "Myth / False" Red Comic Stamp Overlay (The Re-Hook Snapper)
1. **Idea:** Pop a stylized, hand-drawn red "MYTH" or "FALSE" badge over the center stage for 600ms exactly when Move 3 triggers the misconception flip (`disagree.png`).
2. **Why it helps retention:** Channel analytics show a retention drop-off between seconds 4–8 if the misconception isn't recognized. A bold comic stamp visually reinforces the contradiction ("Most people think X — that's WRONG"), snapping viewer focus back right before the drop-off cliff.
3. **Implementation:** Add an overlay image track in `draft/builder.py` referencing `assets/overlays/myth_stamp.png`. Trigger it at the start timestamp of any subtitle tagged with rule `Rule: Misconception Flip` or pose `disagree`, holding for 600ms accompanied by the existing `pop.mp3` SFX.
4. **Effort:** **Low**
5. **Risk of looking bad:** **Low.** Unlike card slams, the stamp is a temporary static overlay in the stickman comic style that auto-dismisses in 0.6s without moving layout elements.

---

### Rank 3: Chiastic Payoff Screen Split (Move 6 Visual Synthesis)
1. **Idea:** Transition the white background into a crisp 50/50 dual-tinted split (subtle warm left / subtle cool right with a dashed black comic dividing line) during Move 6 ("A does X, while B does Y").
2. **Why it helps retention:** Move 6 is the core takeaway sentence viewers rewatch for (driving APV > 90%). Splitting the background into two distinct visual zones mirrors the chiastic verbal structure, giving the viewer's brain an immediate structural map of the two mechanisms.
3. **Implementation:** Create `assets/background/split_stage.png`. In `builder.py`, split `bg_track` at `move6_start_us` to swap from `dotgrid.png` to `split_stage.png` through the end of the video.
4. **Effort:** **Low**
5. **Risk of looking bad:** **Low.** Replaces a background asset on an existing track at an already-computed timestamp (`move6_start_us` in `compute_card_spotlight_segments`).

---

### Rank 4: Move 7 "Next Matchup" Silhouette Teaser & Interactive Subscribe Prompt
1. **Idea:** Swap the top comparison cards for mystery silhouette / "VS" teaser cards of the upcoming battle during Move 7, paired with an animated subscribe cursor/badge on `final_end.png`.
2. **Why it helps retention & subscribes:** Channel data proved that specific forward teases (*"Next is Dr. Strange vs Scarlet Witch"*) generated 41 subscribers vs 0–2 for generic endings. Displaying visual teaser silhouettes for the next topic gives viewers an instant reason to tap Subscribe before swiping.
3. **Implementation:** In `builder.py`, cut Image 1 and Image 2 tracks at `move7_start` (position >= 85%) and place a generated silhouette/question-mark card or franchise graphic, while placing an animated subscribe badge asset near the mascot.
4. **Effort:** **Medium**
5. **Risk of looking bad:** **Low.** Operates only in the final 2–3 seconds of the video; does not interfere with the core educational comparison.

---

### Rank 5: Polish & Scale the "Text Bomb" with Localized 200ms Micro-Impact Shake
1. **Idea:** Standardize the working text-bomb emphasis (large caption + mascot shrink) by injecting a 200ms camera micro-shake effect on keyword impact moments.
2. **Why it helps retention:** Pacing fatigue occurs when a video maintains uniform energy for 25 seconds. Micro-impact shakes on high-velocity action verbs (`ABSORBS`, `SHATTERS`, `OVERHEATS`) create kinetic punctuation that resets the viewer's attention cycle every 5–7 seconds.
3. **Implementation:** In `draft/patcher.py`, inject CapCut's built-in `Camera Shake` or `Jitter` video effect (`render_index: 11000`) for 200ms on the canvas at each `is_emphasis` chunk timestamp. Keep the cards and text centered.
4. **Effort:** **Medium**
5. **Risk of looking bad:** **Medium.** *Past Failure Precaution:* Full-screen element movement looks terrible. The fix is to apply the shake to the *entire canvas track* at very low amplitude (0.05) and short duration (150–200ms), keeping image coordinates completely fixed.

---

### Rank 6: Doodled Comic Focus Arrows (Mascot-to-Card Visual Directionality)
1. **Idea:** Display a snappy 300ms hand-drawn black doodle arrow pointing from the mascot's hand toward Entity X when `left.png` triggers and Entity Y when `right.png` triggers.
2. **Why it helps retention:** With high speaking velocity (2.8 words/sec), viewers' eyes can lag behind narration. A fast, sketchy directional arrow guides eye gaze directly to the relevant card, reducing cognitive load and keeping viewers glued to the screen.
3. **Implementation:** Add `assets/overlays/arrow_left.png` and `arrow_right.png`. In `builder.py`, insert a 350ms segment on an overlay track whenever the mascot transitions from `normal`/`thinking` to `left` or `right`.
4. **Effort:** **Medium**
5. **Risk of looking bad:** **Low.** Assets must strictly match the stickman mascot's rough black ink style (no clean corporate vectors or 3D arrows).

---

### Rank 7: Dynamic 2-Word "Mechanism Badge" Below Comparison Cards
1. **Idea:** Pop a compact, high-contrast comic pill tag (e.g. `[ KINETIC ABSORPTION ]` / `[ MOLECULAR RIGIDITY ]`) directly underneath the active card during Move 4 and Move 5.
2. **Why it helps retention:** Mechanical clarity is the defining value proposition of the channel. Displaying the 2-word physical mechanism under the card reinforces comprehension for sound-off or fast-scrolling viewers and highlights the deep lore angle.
3. **Implementation:** Have `generator/prompt_builder.py` extract a 2-word `mechanism_tag_x` and `mechanism_tag_y` in the JSON output. In `builder.py`, generate a text track segment positioned at `y = 0.25` beneath the active card during Move 4 and Move 5.
4. **Effort:** **Medium**
5. **Risk of looking bad:** **Medium.** Must maintain strict padding between the bottom of the card (`y = 0.27`) and the top of the center subtitles (`y = 0.04`) to prevent visual crowding.

---

### Rank 8: Minimalist Dotted Frame-Border Progress Scrub Line
1. **Idea:** A subtle, ultra-thin (3px) dark charcoal progress bar along the bottom frame boundary (or top edge) that fills smoothly from 0 to 100% over the video duration.
2. **Why it helps retention:** While YouTube has a native scrub bar, custom on-screen micro-progress bars provide an immediate subconscious signal that the video is short (<30s) and near completion, discouraging mid-video drop-offs at the 15–20s mark.
3. **Implementation:** Create a pre-rendered 30-second looping video asset `assets/overlays/progress_bar.mp4` (or scale a 1px solid line across keyframes in CapCut JSON) and place it on track index 1.
4. **Effort:** **Low**
5. **Risk of looking bad:** **Low.** Must be strictly minimal (3px thin, monochrome #222222) to avoid looking like cheap TikTok repost spam.

---

## 4. Summary Matrix & Immediate Next Steps

| Rank | Visual Improvement | Primary Metric Target | Pipeline Component | Implementation Effort | Fragility Risk |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **1** | Comic Card Borders & Accent Tags | Stayed to Watch % (0-3s) | `image_processor.py` | **Low** | None |
| **2** | Move 3 "Myth/False" Stamp | Re-hook Retention (4-8s) | `builder.py` + Overlay | **Low** | Low |
| **3** | Chiastic Split Background | Payoff & Re-watch APV | `builder.py` + BG Asset | **Low** | Low |
| **4** | Move 7 Next Matchup Teaser | Subscribers & Channel Loop | `builder.py` + Script JSON | **Medium** | Low |
| **5** | Text Bomb + Micro Canvas Shake | Mid-Video Engagement | `patcher.py` (Effects) | **Medium** | Medium |
| **6** | Comic Focus Hand Arrows | Visual Directionality | `builder.py` + Overlays | **Medium** | Low |
| **7** | 2-Word Mechanism Badges | Lore Comprehension | `prompt_builder` + `builder`| **Medium** | Medium |
| **8** | Minimal Frame Progress Bar | Completion Rate | `builder.py` (Overlay Track)| **Low** | Low |
