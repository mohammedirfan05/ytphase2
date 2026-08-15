"""
Image processor: Auto 1:1 square center-crop normalization
"""

import os
from pathlib import Path
from typing import Optional, List
from PIL import Image


def ensure_1to1_crop(img_path: str, cache_dir: str = "assets/processed") -> str:
    """
    Performs auto 1:1 square center-crop on an image file regardless of input dimensions.
    Returns path to cropped 1:1 image.
    """
    if not os.path.isfile(img_path):
        return img_path

    try:
        with Image.open(img_path) as img:
            w, h = img.size
            if w == h:
                return os.path.abspath(img_path)  # Already 1:1 square

            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            cropped = img.crop((left, top, right, bottom))

            os.makedirs(cache_dir, exist_ok=True)
            base_name = os.path.basename(img_path)
            cropped_filename = f"crop_1to1_{base_name}"
            out_path = os.path.abspath(os.path.join(cache_dir, cropped_filename))
            cropped.save(out_path)
            return out_path
    except Exception:
        return os.path.abspath(img_path)


def find_comparison_images(input_dir: str = "input") -> tuple[Optional[str], Optional[str]]:
    """
    Finds image1 and image2 in input directory or fallback locations.
    """
    if not os.path.isdir(input_dir):
        return None, None

    img_exts = {".png", ".jpg", ".jpeg", ".webp"}
    img1_path = None
    img2_path = None

    for prefix in ["image1", "img1", "1", "left"]:
        for ext in img_exts:
            candidate = os.path.join(input_dir, f"{prefix}{ext}")
            if os.path.isfile(candidate):
                img1_path = candidate
                break
        if img1_path:
            break

    for prefix in ["image2", "img2", "2", "right"]:
        for ext in img_exts:
            candidate = os.path.join(input_dir, f"{prefix}{ext}")
            if os.path.isfile(candidate):
                img2_path = candidate
                break
        if img2_path:
            break

    # If still not found, check any 2 images in directory
    if not img1_path or not img2_path:
        all_imgs = [os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir)) if Path(f).suffix.lower() in img_exts]
        if len(all_imgs) >= 2:
            img1_path = img1_path or all_imgs[0]
            img2_path = img2_path or all_imgs[1]
        elif len(all_imgs) == 1:
            img1_path = img1_path or all_imgs[0]

    return img1_path, img2_path
