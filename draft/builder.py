"""
CapCut Desktop Draft Builder for 'Dont Mix This'
Constructs complete, layered, multi-track CapCut projects ready to open in CapCut Desktop.
Applies gapless timeline continuity for mascot poses and subtitle captions.
"""

import os
import re
import sys
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import pycapcut as pcc
from pycapcut.metadata.effect_meta import EffectMeta

from draft.config import DraftConfig
from draft.stt import get_wav_duration_us
from draft.tagger import TaggedSubtitle
from draft.image_processor import ensure_1to1_crop
from draft.patcher import patch_draft_content_json

logger = logging.getLogger("DraftBuilder")

# Threshold in microseconds for distinguishing a conversational pause from a genuine long silence.
# Any inter-caption gap <= 1.2s is smoothly bridged so captions never flicker off.
CAPTION_PAUSE_THRESHOLD_US = 1_200_000


class CustomFontWrapper:
    """Wrapper class so pycapcut's TextSegment accepts custom font metadata."""
    def __init__(self, font_name: str, resource_id: str = "7564679598558973200"):
        self.value = EffectMeta(font_name, True, resource_id, resource_id, "", [])


def optimize_mascot_timeline(
    tagged_subtitles: List[TaggedSubtitle],
    cfg: DraftConfig,
    total_duration_us: int
) -> Tuple[List[Dict], Dict]:
    """
    Builds a gapless mascot overlay timeline:
    1. Groups consecutive identical poses into single continuous clips.
    2. Extends each pose clip until the START of the next pose (0 gap).
    3. Extends first clip to start at 0us and final clip to total_duration_us.
    Returns the list of optimized mascot clips and gap statistics.
    """
    if not tagged_subtitles:
        return [], {"raw_gaps": 0, "fixed_gaps": 0, "dead_time_ms": 0}

    raw_gaps = 0
    dead_time_us = 0
    for i in range(len(tagged_subtitles) - 1):
        gap = tagged_subtitles[i + 1].start_us - tagged_subtitles[i].end_us
        if gap > 0:
            raw_gaps += 1
            dead_time_us += gap

    # 1. Merge contiguous identical poses
    merged_groups = []
    current = None

    for sub in tagged_subtitles:
        pose_name = sub.pose
        pose_file = cfg.mascot_mapping.get(pose_name, "left.png")
        pose_path = cfg.mascot_dir / pose_file
        if not pose_path.is_file():
            pose_path = cfg.mascot_dir / "left.png"

        pose_path_str = str(pose_path)

        if current is None:
            current = {
                "path": pose_path_str,
                "pose": pose_name,
                "start_us": sub.start_us,
                "end_us": sub.end_us,
                "is_emp": sub.is_emphasis
            }
        else:
            if current["path"] == pose_path_str:
                current["end_us"] = sub.end_us
                if sub.is_emphasis:
                    current["is_emp"] = True
            else:
                merged_groups.append(current)
                current = {
                    "path": pose_path_str,
                    "pose": pose_name,
                    "start_us": sub.start_us,
                    "end_us": sub.end_us,
                    "is_emp": sub.is_emphasis
                }
    if current:
        merged_groups.append(current)

    # 2. Extend durations to bridge all gaps seamlessly
    optimized_clips = []
    num_groups = len(merged_groups)

    for i, gp in enumerate(merged_groups):
        # First clip starts at 0 to ensure mascot is visible from frame 1
        st_us = 0 if i == 0 else gp["start_us"]
        
        # Clip extends right to the start of the next group
        if i < num_groups - 1:
            next_start = merged_groups[i + 1]["start_us"]
            et_us = next_start
        else:
            # Final clip holds until video end
            et_us = total_duration_us

        dur_us = max(100_000, et_us - st_us)

        scale = 0.28 if gp["is_emp"] else cfg.mascot_scale
        pos_x = 0.351852 if "wtd" in gp["path"] else cfg.mascot_x

        optimized_clips.append({
            "path": gp["path"],
            "pose": gp["pose"],
            "start_us": st_us,
            "end_us": et_us,
            "duration_us": dur_us,
            "scale": scale,
            "pos_x": pos_x,
            "pos_y": cfg.mascot_y
        })

    stats = {
        "raw_gaps": raw_gaps,
        "fixed_gaps": 0,
        "dead_time_ms": round(dead_time_us / 1000.0, 1),
        "original_blocks": len(tagged_subtitles),
        "merged_clips": len(optimized_clips)
    }

    return optimized_clips, stats


