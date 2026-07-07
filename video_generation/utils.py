"""Utility functions for deterministic video rendering."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def sanitize_filename(value: str, fallback: str = "medicine_video") -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in str(value or ""))
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:80] or fallback


def check_ffmpeg_available() -> bool:
    if shutil.which("ffmpeg"):
        return True
    try:
        import imageio_ffmpeg  # type: ignore

        return bool(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return False


def dependency_report() -> dict[str, bool]:
    report = {"ffmpeg": check_ffmpeg_available()}
    for package in ("moviepy", "PIL", "numpy", "transformers", "torch"):
        try:
            __import__(package)
            report[package] = True
        except Exception:
            report[package] = False
    return report


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/Nirmala.ttc"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def draw_rounded_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str = "#DDEBE4") -> None:
    draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=2)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    line_spacing: int = 8,
    max_lines: int | None = None,
) -> int:
    words = str(text or "").split()
    if not words:
        return xy[1]
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = textwrap.shorten(lines[-1], width=max(12, len(lines[-1]) - 3), placeholder="...")
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += draw.textbbox((0, 0), line, font=font)[3] + line_spacing
    return y


def run_command(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")
