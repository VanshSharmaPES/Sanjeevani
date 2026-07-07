"""Optional free/local TTS hook for Sanjeevani video guides.

The generator is intentionally useful without TTS. If a local model path is
configured later, this module can be extended without changing the video
pipeline contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import VideoGenerationSettings


@dataclass
class TTSResult:
    audio_path: str | None
    engine: str
    warnings: list[str]


def synthesize_narration(text: str, output_path: str | Path, language: str, settings: VideoGenerationSettings) -> TTSResult:
    if not settings.enable_local_tts:
        return TTSResult(None, "captions_only", [])

    model_path = settings.local_tts_model_path
    if not model_path or not model_path.exists():
        return TTSResult(None, "captions_only", [])

    try:
        # Placeholder integration point for AI4Bharat Indic Parler-TTS or another
        # local model. We deliberately avoid any network/model download here.
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except Exception as exc:
        return TTSResult(None, "captions_only", [f"Local TTS dependencies unavailable: {exc}"])

    return TTSResult(
        None,
        "captions_only",
        [
            "Local TTS model path is configured, but no model adapter is enabled yet; "
            "generated captions-only video."
        ],
    )
