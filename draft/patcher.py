"""
CapCut Draft JSON Patcher: Fonts, Rich-Text Word Highlighting & Video Effects
"""

import os
import re
import json
import uuid
import copy
import glob
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from draft.config import HIGHLIGHT_COLOR_MAP


def resolve_capcut_font_info(font_name: str = "LuckiestGuy-Rg", resource_id: str = "7564679598558973200") -> Tuple[str, str]:
    """
    Finds the local cached .ttf path for font_name in CapCut cache directory.
    """
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    cache_dir = os.path.join(local_appdata, "CapCut", "User Data", "Cache", "effect", resource_id)

    font_path = ""
    if os.path.isdir(cache_dir):
        ttf_files = glob.glob(os.path.join(cache_dir, "**", "*.ttf"), recursive=True)
        if ttf_files:
            font_path = ttf_files[0].replace('\\', '/')

    if not font_path:
        font_path = f"C:/{font_name}.ttf"

    return resource_id, font_path


def find_keyword_span(text: str, title_labels: Optional[List[str]] = None) -> Optional[Tuple[int, int]]:
    """
    Finds the character span (start, end) of the best keyword to highlight in the subtitle text.
    """
    if not text or not text.strip():
        return None

    # 1. Match entity labels first
    if title_labels:
        for lbl in title_labels:
            if not lbl or len(lbl.strip()) < 2:
                continue
            lbl_clean = lbl.strip()
            m = re.search(r'\b' + re.escape(lbl_clean) + r'\b', text, re.IGNORECASE)
            if m:
                return (m.start(), m.end())

    # 2. Priority key contrast / action words
    priority_keywords = [
        "difference", "versus", "vs", "wrong", "incorrect", "never", "impossible",
        "secret", "shared", "original", "rebooted", "mechanism", "weakness", "power",
        "energy", "universe", "armor", "comic", "canon", "mass", "burst", "absorbs"
    ]
    for kw in priority_keywords:
        m = re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)
        if m:
            return (m.start(), m.end())

    # 3. Fallback: Longest substantive word
    stop_words = {
        "this", "that", "these", "those", "is", "are", "was", "were", "the", "a", "an",
        "and", "or", "but", "so", "for", "with", "from", "into", "they", "them", "their",
        "most", "people", "think", "both", "just", "what", "whats", "you", "your"
    }
    candidates = []
    for match in re.finditer(r'\b[A-Za-z0-9\'-]+\b', text):
        w = match.group(0).lower().strip("'-")
        if w not in stop_words and len(w) >= 3:
            candidates.append((len(w), match.start(), match.end()))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, start, end = candidates[0]
        return (start, end)

    return None


