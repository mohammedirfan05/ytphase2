# "Dont Mix This" — YouTube Shorts Automation

End-to-end automation pipeline for the YouTube Shorts channel **"Dont Mix This"**. Combines data-grounded script generation (`gemini-3.6-flash`) with high-energy voice synthesis (`gemini-3.1-flash-tts-preview`).

---

## 📂 Minimal Codebase Structure

```
automation_new/
├── .env                  # Your GEMINI_API_KEY
├── .env.example          # Environment template
├── .gitignore            # Protects keys, logs, audio, and cache
├── config.yaml           # Duration (21-30s), tone, pace, and anti-slop knobs
├── run.py                # 🚀 Full end-to-end pipeline (Script + Voiceover)
├── generate.py           # Standalone script generator CLI
├── requirements.txt      # Python dependencies
├── README.md             # Documentation
├── generator/            # Script generator engine
│   ├── config.py
│   ├── prompt_builder.py
│   ├── llm_client.py
│   ├── validator.py
│   └── logger.py
├── tts/                  # 🎙️ Gemini TTS engine (Puck / 0.9 temp)
│   ├── __init__.py
│   ├── config.py
│   └── tts_client.py
├── generated_scripts/    # Approved JSON scripts
├── outputs/              # Voiceover WAV files and export packages
└── research_archive/     # Archived Phase 1 research data, CSVs & reports
```

---

## 🎙️ Voiceover (TTS) Specifications
Strictly calibrated to your playground configuration:
- **Model:** `gemini-3.1-flash-tts-preview`
- **Voice:** `Puck` (Upbeat, Middle pitch)
- **Temperature:** `0.9` (Strictly enforced)
- **Scene:** `A fast-paced educational explainer breaking down story terminology, direct-to-camera style`
- **Sample Context:** `Energetic YouTube Shorts narration, quick pacing, conversational but confident tone`
- **Output:** Studio-grade 24kHz 16-bit Mono WAV audio

---

## 🚀 How to Run the Unified Pipeline

Simply run:
```powershell
python run.py
```

### Flow:
1. Prompts you for `Entity X` (e.g. `Mjolnir`) and `Entity Y` (e.g. `Stormbreaker`).
2. Generates the **best 3 script variants** (21–30s duration, 7-move structure, zero AI slop).
3. Prompts you to pick your favorite variant (`1`, `2`, or `3`).
4. Automatically pushes the approved script to **Gemini Flash TTS** and outputs:
   - 📄 `generated_scripts/<topic>.json`
   - 🔊 `outputs/<topic>.wav`