def optimize_caption_timeline(
    tagged_subtitles: List[TaggedSubtitle],
    total_duration_us: int,
    pause_threshold_us: int = CAPTION_PAUSE_THRESHOLD_US
) -> Tuple[List[Dict], Dict]:
    """
    Builds a smooth, flicker-free subtitle caption timeline:
    Extends each caption chunk until the START of the next chunk,
    unless the gap exceeds pause_threshold_us (intentional long silence).
    """
    if not tagged_subtitles:
        return [], {"raw_gaps": 0, "fixed_gaps": 0, "dead_time_ms": 0}

    raw_gaps = 0
    dead_time_us = 0
    n = len(tagged_subtitles)

    for i in range(n - 1):
        gap = tagged_subtitles[i + 1].start_us - tagged_subtitles[i].end_us
        if gap > 0:
            raw_gaps += 1
            dead_time_us += gap

    optimized_captions = []

    for i, sub in enumerate(tagged_subtitles):
        st_us = sub.start_us

        if i < n - 1:
            next_st = tagged_subtitles[i + 1].start_us
            gap = next_st - sub.end_us
            if gap <= pause_threshold_us:
                et_us = next_st
            else:
                # Genuine long silence: hold for natural duration + 300ms tail
                et_us = min(next_st, sub.end_us + 300_000)
        else:
            # Last caption: hold until total_duration_us or at least 1.5s
            et_us = min(total_duration_us, max(sub.end_us + 800_000, total_duration_us))

        dur_us = max(100_000, et_us - st_us)

        optimized_captions.append({
            "text": sub.text,
            "start_us": st_us,
            "end_us": et_us,
            "duration_us": dur_us,
            "is_emphasis": sub.is_emphasis,
            "pose": sub.pose,
            "index": sub.index
        })

    stats = {
        "raw_gaps": raw_gaps,
        "fixed_gaps": 0,
        "dead_time_ms": round(dead_time_us / 1000.0, 1),
        "total_chunks": n
    }

    return optimized_captions, stats