def patch_draft_content_json(
    draft_dir: str,
    font_name: str = "LuckiestGuy-Rg",
    font_resource_id: str = "7564679598558973200",
    labels: Optional[List[str]] = None,
    highlight_color: str = "orange",
    add_effects: bool = True
) -> bool:
    """
    Directly patches the draft_content.json file in the CapCut project directory.
    """
    draft_json_path = os.path.join(draft_dir, "draft_content.json")
    if not os.path.isfile(draft_json_path):
        return False

    res_id, font_path = resolve_capcut_font_info(font_name, font_resource_id)
    highlight_rgb = HIGHLIGHT_COLOR_MAP.get(highlight_color.lower(), (1.0, 0.35, 0.0))
    title_labels = [l.strip().upper() for l in (labels or []) if l and l.strip()]

    try:
        with open(draft_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Update tracks to PIP overlay flags (flag = 2) for non-background video tracks
        for track in data.get('tracks', []):
            t_name = track.get('name', '')
            if track.get('type') == 'video' and t_name != 'bg_track':
                track['flag'] = 2

        # 2. Patch font and rich-text word highlights in texts
        texts = data.get('materials', {}).get('texts', [])
        
        # Subtitle material IDs
        subtitle_material_ids = set()
        for track in data.get('tracks', []):
            if track.get('name') == 'subtitle_track':
                for seg in track.get('segments', []):
                    if seg.get('material_id'):
                        subtitle_material_ids.add(seg['material_id'])

        for text_item in texts:
            text_item['use_effect_default_color'] = False
            text_item['preset_id'] = ''
            text_item['preset_name'] = ''
            text_item['font_resource_id'] = res_id
            text_item['font_id'] = res_id
            text_item['font_path'] = font_path
            text_item['font_title'] = font_name
            text_item['font_name'] = font_name
            text_item['fonts'] = [
                {
                    'id': uuid.uuid4().hex.upper(),
                    'resource_id': res_id,
                    'third_resource_id': '',
                    'category_id': 'preset',
                    'category_name': 'Presets',
                    'source_platform': 1,
                    'path': font_path,
                    'effect_id': res_id,
                    'title': font_name,
                    'team_id': '',
                    'file_uri': '',
                    'request_id': ''
                }
            ]

            if 'content' in text_item and isinstance(text_item['content'], str):
                try:
                    content_obj = json.loads(text_item['content'])
                    text_str = content_obj.get('text', '')

                    if 'styles' in content_obj and content_obj['styles']:
                        is_subtitle = text_item.get('id') in subtitle_material_ids
                        is_title_label = any(lbl and lbl in text_str.upper() for lbl in title_labels)

                        if is_title_label:
                            for s in content_obj['styles']:
                                s['font'] = {'id': res_id, 'path': font_path}
                                s['size'] = 9.0
                        elif is_subtitle and text_str.strip():
                            base_style = content_obj['styles'][0]
                            base_style['font'] = {'id': res_id, 'path': font_path}
                            text_len = len(text_str)

                            kw_range = find_keyword_span(text_str, title_labels)
                            if kw_range:
                                kw_start, kw_end = kw_range
                                new_styles = []

                                if kw_start > 0:
                                    s_before = copy.deepcopy(base_style)
                                    s_before['range'] = [0, kw_start]
                                    new_styles.append(s_before)

                                s_kw = copy.deepcopy(base_style)
                                s_kw['range'] = [kw_start, kw_end]
                                if 'fill' in s_kw and 'content' in s_kw['fill'] and 'solid' in s_kw['fill']['content']:
                                    s_kw['fill']['content']['solid']['color'] = list(highlight_rgb)
                                    s_kw['fill']['content']['solid']['alpha'] = 1.0
                                new_styles.append(s_kw)

                                if kw_end < text_len:
                                    s_after = copy.deepcopy(base_style)
                                    s_after['range'] = [kw_end, text_len]
                                    new_styles.append(s_after)

                                content_obj['styles'] = new_styles
                                text_item['is_rich_text'] = True
                            else:
                                for s in content_obj['styles']:
                                    s['font'] = {'id': res_id, 'path': font_path}
                        else:
                            for s in content_obj['styles']:
                                s['font'] = {'id': res_id, 'path': font_path}

                    text_item['content'] = json.dumps(content_obj, ensure_ascii=False)
                except Exception:
                    pass

        # 3. Inject Jitter Beat clip effects on image tracks if requested
        if add_effects:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            eff_cache_path = os.path.join(
                local_appdata, "CapCut", "User Data", "Cache", "effect",
                "7626761686543830290", "ed61aeec3e6dae1262ce40fa34d86c95"
            ).replace('\\', '/')
            
            effects_list = data.get('materials', {}).get('video_effects', [])
            image_track_names = {'img1_track', 'img2_track'}
            
            for track in data.get('tracks', []):
                if track.get('name') in image_track_names:
                    for seg in track.get('segments', [])[:1]:
                        eff_id = uuid.uuid4().hex.upper()
                        if 'extra_material_refs' not in seg:
                            seg['extra_material_refs'] = []
                        seg['extra_material_refs'].append(eff_id)
                        
                        effects_list.append({
                            "id": eff_id,
                            "effect_id": "7626761686543830290",
                            "resource_id": "7626761686543830290",
                            "name": "Jitter Beat",
                            "type": "video_effect",
                            "sub_type": 0,
                            "bind_segment_id": "",
                            "transparent_params": "",
                            "path": eff_cache_path if os.path.exists(eff_cache_path) else "",
                            "value": 1.0,
                            "category_id": "1111",
                            "category_name": "Video effects",
                            "platform": "all",
                            "apply_target_type": 0,
                            "source_platform": 1,
                            "version": "",
                            "item_effect_type": 0,
                            "adjust_params": [
                                {
                                    "name": "effects_adjust_speed",
                                    "value": 0.08,
                                    "default_value": 0.33333333333333
                                }
                            ],
                            "time_range": {
                                "start": 0,
                                "duration": 600_000
                            },
                            "render_index": 11000,
                            "track_render_index": 0
                        })
            
            if 'materials' not in data:
                data['materials'] = {}
            data['materials']['video_effects'] = effects_list

        with open(draft_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False
