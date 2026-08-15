#!/usr/bin/env python
"""
"Dont Mix This" - Full End-to-End Pipeline: Script Generation + Gemini TTS Voiceover
"""

import os
import sys
import json
import re
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

from generator.config import load_config
from generator.llm_client import ScriptGeneratorClient
from generator.logger import GenerationLogger
from tts.tts_client import GeminiTTSClient
from tts.config import TTSConfig

console = Console(force_terminal=True, legacy_windows=False)


def main():
    console.print(Panel.fit(
        "[bold cyan]🎬 Dont Mix This — YouTube Shorts Automation Engine[/bold cyan]\n"
        "[dim]Phase 1 & 2 Grounded Script Generator[/dim] [magenta]+[/magenta] [green]Gemini 3.1 Flash TTS (\"Puck\" / 0.9 temp)[/green]",
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
    concept_x = Prompt.ask("[bold cyan]Entity X[/bold cyan] (e.g. Mjolnir)").strip()
    while not concept_x:
        concept_x = Prompt.ask("[bold red]Please enter Entity X[/bold red]").strip()

    concept_y = Prompt.ask("[bold cyan]Entity Y[/bold cyan] (e.g. Stormbreaker)").strip()
    while not concept_y:
        concept_y = Prompt.ask("[bold red]Please enter Entity Y[/bold red]").strip()

    topic = f"{concept_x} vs {concept_y}"
    safe_topic = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower()).strip('_')

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
    
    # Also save copy in outputs directory
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    out_json_path = outputs_dir / f"{safe_topic}.json"
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(approved_variant, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]✓ Script approved & saved to:[/green] [bold yellow]{saved_json_path}[/bold yellow]")

    # 7. Generate TTS Audio via Gemini 3.1 Flash TTS
    tts_audio_path = outputs_dir / f"{safe_topic}.wav"
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

    # 8. Final Success Report
    console.print(Panel(
        f"[bold green]🎉 FULL PIPELINE COMPLETE![/bold green]\n\n"
        f"[bold white]Topic:[/bold white] {topic}\n"
        f"[bold white]Selected Variant:[/bold white] [{selected_idx + 1}] {approved_variant.get('angle_name')}\n"
        f"[bold white]Audio Duration:[/bold white] [green]{audio_result.get('duration_seconds')}s[/green] ({audio_result.get('file_size_kb')} KB)\n\n"
        f"[bold yellow]Generated Files:[/bold yellow]\n"
        f"  📄 [dim]Script JSON:[/dim]  [bold]{saved_json_path}[/bold]\n"
        f"  🔊 [dim]Voiceover WAV:[/dim] [bold]{audio_result.get('output_path')}[/bold]\n\n"
        f"[bold cyan]Ready for video assembly & stickman animation![/bold cyan]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
