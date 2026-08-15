#!/usr/bin/env python
"""
"Dont Mix This" - YouTube Shorts Script Generator CLI
Generates 3 high-retention 21-30s voiceover variants and saves the approved script to JSON for TTS.
"""

import os
import sys
import json
import click
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

console = Console(force_terminal=True, legacy_windows=False)


@click.command(help="Generate YouTube Shorts scripts for 'Dont Mix This' comparisons.")
@click.argument("topic", required=True)
@click.option("--variants", "-v", default=None, type=int, help="Number of script variants to generate (default: 3).")
@click.option("--model", "-m", default=None, type=str, help="Gemini model identifier (e.g. gemini-3.6-flash).")
@click.option("--duration", "-d", default=None, type=int, help="Target duration in seconds (21-30s).")
@click.option("--config-path", "-c", default="config.yaml", help="Path to custom config.yaml file.")
@click.option("--pick", "-p", default=None, type=int, help="Auto-approve specific variant number (1-3) without interactive prompt.")
def main(topic: str, variants: int, model: str, duration: int, config_path: str, pick: int):
    """Main CLI generation and approval command."""
    # 1. Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        sys.exit(1)
        
    # Apply CLI overrides
    if model:
        config.model = model
    if duration:
        config.target_duration_seconds = duration
        
    num_variants = variants or config.default_num_variants

    console.print(Panel.fit(
        f"[bold cyan]Dont Mix This - Script Generator[/bold cyan]\n"
        f"[dim]Topic:[/dim] [bold yellow]\"{topic}\"[/bold yellow] | "
        f"[dim]Model:[/dim] [green]{config.model}[/green] | "
        f"[dim]Target:[/dim] [magenta]{config.target_duration_seconds}s (~{config.words_per_second} wps)[/magenta]",
        border_style="cyan"
    ))

    # 2. Check for API key
    if not (config.gemini_api_key or os.getenv("GEMINI_API_KEY")):
        console.print(
            "\n[bold red]Error: GEMINI_API_KEY environment variable is not set.[/bold red]\n"
            "[yellow]Please set it in your .env file or shell environment:[/yellow]\n"
            "  [dim]Edit .env:[/dim]         GEMINI_API_KEY=your_api_key_here\n"
            "  [dim]Windows PowerShell:[/dim] $env:GEMINI_API_KEY=\"your_api_key_here\"\n"
        )
        sys.exit(1)

    # 3. Call LLM Generator
    with console.status("[bold green]Generating best 3 script variants with Gemini 3.6 Flash...[/bold green]", spinner="dots"):
        try:
            client = ScriptGeneratorClient(config)
            response_data = client.generate(topic, num_variants=num_variants)
        except Exception as e:
            console.print(f"\n[bold red]Generation Failed:[/bold red] {e}")
            sys.exit(1)

    # Log entire run for history
    logger = GenerationLogger(config)
    logger.log_generation_run(topic, response_data)

    # 4. Display Results in Rich Terminal UI
    variants_list = response_data.get("variants", [])
    console.print(f"\n[bold green][+] Generated {len(variants_list)} candidate variants for your review:[/bold green]\n")

    for i, var in enumerate(variants_list, 1):
        dur = var.get("estimated_duration_seconds", 0)
        wc = var.get("word_count", 0)
        validation = var.get("validation", {})
        score = validation.get("compliance_score", 100)
        dur_color = "green" if 21 <= dur <= 30 else ("yellow" if dur <= 34 else "red")
        
        console.print(Panel(
            f"[bold white]OPTION [{i}]: {var.get('angle_name', 'Script Angle')}[/bold white]\n"
            f"[dim]Duration:[/dim] [{dur_color}]{dur}s[/] ({wc} words) | "
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

    # 5. Interactive Approval Flow
    selected_idx = None
    if pick is not None:
        if 1 <= pick <= len(variants_list):
            selected_idx = pick - 1
            console.print(f"[dim]Auto-approving variant [{pick}] via --pick flag...[/dim]")
        else:
            console.print(f"[bold red]Invalid --pick option {pick}. Must be 1-{len(variants_list)}.[/bold red]")

    if selected_idx is None:
        choice = Prompt.ask(
            "\n[bold cyan]Select the best variant to approve and save (1, 2, 3), or [0/q] to skip[/bold cyan]",
            choices=[str(i) for i in range(1, len(variants_list) + 1)] + ["0", "q", "Q"],
            default="1"
        )
        if choice in ["0", "q", "Q"]:
            console.print("[yellow]No variant selected. Exiting without saving to generated_scripts/.[/yellow]")
            sys.exit(0)
        selected_idx = int(choice) - 1

    # 6. Save Approved Variant to generated_scripts/<topic>.json
    approved_variant = variants_list[selected_idx]
    saved_path = logger.save_approved_script(topic, approved_variant)

    console.print(Panel(
        f"[bold green]✓ APPROVED & SAVED FOR TTS[/bold green]\n\n"
        f"[bold white]Variant [{selected_idx + 1}]: {approved_variant.get('angle_name')}[/bold white]\n"
        f"[dim]Saved JSON:[/dim] [bold yellow]{saved_path}[/bold yellow]\n"
        f"[dim]Ready for next phase:[/dim] [cyan]Google TTS voice synthesis[/cyan]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
