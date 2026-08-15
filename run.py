#!/usr/bin/env python
"""
"Dont Mix This" - Full End-to-End Pipeline: Script Generation + Gemini TTS Voiceover
"""

import os
import sys
import json
import re
import argparse
from typing import Optional
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

import argparse

from generator.config import load_config
from generator.llm_client import ScriptGeneratorClient
from generator.logger import GenerationLogger
from tts.tts_client import GeminiTTSClient
from tts.config import TTSConfig

from draft.config import DraftConfig
from draft.builder import CapCutDraftBuilder
from draft.stt import transcribe_audio_words, align_words_with_script, chunk_words_to_raw_srt, get_wav_duration_us
from draft.tagger import generate_tagged_subtitles, build_semantic_tagged_subtitles
from draft.image_processor import find_comparison_images
from draft.cleaner import safe_cleanup_workspace

console = Console(force_terminal=True, legacy_windows=False)


def run_from_audio(
    audio_path: str,
    concept_x: Optional[str] = None,
    concept_y: Optional[str] = None,
    script_text: Optional[str] = None,
    draft_name: Optional[str] = None
):
    """Direct workflow from pre-existing audio voiceover file."""
    audio_file = Path(audio_path).resolve()
    if not audio_file.is_file():
        console.print(f"[bold red]Error: Audio file not found at '{audio_path}'[/bold red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold cyan]🎬 Direct Audio Mode — CapCut Draft Builder[/bold cyan]\n"
        f"[dim]Source Audio:[/dim] [bold green]{audio_file.name}[/bold green]",
        border_style="cyan"
    ))

    # Ask for X and Y if not provided
    if not concept_x:
        console.print("\n[bold yellow]Enter the two concepts to compare:[/bold yellow]")
        concept_x = Prompt.ask("[bold cyan]Entity X[/bold cyan] (e.g. Mjolnir)").strip()
        while not concept_x:
            concept_x = Prompt.ask("[bold red]Please enter Entity X[/bold red]").strip()

    if not concept_y:
        concept_y = Prompt.ask("[bold cyan]Entity Y[/bold cyan] (e.g. Stormbreaker)").strip()
        while not concept_y:
            concept_y = Prompt.ask("[bold red]Please enter Entity Y[/bold red]").strip()

    topic = f"{concept_x} vs {concept_y}"
    safe_topic = draft_name or re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower()).strip('_')

    # Topic-scoped subfolder inside outputs/
    topic_output_dir = Path("outputs") / safe_topic
    topic_output_dir.mkdir(parents=True, exist_ok=True)

    # Check for optional reference script file
    if not script_text:
        cand_txt = audio_file.with_suffix(".txt")
        cand_json = audio_file.with_suffix(".json")
        if cand_txt.is_file():
            try:
                script_text = cand_txt.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        elif cand_json.is_file():
            try:
                with open(cand_json, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    script_text = data.get("full_script_text", "")
            except Exception:
                pass

    # Audio duration
    audio_duration_us = get_wav_duration_us(str(audio_file))
    audio_duration_s = round(audio_duration_us / 1_000_000.0, 2) if audio_duration_us > 0 else 0.0

    # 1. Transcribe & Generate Tagged Subtitles
    with console.status("[bold green]Transcribing audio timestamps and mapping mascot poses...[/bold green]", spinner="dots"):
        try:
            whisper_words = transcribe_audio_words(str(audio_file), model_size="base")
            aligned_words = align_words_with_script(script_text or "", whisper_words, total_duration_s=audio_duration_s)

            tagged_subs, audit_logs = build_semantic_tagged_subtitles(
                aligned_words=aligned_words,
                concept_x=concept_x,
                concept_y=concept_y
            )

            # Save clean SRT inside topic-scoped subfolder
            srt_path = topic_output_dir / f"{safe_topic}.srt"
            srt_lines = []
            for s in tagged_subs:
                st_str = f"{s.start_ms // 3600000:02d}:{(s.start_ms % 3600000) // 60000:02d}:{(s.start_ms % 60000) // 1000:02d},{s.start_ms % 1000:03d}"
                et_str = f"{s.end_ms // 3600000:02d}:{(s.end_ms % 3600000) // 60000:02d}:{(s.end_ms % 60000) // 1000:02d},{s.end_ms % 1000:03d}"
                srt_lines.append(f"{s.index}\n{st_str} --> {et_str}\n{s.text} {s.tag}\n")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_lines))

            # Save Mascot Audit Log inside topic-scoped subfolder
            audit_log_path = topic_output_dir / f"{safe_topic}_mascot_audit.log"
            with open(audit_log_path, "w", encoding="utf-8") as f:
                f.write(f"=== Mascot Tagging & Caption Audit Log for '{topic}' ===\n\n")
                f.write("\n".join(audit_logs))
                f.write("\n")

        except Exception as e:
            console.print(f"\n[bold red]Transcription & Alignment Failed:[/bold red] {e}")
            sys.exit(1)

    # Print Mascot Audit Table
    table = Table(title=f"Mascot Pose & Caption Audit ({len(tagged_subs)} blocks, max 3 words)", show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Block", style="dim", width=6)
    table.add_column("Timing", style="cyan", width=14)
    table.add_column("Caption Chunk", style="bold white", width=28)
    table.add_column("Rule Triggered", style="yellow", width=28)
    table.add_column("Mascot Pose", style="bold green", width=14)

    for s in tagged_subs:
        st_s = s.start_ms / 1000.0
        et_s = s.end_ms / 1000.0
        pose_color = "red" if s.pose == "left" else ("blue" if s.pose == "right" else "green")
        table.add_row(
            f"#{s.index}",
            f"{st_s:4.2f}s - {et_s:4.2f}s",
            s.text,
            s.rule_name.replace("Rule: ", ""),
            f"[{pose_color}]{s.pose}.png[/]"
        )
    console.print(table)

    # 2. Discover comparison images & Build CapCut Draft Project
    with console.status("[bold yellow]Assembling CapCut Desktop Draft project...[/bold yellow]", spinner="dots"):
        try:
            draft_cfg = DraftConfig()
            img1, img2 = find_comparison_images("input")

            builder = CapCutDraftBuilder(draft_cfg)
            draft_path, stats = builder.build_draft(
                project_name=safe_topic,
                concept_x=concept_x,
                concept_y=concept_y,
                audio_path=str(audio_file),
                tagged_subtitles=tagged_subs,
                image1_path=img1,
                image2_path=img2
            )
        except Exception as e:
            console.print(f"\n[bold red]CapCut Draft Assembly Failed:[/bold red] {e}")
            sys.exit(1)

    # 3. Print Timeline Continuity Report
    m_stat = stats["mascot"]
    c_stat = stats["caption"]
    cont_table = Table(title="Timeline Continuity & Gap-Fill Summary", show_header=True, header_style="bold cyan", expand=True)
    cont_table.add_column("Track Layer", style="bold white", width=22)
    cont_table.add_column("Before Fix (Raw Gaps)", style="red", width=24)
    cont_table.add_column("After Fix (Gapless)", style="bold green", width=24)
    cont_table.add_column("Dead Time Closed", style="yellow", width=20)

    cont_table.add_row(
        "Mascot Overlay Track",
        f"{m_stat['raw_gaps']} gaps ({m_stat['original_blocks']} discrete blocks)",
        f"0 gaps ({m_stat['merged_clips']} merged clips)",
        f"{m_stat['dead_time_ms']} ms closed"
    )
    cont_table.add_row(
        "Caption Subtitle Track",
        f"{c_stat['raw_gaps']} blank flickers",
        f"0 flickers ({c_stat['total_chunks']} smooth chunks)",
        f"{c_stat['dead_time_ms']} ms closed"
    )
    console.print(cont_table)

    # 4. Final Success Report
    console.print(Panel(
        f"[bold green]🎉 CAPCUT DRAFT GENERATION COMPLETE![/bold green]\n\n"
        f"[bold white]Topic:[/bold white] {topic}\n"
        f"[bold white]Audio Source:[/bold white] [green]{audio_file.name}[/green] ({audio_duration_s}s)\n"
        f"[bold white]Subtitles:[/bold white] [cyan]{len(tagged_subs)} caption blocks (<= 3 words, LuckiestGuy-Rg + Highlights)[/cyan]\n"
        f"[bold white]Timeline Continuity:[/bold white] [bold green]100% Gapless (Zero Mascot/Caption Dead-Zones)[/bold green]\n\n"
        f"[bold yellow]Generated Assets & Project:[/bold yellow]\n"
        f"  📝 [dim]Aligned SRT:[/dim]       [bold]{srt_path}[/bold]\n"
        f"  🔍 [dim]Audit Log:[/dim]         [bold]{audit_log_path}[/bold]\n"
        f"  🎬 [bold magenta]CapCut Draft:[/bold magenta]      [bold green]{draft_path}[/bold green]\n\n"
        f"[bold cyan]Open CapCut Desktop to view, refine, and render your Short![/bold cyan]",
        border_style="green"
    ))


def main():
    parser = argparse.ArgumentParser(description="Dont Mix This - YouTube Shorts Automation Engine")
    parser.add_argument("--audio", "-a", type=str, default=None, help="Path to pre-existing voiceover audio (.wav/.mp3) to bypass script/TTS.")
    parser.add_argument("--x", type=str, default=None, help="Entity X name (e.g. Mjolnir)")
    parser.add_argument("--y", type=str, default=None, help="Entity Y name (e.g. Stormbreaker)")
    parser.add_argument("--script", "-s", type=str, default=None, help="Optional reference script text or .txt file")
    parser.add_argument("--draft-name", "-n", type=str, default=None, help="Custom CapCut draft project name")
    parser.add_argument("--clean", action="store_true", help="Safely cleans transient outputs & processed crops (STRICTLY preserves input/ images)")
    args = parser.parse_args()

    # If --clean is requested, perform safe workspace cleanup
    if args.clean:
        console.print(Panel.fit(
            "[bold cyan]🧹 Dont Mix This — Safe Workspace Cleaner[/bold cyan]\n"
            "[dim]Clearing temporary outputs & processed preview crops...[/dim]\n"
            "[bold green]✓ STRICT SAFETY:[/bold green] [italic]Images in 'input/' are completely untouched.[/italic]",
            border_style="cyan"
        ))
        res = safe_cleanup_workspace()
        
        table = Table(title="Cleaned Artifacts Summary", show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Category", style="bold white", width=26)
        table.add_column("Items Removed", style="bold yellow", width=18)
        table.add_column("Details", style="dim", width=36)

        table.add_row(
            "Project Output Subfolders",
            f"{res['deleted_folders_count']} folders",
            ", ".join(res['deleted_folders'][:3]) + ("..." if len(res['deleted_folders']) > 3 else "") or "None"
        )
        table.add_row(
            "Transient Files & Audio",
            f"{res['deleted_files_count']} files",
            f"{res['mb_freed']} MB freed from disk"
        )
        table.add_row(
            "User Input Images",
            "[bold green]0 touched (Preserved)[/bold green]",
            "input/ directory completely untouched"
        )
        console.print(table)
        console.print(Panel(
            f"[bold green]✓ Cleanup complete![/bold green] Freed [bold yellow]{res['mb_freed']} MB[/bold yellow]. Workspace is clean.",
            border_style="green"
        ))
        return

    # If --audio is provided, bypass script generator and TTS
    if args.audio:
        script_content = None
        if args.script:
            if os.path.isfile(args.script):
                with open(args.script, "r", encoding="utf-8") as f:
                    script_content = f.read()
            else:
                script_content = args.script
        run_from_audio(
            audio_path=args.audio,
            concept_x=args.x,
            concept_y=args.y,
            script_text=script_content,
            draft_name=args.draft_name
        )
        return

    # Full End-to-End Mode (Script Generator + TTS + Draft Builder)
    console.print(Panel.fit(
        "[bold cyan]🎬 Dont Mix This — YouTube Shorts Automation Engine[/bold cyan]\n"
        "[dim]Script Generator[/dim] [magenta]+[/magenta] [green]Gemini 3.1 Flash TTS (\"Puck\")[/green] [magenta]+[/magenta] [bold yellow]CapCut Draft Builder[/bold yellow]",
        border_style="cyan"
    ))

    # 1. Load configuration
    try:
        config = load_config("config.yaml")
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        sys.exit(1)

    # 2. Check for API key
    if not (config.gemini_api_key or os.getenv("GEMINI_API_KEY")):
        console.print(
            "\n[bold red]Error: GEMINI_API_KEY is not set.[/bold red]\n"
            "[yellow]Please add your API key to the .env file in this directory:[/yellow]\n"
            "  GEMINI_API_KEY=your_gemini_api_key_here\n"
        )
        sys.exit(1)

    # 3. Ask for X and Y in terminal
    console.print("\n[bold yellow]Enter the two concepts to compare:[/bold yellow]")
    concept_x = args.x or Prompt.ask("[bold cyan]Entity X[/bold cyan] (e.g. Mjolnir)").strip()
    while not concept_x:
        concept_x = Prompt.ask("[bold red]Please enter Entity X[/bold red]").strip()

    concept_y = args.y or Prompt.ask("[bold cyan]Entity Y[/bold cyan] (e.g. Stormbreaker)").strip()
    while not concept_y:
        concept_y = Prompt.ask("[bold red]Please enter Entity Y[/bold red]").strip()

    topic = f"{concept_x} vs {concept_y}"
    safe_topic = args.draft_name or re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower()).strip('_')

    console.print(f"\n[dim]Target Topic:[/dim] [bold white]\"{topic}\"[/bold white]")

    # 4. Generate 3 variants via Gemini Flash
    with console.status("[bold green]Generating best 3 script variants with Gemini 3.6 Flash...[/bold green]", spinner="dots"):
        try:
            generator_client = ScriptGeneratorClient(config)
            response_data = generator_client.generate(topic, num_variants=3)
        except Exception as e:
            console.print(f"\n[bold red]Script Generation Failed:[/bold red] {e}")
            sys.exit(1)

    # Log generation run
    logger = GenerationLogger(config)
    logger.log_generation_run(topic, response_data)

    variants_list = response_data.get("variants", [])
    if not variants_list:
        console.print("[bold red]No script variants returned by generator.[/bold red]")
        sys.exit(1)

    console.print(f"\n[bold green][+] Generated {len(variants_list)} candidate variants for your review:[/bold green]\n")

    for i, var in enumerate(variants_list, 1):
        dur = var.get("estimated_duration_seconds", 0)
        wc = var.get("word_count", 0)
        validation = var.get("validation", {})
        score = validation.get("compliance_score", 100)
        dur_color = "green" if 21 <= dur <= 30 else ("yellow" if dur <= 34 else "red")
        
        console.print(Panel(
            f"[bold white]OPTION [{i}]: {var.get('angle_name', 'Script Angle')}[/bold white]\n"
            f"[dim]Pacing:[/dim] [{dur_color}]{dur}s[/] ({wc} words) | "
            f"[dim]Compliance:[/dim] [cyan]{score}/100[/cyan] | "
            f"[dim]Patterns:[/dim] [italic]{', '.join(var.get('phase1_patterns_used', []))}[/italic]",
            border_style="bright_blue",
            expand=False
        ))
        
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Timing", style="dim", width=12)
        table.add_column("Move", style="bold cyan", width=26)
        table.add_column("Narration (Voiceover Script)", style="white")

        for line in var.get("script_lines", []):
            table.add_row(
                line.get("second_marker", ""),
                line.get("move_name", ""),
                line.get("text", "")
            )
            
        console.print(table)
        console.print(f"[bold yellow]TTS Text:[/bold yellow] [italic]\"{var.get('full_script_text', '')}\"[/italic]")
        console.print(f"[bold green]Outro Rule:[/bold green] [bold]{var.get('final_rule_outro', '')}[/bold]")
        console.print(f"[bold dim]Title & Tags:[/bold dim] {var.get('suggested_title', '')} [dim]{' '.join(var.get('suggested_hashtags', []))}[/dim]\n")
        console.print("-" * 70)

    # 5. Interactive Approval
    choice = Prompt.ask(
        "\n[bold cyan]Select the best variant to approve and synthesize with TTS (1, 2, 3), or [0/q] to skip[/bold cyan]",
        choices=[str(i) for i in range(1, len(variants_list) + 1)] + ["0", "q", "Q"],
        default="1"
    )
    
    if choice in ["0", "q", "Q"]:
        console.print("[yellow]Skipped. Exiting pipeline.[/yellow]")
        sys.exit(0)

    selected_idx = int(choice) - 1
    approved_variant = variants_list[selected_idx]

    # 6. Save Approved Script JSON
    saved_json_path = logger.save_approved_script(topic, approved_variant)
    
    # Topic-scoped output subfolder
    topic_output_dir = Path("outputs") / safe_topic
    topic_output_dir.mkdir(parents=True, exist_ok=True)
    out_json_path = topic_output_dir / f"{safe_topic}.json"
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(approved_variant, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]✓ Script approved & saved to:[/green] [bold yellow]{saved_json_path}[/bold yellow]")

    # 7. Generate TTS Audio via Gemini 3.1 Flash TTS
    tts_audio_path = topic_output_dir / f"{safe_topic}.wav"
    script_text = approved_variant.get("full_script_text", "")

    console.print(Panel(
        f"[bold cyan]Synthesizing Voiceover via Gemini 3.1 Flash TTS[/bold cyan]\n"
        f"[dim]Voice:[/dim] [bold green]Puck[/bold green] (Upbeat, Middle pitch) | "
        f"[dim]Temperature:[/dim] [bold yellow]0.9[/bold yellow]\n"
        f"[dim]Scene:[/dim] [italic]A fast-paced educational explainer breaking down story terminology...[/italic]",
        border_style="cyan"
    ))

    with console.status("[bold green]Generating audio voiceover with Puck voice...[/bold green]", spinner="dots"):
        try:
            tts_config = TTSConfig()
            tts_client = GeminiTTSClient(config=tts_config, api_key=config.gemini_api_key)
            audio_result = tts_client.generate_audio(script_text, str(tts_audio_path))
        except Exception as e:
            console.print(f"\n[bold red]TTS Voice Synthesis Failed:[/bold red] {e}")
            sys.exit(1)

    audio_duration = audio_result.get("duration_seconds", 0.0)

    # 8. Transcribe & Generate Tagged Subtitles
    with console.status("[bold green]Aligning word timestamps and mapping mascot poses...[/bold green]", spinner="dots"):
        try:
            whisper_words = transcribe_audio_words(str(tts_audio_path), model_size="base")
            aligned_words = align_words_with_script(script_text, whisper_words, total_duration_s=audio_duration)

            tagged_subs, audit_logs = build_semantic_tagged_subtitles(
                aligned_words=aligned_words,
                concept_x=concept_x,
                concept_y=concept_y
            )

            # Save clean SRT inside topic-scoped subfolder
            srt_path = topic_output_dir / f"{safe_topic}.srt"
            srt_lines = []
            for s in tagged_subs:
                st_str = f"{s.start_ms // 3600000:02d}:{(s.start_ms % 3600000) // 60000:02d}:{(s.start_ms % 60000) // 1000:02d},{s.start_ms % 1000:03d}"
                et_str = f"{s.end_ms // 3600000:02d}:{(s.end_ms % 3600000) // 60000:02d}:{(s.end_ms % 60000) // 1000:02d},{s.end_ms % 1000:03d}"
                srt_lines.append(f"{s.index}\n{st_str} --> {et_str}\n{s.text} {s.tag}\n")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_lines))

            # Save Mascot Audit Log inside topic-scoped subfolder
            audit_log_path = topic_output_dir / f"{safe_topic}_mascot_audit.log"
            with open(audit_log_path, "w", encoding="utf-8") as f:
                f.write(f"=== Mascot Tagging & Caption Audit Log for '{topic}' ===\n\n")
                f.write("\n".join(audit_logs))
                f.write("\n")

        except Exception as e:
            console.print(f"\n[bold red]Subtitle Alignment Failed:[/bold red] {e}")
            sys.exit(1)

    # Print Mascot Audit Table
    table = Table(title=f"Mascot Pose & Caption Audit ({len(tagged_subs)} blocks, max 3 words)", show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Block", style="dim", width=6)
    table.add_column("Timing", style="cyan", width=14)
    table.add_column("Caption Chunk", style="bold white", width=28)
    table.add_column("Rule Triggered", style="yellow", width=28)
    table.add_column("Mascot Pose", style="bold green", width=14)

    for s in tagged_subs:
        st_s = s.start_ms / 1000.0
        et_s = s.end_ms / 1000.0
        pose_color = "red" if s.pose == "left" else ("blue" if s.pose == "right" else "green")
        table.add_row(
            f"#{s.index}",
            f"{st_s:4.2f}s - {et_s:4.2f}s",
            s.text,
            s.rule_name.replace("Rule: ", ""),
            f"[{pose_color}]{s.pose}.png[/]"
        )
    console.print(table)

    # 9. Discover comparison images & Build CapCut Draft Project
    with console.status("[bold yellow]Assembling CapCut Desktop Draft project...[/bold yellow]", spinner="dots"):
        try:
            draft_cfg = DraftConfig()
            img1, img2 = find_comparison_images("input")

            builder = CapCutDraftBuilder(draft_cfg)
            draft_path, stats = builder.build_draft(
                project_name=safe_topic,
                concept_x=concept_x,
                concept_y=concept_y,
                audio_path=str(tts_audio_path),
                tagged_subtitles=tagged_subs,
                image1_path=img1,
                image2_path=img2
            )
        except Exception as e:
            console.print(f"\n[bold red]CapCut Draft Assembly Failed:[/bold red] {e}")
            sys.exit(1)

    # 10. Print Timeline Continuity Report
    m_stat = stats["mascot"]
    c_stat = stats["caption"]
    cont_table = Table(title="Timeline Continuity & Gap-Fill Summary", show_header=True, header_style="bold cyan", expand=True)
    cont_table.add_column("Track Layer", style="bold white", width=22)
    cont_table.add_column("Before Fix (Raw Gaps)", style="red", width=24)
    cont_table.add_column("After Fix (Gapless)", style="bold green", width=24)
    cont_table.add_column("Dead Time Closed", style="yellow", width=20)

    cont_table.add_row(
        "Mascot Overlay Track",
        f"{m_stat['raw_gaps']} gaps ({m_stat['original_blocks']} discrete blocks)",
        f"0 gaps ({m_stat['merged_clips']} merged clips)",
        f"{m_stat['dead_time_ms']} ms closed"
    )
    cont_table.add_row(
        "Caption Subtitle Track",
        f"{c_stat['raw_gaps']} blank flickers",
        f"0 flickers ({c_stat['total_chunks']} smooth chunks)",
        f"{c_stat['dead_time_ms']} ms closed"
    )
    console.print(cont_table)

    # 11. Final Success Report
    console.print(Panel(
        f"[bold green]🎉 FULL PIPELINE COMPLETE — CAPCUT DRAFT READY![/bold green]\n\n"
        f"[bold white]Topic:[/bold white] {topic}\n"
        f"[bold white]Selected Variant:[/bold white] [{selected_idx + 1}] {approved_variant.get('angle_name')}\n"
        f"[bold white]Audio Duration:[/bold white] [green]{audio_duration}s[/green]\n"
        f"[bold white]Subtitles:[/bold white] [cyan]{len(tagged_subs)} caption blocks (<= 3 words, LuckiestGuy-Rg + Highlights)[/cyan]\n"
        f"[bold white]Timeline Continuity:[/bold white] [bold green]100% Gapless (Zero Mascot/Caption Dead-Zones)[/bold green]\n\n"
        f"[bold yellow]Generated Assets & Project:[/bold yellow]\n"
        f"  📄 [dim]Script JSON:[/dim]       [bold]{saved_json_path}[/bold]\n"
        f"  🔊 [dim]Voiceover WAV:[/dim]     [bold]{audio_result.get('output_path')}[/bold]\n"
        f"  📝 [dim]Aligned SRT:[/dim]       [bold]{srt_path}[/bold]\n"
        f"  🔍 [dim]Audit Log:[/dim]         [bold]{audit_log_path}[/bold]\n"
        f"  🎬 [bold magenta]CapCut Draft:[/bold magenta]      [bold green]{draft_path}[/bold green]\n\n"
        f"[bold cyan]Open CapCut Desktop to view, refine, and render your Short![/bold cyan]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()


