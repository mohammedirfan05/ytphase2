"""
Workspace Cleanup CLI for 'Dont Mix This'
Usage: python clean.py
Cleans outputs/, assets/processed/, and logs/ while strictly preserving input/ images.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from draft.cleaner import safe_cleanup_workspace

console = Console(force_terminal=True, legacy_windows=False)


def main():
    console.print(Panel.fit(
        "[bold cyan]🧹 Dont Mix This — Safe Workspace Cleaner[/bold cyan]\n"
        "[dim]Clears temporary outputs & processed preview crops[/dim]\n"
        "[bold green]✓ STRICT SAFETY:[/bold green] [italic]Images inside 'input/' are NEVER touched.[/italic]",
        border_style="cyan"
    ))

    result = safe_cleanup_workspace()

    table = Table(title="Cleaned Artifacts Summary", show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Category", style="bold white", width=26)
    table.add_column("Items Removed", style="bold yellow", width=18)
    table.add_column("Details", style="dim", width=36)

    table.add_row(
        "Project Output Subfolders",
        f"{result['deleted_folders_count']} folders",
        ", ".join(result['deleted_folders'][:3]) + ("..." if len(result['deleted_folders']) > 3 else "") or "None"
    )
    table.add_row(
        "Transient Files & Audio",
        f"{result['deleted_files_count']} files",
        f"{result['mb_freed']} MB freed from disk"
    )
    table.add_row(
        "User Input Images",
        "[bold green]0 touched (Preserved)[/bold green]",
        "input/ directory completely untouched"
    )

    console.print(table)
    console.print(Panel(
        f"[bold green]✓ Cleanup complete![/bold green] Freed [bold yellow]{result['mb_freed']} MB[/bold yellow]. Workspace is clean.",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
