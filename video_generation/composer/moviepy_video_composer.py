"""MoviePy/FFmpeg composition entry points.

The current implementation lives in video_generation.generator to keep the
existing public API stable. This module is the production boundary for the
composer package requested by the strict online asset pipeline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from video_generation.generator import _compose_video
from video_generation.schemas import MedicineVideoInput
from video_generation.services.asset_resolver import ResolvedMedicineAssets


def compose_prescription_video(
    medicine: MedicineVideoInput,
    script_lines: list[str],
    assets: ResolvedMedicineAssets,
    audio_path: str | None,
    output_path: Path,
    duration_seconds: int,
) -> np.ndarray:
    return _compose_video(medicine, script_lines, assets, audio_path, output_path, duration_seconds)
