# Project Description: Shorts Automation Studio

This project is a video-production automation system for creating YouTube Shorts in a very specific format: fast, comparison-based explainers built around fandom topics, visual contrasts, and punchy retention hooks. The goal is to turn a topic idea into a fully assembled short-form edit that is ready to open in CapCut Desktop and publish with minimal manual work.

The project is not a generic video editor. It is designed around a very narrow content pattern that consistently works for the channel: two recognizable entities, a binary question, a fast myth-busting explanation, and a visual system that reinforces the contrast in real time.

This document describes the operational system, the editing logic, the asset pipeline, and the CapCut project assembly behavior — without going into the script-writing or TTS engines, since those are already implemented elsewhere in the new project.

---

## 1. Core Purpose

The system is built to automate the production of Shorts for a channel called Dont Mix This, centered on comparisons such as:

- Marvel vs DC lore concepts
- Power systems and abilities
- Character mechanics and rules
- Universe definitions and terminology
- Pop-culture confusion points

The ideal short follows a pattern like:

- Immediate binary hook: “This is X. This is Y. So what’s the difference?”
- A common misconception is named and busted quickly
- The explanation reveals the real mechanism behind the contrast
- The visual composition reinforces the distinction in the foreground
- The short ends with a simple CTA and a clean visual payoff

The system is designed to optimize for retention, pacing, and strong visual contrast rather than broad storytelling.

---

## 2. What the Project Outputs

The output of this project is not a finished final video file. It is a production-ready CapCut Desktop draft project that is designed to be opened and rendered in CapCut.

The project prepares:

- comparison images
- title labels
- mascot poses and reactions
- timed subtitle blocks
- background treatment
- overlay effects
- transitions between visual contrast moments
- branded text styling
- project file structure that CapCut can use as a draft

In other words, the system takes a script and a set of visual assets and transforms them into a structured CapCut editing project with all the editorial timing baked in.

---

## 3. Production Philosophy

This project follows a very deliberate Short-form video formula. The content is intentionally reduced to a highly efficient formula:

1. Hook the viewer in the first 1–3 seconds
2. Confirm that the viewer is watching the right kind of contrast
3. Explain the difference using a clear mechanism
4. Reinforce the confusion point visually
5. Deliver a crisp ending with no wasted time

This is not a freeform editing workflow. It is a rigid content-engine architecture built for viewer retention and fast understanding.

The project assumes that a successful short needs:

- strong left-vs-right contrast
- obvious visual hierarchy
- instant readability
- short subtitle blocks
- mascot emphasis moments
- little or no dead air
- clear motion and beat pacing

---

## 4. Asset Model and Visual Structure

### 4.1 Comparison image pairs

The system expects image pairs for a comparison. In deepdive mode it uses a single pair. In compilation mode it uses multiple image pairs.

Typical naming conventions:

- image1 / image2
- image3 / image4
- image5 / image6

Each pair represents a comparison between two entities or concepts. These are often placed side by side or sequentially swapped in the composition depending on the beat.

### 4.2 1:1 crop requirement

The project normalizes comparison images into square crops before placing them into the CapCut draft. This is critical because Shorts are highly vertical, and the design expects a clean center-focused composition.

The crop logic:

- reads the original image
- detects the shortest side
- crops a centered square region
- saves the processed version
- uses the processed square version in the draft

This ensures the final scene stays visually stable and consistent across all videos.

### 4.3 Background layer

Each short has a background visual layer that acts like the structural stage. The project can use a primary background image or a stylized backplate that sets the mood for the scene.

This layer is generally treated as a static supportive layer rather than the storytelling focus. The important elements sit on top of it:

- comparison images
- text labels
- mascot reactions
- short captions
- effect overlays

This creates a layered look where the background anchors the edit while the foreground does the actual persuasion.

---

## 5. Subtitle and Timing System

A huge part of the editing quality is not the script text itself, but the timing and segmentation of the captions.

### 5.1 Word-level timing

The system extracts subtitle timing from the voiceover and splits it into very short chunks. It avoids large subtitle blocks and instead creates short, readable bursts with a maximum word count threshold.

This is important because YouTube Shorts use fast scanning behavior. If subtitles are too long, they become visually noisy and reduce clarity.

The subtitle system does the following:

- converts the voiceover to time-aligned subtitle entries
- splits blocks to a safe word limit
- preserves short phrase cadence
- keeps the visual text blocks easy to read
- aligns subtitle timing to the narration rhythm

### 5.2 Hook blocks and contrast blocks

The project treats subtitle blocks as narrative cues, not just captions. Certain blocks are tagged as special moments, such as:

- hook lines
- misconception lines
- reveal lines
- contrast-explaining lines
- punchline endings

These blocks get special treatment in the draft, including stronger emphasis, more aggressive styling, and more visible keyword highlighting.

### 5.3 Keyword highlighting

For the visual readability of subtitles, the project identifies important keywords inside caption text and highlights them in a brighter color. This is done to draw attention to the most important concept in a sentence.

Examples of highlighted terms include:

