"""
Draft Builder Configuration & Asset Mapping for 'Dont Mix This'
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Tuple

# Base Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# CapCut Drafts Directory (Windows & macOS auto-detection)
def get_capcut_drafts_dir() -> str:
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        return os.path.join(local_appdata, "CapCut", "User Data", "Projects", "com.lveditor.draft")
    return r"C:\Users\%USERNAME%\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"


# Mascot Tag -> Filename Mapping
DEFAULT_MASCOT_MAPPING: Dict[str, str] = {
    "normal": "normal.png",
    "left": "left.png",
    "right": "right.png",
    "remember_this": "remember_this.png",
    "wtd": "wtd.png",
    "disagree": "disagree.png",
    "shocked": "shocked.png",
    "victorious": "victorious.png",
    "thinking": "thinking.png",
    "smug": "smug.png",
    "twohandsopen": "twohandsopen.png",
    "final_end": "final_end.png",
}

# Subtitle Highlight Colors (RGB 0.0 - 1.0)
HIGHLIGHT_COLOR_MAP: Dict[str, Tuple[float, float, float]] = {
    "orange": (1.0, 0.35, 0.0),      # Electric Sunset Orange #FF5500 (Vibrant, high-contrast)
    "yellow": (1.0, 0.35, 0.0),
    "cyan": (0.0, 0.85, 1.0),        # Electric Cyan #00D9FF
    "green": (0.0, 0.7, 0.25),       # Emerald Green #00B340
    "purple": (0.55, 0.15, 0.9),     # Electric Purple #8C26E6
    "pink": (0.9, 0.1, 0.55),        # Vivid Magenta Pink #E61A8C
    "red": (1.0, 0.2, 0.2),          # Punchy Red #FF3333
    "white": (1.0, 1.0, 1.0)
}


@dataclass
class DraftConfig:
    # Canvas dimensions & FPS
    width: int = 1080
    height: int = 1920
    fps: int = 30
    
    # Subtitle Font & Styling
    font_name: str = "LuckiestGuy-Rg"
    font_resource_id: str = "7564679598558973200"
    highlight_color: str = "orange"
    max_words_per_line: int = 3
    
    # Visual Layout Transforms (Normalized CapCut coordinates -1.0 to 1.0)
    # Comparison Image 1 (Top Left)
    img1_x: float = -0.465741
    img1_y: float = 0.469792
    img1_scale: float = 0.40
    
    # Comparison Image 2 (Top Right)
    img2_x: float = 0.510185
    img2_y: float = 0.473438
    img2_scale: float = 0.40
    
    # Entity Title Labels (Above Images)
    label1_x: float = -0.448148
    label1_y: float = 0.781771
    label2_x: float = 0.476852
    label2_y: float = 0.778646
    
    # Mascot Stance (Center-Bottom)
    mascot_x: float = -0.088889
    mascot_y: float = -0.425
    mascot_scale: float = 0.42
    
    # Subtitles (Center)
    subtitle_x: float = 0.0
    subtitle_y: float = 0.042188
    subtitle_scale: float = 1.0
    
    # Directories & Assets
    assets_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "assets")
    mascot_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "mascot")
    bg_image_path: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "background" / "dotgrid.png")
    click_sfx_path: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "sound_effects" / "mouse_click.mp3")
    pop_sfx_path: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "sound_effects" / "pop.mp3")
    whoosh_sfx_path: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "sound_effects" / "whoosh-clean.mp3")
    processed_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "assets" / "processed")
    input_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "input")
    drafts_dir: str = field(default_factory=get_capcut_drafts_dir)
    mascot_mapping: Dict[str, str] = field(default_factory=lambda: DEFAULT_MASCOT_MAPPING)
