"""
Safe Workspace Cleanup Utility for 'Dont Mix This'
Cleans temporary build outputs and processed images while STRICTLY preserving the user's input/ directory.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def safe_cleanup_workspace(
    outputs_dir: Path = PROJECT_ROOT / "outputs",
    processed_dir: Path = PROJECT_ROOT / "assets" / "processed",
    logs_dir: Path = PROJECT_ROOT / "logs"
) -> Dict[str, any]:
    """
    Safely removes transient artifacts:
    - All subdirectories and files inside outputs/ (except .gitkeep)
    - All cropped preview files in assets/processed/ (except .gitkeep)
    - Log files in logs/
    
    STRICT SAFETY RULE:
    - The input/ folder is NEVER touched or modified.
    """
    deleted_files: List[str] = []
    deleted_folders: List[str] = []
    total_bytes_freed: int = 0

    # 1. Clean outputs/ folder
    if outputs_dir.is_dir():
        for item in outputs_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_file():
                try:
                    total_bytes_freed += item.stat().st_size
                    item.unlink()
                    deleted_files.append(f"outputs/{item.name}")
                except Exception as e:
                    pass
            elif item.is_dir():
                try:
                    # Calculate directory size
                    for root, _, files in os.walk(item):
                        for f in files:
                            fp = Path(root) / f
                            total_bytes_freed += fp.stat().st_size
                    shutil.rmtree(item)
                    deleted_folders.append(f"outputs/{item.name}/")
                except Exception as e:
                    pass

    # 2. Clean assets/processed/ folder
    if processed_dir.is_dir():
        for item in processed_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_file():
                try:
                    total_bytes_freed += item.stat().st_size
                    item.unlink()
                    deleted_files.append(f"assets/processed/{item.name}")
                except Exception as e:
                    pass

    # 3. Clean logs/ folder
    if logs_dir.is_dir():
        for item in logs_dir.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_file() and item.suffix == ".log":
                try:
                    total_bytes_freed += item.stat().st_size
                    item.unlink()
                    deleted_files.append(f"logs/{item.name}")
                except Exception as e:
                    pass

    return {
        "deleted_files_count": len(deleted_files),
        "deleted_folders_count": len(deleted_folders),
        "deleted_files": deleted_files,
        "deleted_folders": deleted_folders,
        "mb_freed": round(total_bytes_freed / (1024 * 1024), 2)
    }