- the main entity names
- contrast words like “difference,” “wrong,” “reboot,” “canon,” etc.
- standout concept terms like “magic,” “power,” “weakness,” “universe,” “continuity,” “armor,” etc.

The system tries to highlight the strongest semantic keyword in each subtitle rather than simply applying a generic color to all text. This makes the viewer feel the structure of the argument even when reading quickly.

---

## 6. Mascot System

One of the main identity features of this project is the mascot layer. The mascot is not decorative; it is a performance character that reacts to the script and reinforces the pacing.

### 6.1 Mascot role

The mascot acts like a presenter, commentator, or exaggerated reaction character. It helps the edit feel alive and can visually encode the emotion of the current beat.

Typical mascot functions:

- intro / neutral stance at the start
- shocked or confused reaction at misconceptions
- triumphant pose at payoff moments
- thinking pose during explanation
- smug or victorious stance at the end
- open-hand “explanation” pose during conceptual contrast

The mascot is used to make the short feel like a “hosted” explainer rather than a static slideshow.

### 6.2 Mascot pose mapping

The system uses a mapping file that links each tag or emotion label to a specific mascot asset file. This mapping is central to how the project knows which mascot pose to display at each point in the video.

Examples of pose labels include:

- normal
- left
- right
- remember_this
- wtd
- disagree
- shocked
- victorious
- thinking
- smug
- twohandsopen

These are not arbitrary names; they correspond to emotional states and narrative beats.

### 6.3 Tag-based insertion

The subtitle system inserts labels like [IMG:tag_code] into the script or subtitle text. Later, when the project is built, those tags are interpreted and mapped to the corresponding mascot art file.

This means the script narrative and visual reaction layer stay connected. A line that says “That is the big difference” could trigger a “thinking” pose, while a line like “This is the real issue” may trigger a shocked or victorious expression.

This is one of the key design patterns that makes the edit feel dynamic instead of static.

---

## 7. CapCut Draft Construction Logic

This is the heart of the project. The system does not just render an MP4. It constructs a CapCut Desktop project bundle in the local CapCut draft folder, with structured scene segments, tracks, labels, overlay layers, and timing metadata.

### 7.1 Draft generation target

The project writes the draft output to the local CapCut Desktop draft directory, which means the user can open it immediately inside CapCut and make final refinements if needed.

This is a “draft-first” pipeline, not a final render pipeline. The generated project is designed to be polished enough to use immediately but still editable in the native editor.

### 7.2 Track system

The generated CapCut draft organizes content into layered tracks. The core logic is roughly:

- background track
- comparison image track(s)
- label text track(s)
- subtitle track
- mascot track
- effects overlay track(s)

Each of these layers sits on a different timeline track so they can be edited independently and animated without colliding visually.

### 7.3 Segment logic

The system chops the timeline into segments based on subtitle blocks and comparison beats. Each segment has a:start/end time, a placement target, and a visual role.

This means the draft is not one long static montage. It is structured as multiple timed units:

- hook segment
- misconception segment
- contrast segment
- reveal segment
- closing segment

At each segment boundary, the system may switch:

- which image is visible
- which text labels are in frame
- which mascot pose is active
- which subtitle highlight is emphasized
- whether the visual is zooming, shaking, or fading

### 7.4 Image swap timing

A comparison short usually does not keep both images visible all the time. The project uses the SRT timing and the support tags to decide when to show each side of the comparison.

This creates a dynamic editorial rhythm:

- show A
- then reveal B
- make the viewer compare the two
- then lock on a single explanation moment

The visual flow is designed to feel like a controlled comparison, not a random slide show.

---

## 8. Transition and Motion Logic

The project heavily relies on short, sharp visual transitions and subtle motion patterns to maintain retention. It is explicitly designed to avoid long, slow transitions.

### 8.1 Hard cuts and beat switches

The editorial cadence favors quick cuts between visual states. This is critical for a Shorts format where the viewer is deciding within a second whether to keep watching.

Typical behavior:

- abrupt swap from one image to the other
- text label appears only when relevant
- mascot reaction switches on emotional beat
- caption block updates in sync with speech

### 8.2 Quick effect layering

To make the visual contrast more alive, the project adds brief motion effects to comparison images and overlay layers. The effect is intentionally isolated so it affects only the image or overlay clip, not the full background.

The effect is not a heavy cinematic motion package. It is a lightweight “jitter/beat” effect used to make the visual scene pulse, especially when a key contrast or misconception is introduced.

This kind of effect helps the short feel energetic without making it look sloppy or chaotic.

### 8.3 PIP and overlay isolation

The generated draft uses special overlay-track handling so that image overlays behave like picture-in-picture or layered visual sub-tracks rather than full-scene elements.

This matters because it keeps the motion effect and image treatment from bleeding across the whole timeline or background. The system uses per-track flags and per-segment effect attachment so masks and effects stay isolated to the intended clip.

This is a technical but very important design choice: it prevents the entire project from looking like one giant, over-affected frame.

---

## 9. Text and Label Styling