class CapCutDraftBuilder:
    def __init__(self, config: Optional[DraftConfig] = None):
        self.config = config or DraftConfig()

    def build_draft(
        self,
        project_name: str,
        concept_x: str,
        concept_y: str,
        audio_path: str,
        tagged_subtitles: List[TaggedSubtitle],
        image1_path: Optional[str] = None,
        image2_path: Optional[str] = None,
    ) -> Tuple[str, Dict]:
        """
        Assembles and outputs the CapCut draft project with gapless timeline continuity.
        Returns (draft_project_dir, continuity_stats).
        """
        cfg = self.config
        drafts_dir = os.path.expandvars(cfg.drafts_dir)
        os.makedirs(drafts_dir, exist_ok=True)

        draft_folder = pcc.DraftFolder(drafts_dir)
        try:
            script = draft_folder.create_draft(
                project_name,
                width=cfg.width,
                height=cfg.height,
                fps=cfg.fps,
                allow_replace=True
            )
        except (PermissionError, OSError):
            project_name = f"{project_name}_new"
            script = draft_folder.create_draft(
                project_name,
                width=cfg.width,
                height=cfg.height,
                fps=cfg.fps,
                allow_replace=True
            )

        max_sub_end_us = max((sub.end_us for sub in tagged_subtitles), default=30_000_000)
        audio_duration_us = get_wav_duration_us(audio_path)
        total_duration_us = max(audio_duration_us, max_sub_end_us)

        # 1. Voiceover Audio Track
        if audio_path and os.path.isfile(audio_path):
            script.add_track(pcc.TrackType.audio, "audio_track")
            audio_mat = pcc.AudioMaterial(os.path.abspath(audio_path))
            if audio_duration_us > 0:
                audio_mat.duration = audio_duration_us
            audio_seg = pcc.AudioSegment(audio_mat, pcc.Timerange(0, total_duration_us))
            script.add_segment(audio_seg, track_name="audio_track")

        # 2. Background Track (dotgrid stage)
        bg_path = str(cfg.bg_image_path)
        if os.path.isfile(bg_path):
            script.add_track(pcc.TrackType.video, "bg_track")
            bg_mat = pcc.VideoMaterial(os.path.abspath(bg_path))
            bg_mat.duration = total_duration_us
            bg_clip = pcc.ClipSettings(
                scale_x=1.0,
                scale_y=1.0,
                transform_x=0.0,
                transform_y=0.0,
                alpha=1.0
            )
            bg_seg = pcc.VideoSegment(bg_mat, pcc.Timerange(0, total_duration_us), clip_settings=bg_clip)
            script.add_segment(bg_seg, track_name="bg_track")

        # Determine Image 2 & Title Y reveal timestamp
        img2_start_us = 0
        for sub in tagged_subtitles:
            if sub.pose == "right":
                img2_start_us = sub.start_us
                break
        if img2_start_us == 0 and len(tagged_subtitles) >= 2:
            img2_start_us = tagged_subtitles[1].start_us

        # 3. Comparison Image 1 (Top Left)
        if image1_path and os.path.isfile(image1_path):
            cropped_img1 = ensure_1to1_crop(image1_path, str(cfg.processed_dir))
            script.add_track(pcc.TrackType.video, "img1_track")
            img1_mat = pcc.VideoMaterial(cropped_img1)
            img1_mat.duration = total_duration_us
            img1_clip = pcc.ClipSettings(
                scale_x=cfg.img1_scale,
                scale_y=cfg.img1_scale,
                transform_x=cfg.img1_x,
                transform_y=cfg.img1_y,
                alpha=1.0
            )
            img1_seg = pcc.VideoSegment(img1_mat, pcc.Timerange(0, total_duration_us), clip_settings=img1_clip)
            script.add_segment(img1_seg, track_name="img1_track")

        # 4. Comparison Image 2 (Top Right)
        if image2_path and os.path.isfile(image2_path):
            cropped_img2 = ensure_1to1_crop(image2_path, str(cfg.processed_dir))
            script.add_track(pcc.TrackType.video, "img2_track")
            img2_dur_us = total_duration_us - img2_start_us
            img2_mat = pcc.VideoMaterial(cropped_img2)
            img2_mat.duration = img2_dur_us
            img2_clip = pcc.ClipSettings(
                scale_x=cfg.img2_scale,
                scale_y=cfg.img2_scale,
                transform_x=cfg.img2_x,
                transform_y=cfg.img2_y,
                alpha=1.0
            )
            img2_seg = pcc.VideoSegment(img2_mat, pcc.Timerange(img2_start_us, img2_dur_us), clip_settings=img2_clip)
            script.add_segment(img2_seg, track_name="img2_track")

        # 5. SFX Clicks & Pops
        sfx_click = str(cfg.click_sfx_path)
        sfx_pop = str(cfg.pop_sfx_path)
        
        # Click 1 at 0s
        if os.path.isfile(sfx_click):
            script.add_track(pcc.TrackType.audio, "sfx_click1")
            c1_mat = pcc.AudioMaterial(os.path.abspath(sfx_click))
            c1_dur = get_wav_duration_us(sfx_click) or 500_000
            c1_mat.duration = c1_dur
            script.add_segment(pcc.AudioSegment(c1_mat, pcc.Timerange(0, c1_dur)), track_name="sfx_click1")

        # Click 2 at img2_start_us
        if os.path.isfile(sfx_click) and img2_start_us > 0:
            script.add_track(pcc.TrackType.audio, "sfx_click2")
            c2_mat = pcc.AudioMaterial(os.path.abspath(sfx_click))
            c2_dur = get_wav_duration_us(sfx_click) or 500_000
            c2_mat.duration = c2_dur
            script.add_segment(pcc.AudioSegment(c2_mat, pcc.Timerange(img2_start_us, c2_dur)), track_name="sfx_click2")

        # Pop on question / payoff
        if os.path.isfile(sfx_pop) and len(tagged_subtitles) >= 3:
            q_start_us = max(0, tagged_subtitles[2].start_us - 80_000)
            script.add_track(pcc.TrackType.audio, "sfx_pop")
            p_mat = pcc.AudioMaterial(os.path.abspath(sfx_pop))
            p_dur = get_wav_duration_us(sfx_pop) or 700_000
            p_mat.duration = p_dur
            script.add_segment(pcc.AudioSegment(p_mat, pcc.Timerange(q_start_us, p_dur)), track_name="sfx_pop")

        # 6. Gapless Mascot Track (Stance Merging + Seamless Extension)
        script.add_track(pcc.TrackType.video, "mascot_track")
        mascot_clips, mascot_stats = optimize_mascot_timeline(tagged_subtitles, cfg, total_duration_us)

        # Whoosh SFX on mascot side-switches (left <-> right)
        sfx_whoosh = str(cfg.whoosh_sfx_path) if hasattr(cfg, "whoosh_sfx_path") and cfg.whoosh_sfx_path else str(cfg.assets_dir / "sound_effects" / "whoosh-clean.mp3")
        if not os.path.isfile(sfx_whoosh):
            alt_whoosh = cfg.assets_dir / "sound_effects" / "whoosh.mp3"
            if alt_whoosh.is_file():
                sfx_whoosh = str(alt_whoosh)

        if os.path.isfile(sfx_whoosh) and len(mascot_clips) > 1:
            w_dur = get_wav_duration_us(sfx_whoosh) or 400_000
            whoosh_idx = 0
            for idx in range(1, len(mascot_clips)):
                prev_pose = mascot_clips[idx - 1]["pose"]
                curr_pose = mascot_clips[idx]["pose"]
                if (prev_pose == "left" and curr_pose == "right") or (prev_pose == "right" and curr_pose == "left"):
                    w_start = max(0, mascot_clips[idx]["start_us"] - 60_000)
                    whoosh_idx += 1
                    track_name = f"sfx_whoosh_{whoosh_idx}"
                    script.add_track(pcc.TrackType.audio, track_name)
                    w_mat = pcc.AudioMaterial(os.path.abspath(sfx_whoosh))
                    w_mat.duration = w_dur
                    script.add_segment(pcc.AudioSegment(w_mat, pcc.Timerange(w_start, w_dur)), track_name=track_name)

        for m_clip_info in mascot_clips:
            dur = m_clip_info["duration_us"]
            if dur <= 0:
                continue
            m_mat = pcc.VideoMaterial(m_clip_info["path"])
            m_mat.duration = dur
            
            m_clip = pcc.ClipSettings(
                scale_x=m_clip_info["scale"],
                scale_y=m_clip_info["scale"],
                transform_x=m_clip_info["pos_x"],
                transform_y=m_clip_info["pos_y"],
                alpha=1.0
            )
            m_seg = pcc.VideoSegment(m_mat, pcc.Timerange(m_clip_info["start_us"], dur), clip_settings=m_clip)
            try:
                script.add_segment(m_seg, track_name="mascot_track")
            except Exception:
                pass

        # 7. Title X Label Track
        font_wrapper = CustomFontWrapper(cfg.font_name, cfg.font_resource_id)
        if concept_x:
            script.add_track(pcc.TrackType.text, "title_x_track")
            lbl1_seg = pcc.TextSegment(
                concept_x.upper(),
                pcc.Timerange(0, total_duration_us),
                font=font_wrapper,
                style=pcc.TextStyle(color=(1.0, 0.117, 0.251)),
                clip_settings=pcc.ClipSettings(
                    transform_x=cfg.label1_x,
                    transform_y=cfg.label1_y,
                    scale_x=1.0,
                    scale_y=1.0
                )
            )
            script.add_segment(lbl1_seg, track_name="title_x_track")

        # 8. Title Y Label Track
        if concept_y:
            script.add_track(pcc.TrackType.text, "title_y_track")
            lbl2_dur = total_duration_us - img2_start_us
            lbl2_seg = pcc.TextSegment(
                concept_y.upper(),
                pcc.Timerange(img2_start_us, lbl2_dur),
                font=font_wrapper,
                style=pcc.TextStyle(color=(0.0, 0.533, 1.0)),
                clip_settings=pcc.ClipSettings(
                    transform_x=cfg.label2_x,
                    transform_y=cfg.label2_y,
                    scale_x=1.0,
                    scale_y=1.0
                )
            )
            script.add_segment(lbl2_seg, track_name="title_y_track")

        # 9. Gapless Subtitle Text Track
        script.add_track(pcc.TrackType.text, "subtitle_track")
        opt_captions, caption_stats = optimize_caption_timeline(tagged_subtitles, total_duration_us)

        for c_info in opt_captions:
            s_scale = 1.4 if c_info["is_emphasis"] else cfg.subtitle_scale
            sub_seg = pcc.TextSegment(
                c_info["text"],
                pcc.Timerange(c_info["start_us"], c_info["duration_us"]),
                font=font_wrapper,
                style=pcc.TextStyle(color=(0.0, 0.0, 0.0)),
                clip_settings=pcc.ClipSettings(
                    transform_x=cfg.subtitle_x,
                    transform_y=cfg.subtitle_y,
                    scale_x=s_scale,
                    scale_y=s_scale
                )
            )
            try:
                script.add_segment(sub_seg, track_name="subtitle_track")
            except Exception:
                pass

        # Save draft project files
        script.save()

        # Path to generated draft folder
        draft_project_dir = os.path.join(drafts_dir, project_name)

        # 10. Post-process & patch draft_content.json for rich fonts, keyword colors & PIP effects
        patch_draft_content_json(
            draft_dir=draft_project_dir,
            font_name=cfg.font_name,
            font_resource_id=cfg.font_resource_id,
            labels=[concept_x, concept_y],
            highlight_color=cfg.highlight_color,
            add_effects=True
        )

        continuity_stats = {
            "mascot": mascot_stats,
            "caption": caption_stats,
            "mascot_clips_placed": len(mascot_clips),
            "caption_clips_placed": len(opt_captions),
            "total_duration_s": round(total_duration_us / 1_000_000.0, 2)
        }

        return draft_project_dir, continuity_stats