The project uses a custom font setup and specific styling system for the CapCut output. The text layers are made to feel strong and punchy rather than soft or procedural.

### 9.1 Label styling

Entity names are presented as high-contrast labels, often in uppercase or bold forms, to make each side of the comparison easy to read.

Examples:

- X
- Y
- Mjolnir
- Stormbreaker
- MCU
- Marvel Comics

These labels are placed near the image and treated as the visual anchor for the comparison.

### 9.2 Subtitle font and highlight injection

The CapCut draft patching step injects a chosen font into the text materials and ensures the subtitle blocks retain the proper font path and resource metadata. This avoids the common issue where text renders with the wrong font or looks unstyled in CapCut.

It also adds color emphasis to the most important word in selected subtitle blocks, so the viewer can instantly identify what matters in the sentence.

### 9.3 Color system

The project uses a deliberate high-contrast palette for key visual emphasis:

- orange / warm contrast energy
- cyan / cool explanatory emphasis
- red / danger or conflict
- green / certainty or payoff
- purple / higher concept or fantasy energy

The colors are not random; they help the viewer separate the two sides of a comparison and the emotional state of each beat.

---

## 10. Channel Identity and Brand Rules

The system is explicitly built around a specific brand identity: Dont Mix This.

This identity includes:

- topic focus: pop-culture myth-busting and lore confusion
- visual tone: fast, confident, high-contrast, eyes-on-the-screen
- delivery style: direct, opinionated, crisp, explanatory
- format: binary comparison videos with strong hooks
- branding: text and mascot work as a consistent visual system across videos

This is not a general-purpose editing engine. It is tuned to a content niche and a very recognizable presentation style.

---

## 11. Batch and Workflow Automation

The project also includes a batch system for producing multiple Shorts in sequence from a list of ideas. This turns the automation from a single-shot generator into a repeatable production engine.

### 11.1 Topic queue

The project maintains a list of content ideas, each with identifiers, topic type, status, and labels. This lets the system process topics in sequence without duplicating content or forgetting generated assets.

### 11.2 Batch sandboxing

Each item in a batch can be prepared in its own isolated workspace so output, assets, and generated draft files remain separated and easy to debug.

This matters because the project handles multiple topics and multiple drafts, and each one needs a clean, repeatable source setup.

### 11.3 Validation and guardrails

Before generating a draft, the project checks that:

- the required image files exist
- the SRT is valid
- the timing is sensible
- the pair count matches the mode
- audio and subtitle durations are consistent
- the config is structurally valid

This prevents broken draft outputs and reduces manual cleanup work.

---

## 12. What Makes This Project Different

This project is not just a “video editor wrapper.” It is a complete short-form production system with the following characteristics:

- content-level optimization for Shorts retention
- strict comparison-format structure
- visual binary hook design
- dynamic mascot-driven explanations
- subtitle-first timing choreography
- CapCut-first draft generation
- strong image contrast and motion treatment
- batch-ready operation for multiple Shorts
- built around a specific creator identity and audience expectation

It is best understood as a downstream editing and assembly engine for a particular type of viral explainer video.

---

## 13. How the Draft System Feels in Practice

When a short is generated, the viewer experience should feel like this:

- the scene opens immediately with a clear left-right or A-vs-B setup
- the first subtitle appears in a punchy visual style
- the background stays supportive but not distracting
- the mascot reacts to the key idea or misconception
- the images alternate or swap as the argument evolves
- each beat is readable within a quick glance
- the final punchline lands hard and the visual ends cleanly

This is the core value of the system: it is making the viewer process the comparison quickly and intuitively.

---

## 14. Implementation Summary for Another AI Coding Agent

If another AI coding agent is supposed to rebuild or extend this project, the most important things to preserve are:

1. The short-form comparison format is the real product.
2. CapCut draft assembly is the stage where the content becomes video.
3. The visual hierarchy is more important than any single asset.
4. Subtitle timing and emotion tagging drive pacing and readability.
5. The mascot system is a visual performance layer, not just decoration.
6. The image pair + label + subtitle + effect layer is the core composition model.
7. Strong draft metadata patches are needed so the output opens cleanly and looks correct inside CapCut.
8. Batch automation and asset validation are necessary to keep output reliable.

The editing system should feel like a controlled, repeatable production machine for viral comparison Shorts rather than a general-purpose media editor.

---

## 15. Scope Excluded from This Description

This project description intentionally does not cover:

- script generation logic
- AI writing rules and prompt design
- TTS/voice synthesis generation
- narrative writing heuristics
- speech-to-text and transcription pipeline details

Those are implemented separately and are not part of the CapCut assembly / editing system described here.

---

## 16. Bottom Line

This project is a Shorts content assembly engine for a very specific, highly optimized style of comparison-driven explainer content. Its main job is to convert a structured concept into a persuasive, readable, visually strong CapCut draft with the right pacing, mascot reactions, subtitle timing, and contrast-driven formatting.

The most important technical goal is not “generate a video.” It is “generate a convincing, retention-focused CapCut edit that feels like a highly polished, channel-specific comparison short and opens directly in the editor for final production.”
