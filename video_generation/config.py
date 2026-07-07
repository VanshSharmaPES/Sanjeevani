"""Configuration helpers for local video guide generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = Path(__file__).resolve().parent
ASSET_ROOT = MODULE_ROOT / "assets"

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local")
except Exception:
    pass


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _float_env(name: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _path_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class VideoGenerationSettings:
    width: int
    height: int
    fps: int
    duration_seconds: int
    output_dir: Path
    enable_local_tts: bool
    enable_ai_video_background: bool
    local_tts_model_path: Path | None
    local_video_model_path: Path | None
    asset_manifest_path: Path | None
    asset_cache_dir: Path
    asset_gallery_dir: Path
    asset_mode: str
    pexels_api_key: str
    serpapi_api_key: str
    brave_search_api_key: str
    google_cse_api_key: str
    google_cse_id: str
    approved_image_domains: Tuple[str, ...]
    min_asset_score: float
    require_real_assets: bool
    allow_fallback_assets: bool
    enable_asset_downloads: bool
    enable_ocr_image_validation: bool
    enable_vision_image_validation: bool
    asset_validation_debug: bool
    asset_validation_min_confidence: float
    asset_validation_cache_path: Path
    asset_validation_debug_log_path: Path
    assets_dir: Path = ASSET_ROOT


def get_settings() -> VideoGenerationSettings:
    output_dir = _path_env("VIDEO_OUTPUT_DIR", ASSET_ROOT / "outputs")
    local_tts = _path_env("LOCAL_TTS_MODEL_PATH", Path("")) if os.getenv("LOCAL_TTS_MODEL_PATH") else None
    local_video = _path_env("LOCAL_VIDEO_MODEL_PATH", Path("")) if os.getenv("LOCAL_VIDEO_MODEL_PATH") else None
    asset_manifest = _path_env("ASSET_MANIFEST_PATH", Path("")) if os.getenv("ASSET_MANIFEST_PATH") else _path_env("VIDEO_ASSET_MANIFEST_PATH", ASSET_ROOT / "asset_manifest.json")
    approved_domains = tuple(
        domain.strip().casefold()
        for domain in os.getenv("APPROVED_IMAGE_DOMAINS", "").split(",")
        if domain.strip()
    )
    asset_min_confidence = _float_env(
        "ASSET_MIN_CONFIDENCE",
        _float_env("MIN_ASSET_SCORE", 0.75, minimum=0.0, maximum=1.0),
        minimum=0.0,
        maximum=1.0,
    )
    return VideoGenerationSettings(
        width=_int_env("VIDEO_OUTPUT_WIDTH", 1280, minimum=640, maximum=3840),
        height=_int_env("VIDEO_OUTPUT_HEIGHT", 720, minimum=360, maximum=2160),
        fps=_int_env("VIDEO_FPS", 24, minimum=12, maximum=60),
        duration_seconds=_int_env("VIDEO_DURATION_SECONDS", 10, minimum=8, maximum=12),
        output_dir=output_dir,
        enable_local_tts=_bool_env("ENABLE_LOCAL_TTS", True),
        enable_ai_video_background=_bool_env("ENABLE_AI_VIDEO_BACKGROUND", False),
        local_tts_model_path=local_tts,
        local_video_model_path=local_video,
        asset_manifest_path=asset_manifest,
        asset_cache_dir=_path_env("ASSET_CACHE_DIR", ASSET_ROOT / "cache"),
        asset_gallery_dir=_path_env("ASSET_GALLERY_DIR", PROJECT_ROOT / "storage" / "asset_candidate_gallery"),
        asset_mode=os.getenv("ASSET_MODE", "online_strict").strip().casefold(),
        pexels_api_key=os.getenv("PEXELS_API_KEY", "").strip(),
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", "").strip(),
        brave_search_api_key=os.getenv("BRAVE_SEARCH_API_KEY", "").strip(),
        google_cse_api_key=os.getenv("GOOGLE_CSE_API_KEY", "").strip(),
        google_cse_id=os.getenv("GOOGLE_CSE_ID", "").strip(),
        approved_image_domains=approved_domains,
        min_asset_score=asset_min_confidence,
        require_real_assets=_bool_env("REQUIRE_REAL_ASSETS", True),
        allow_fallback_assets=_bool_env("ALLOW_FALLBACK_ASSETS", False),
        enable_asset_downloads=_bool_env("ASSET_ENABLE_WEB_FETCH", _bool_env("ENABLE_VIDEO_ASSET_DOWNLOADS", True)),
        enable_ocr_image_validation=_bool_env("ASSET_ENABLE_OCR_VERIFY", True),
        enable_vision_image_validation=_bool_env("ASSET_ENABLE_VISION_VERIFY", _bool_env("ENABLE_VISION_IMAGE_VALIDATION", True)),
        asset_validation_debug=_bool_env("ASSET_VALIDATION_DEBUG", False),
        asset_validation_min_confidence=_float_env("ASSET_VALIDATION_MIN_CONFIDENCE", 0.65, minimum=0.0, maximum=1.0),
        asset_validation_cache_path=_path_env("ASSET_VALIDATION_CACHE_PATH", PROJECT_ROOT / "cache" / "asset_validation_cache.json"),
        asset_validation_debug_log_path=_path_env("ASSET_VALIDATION_DEBUG_LOG_PATH", PROJECT_ROOT / "logs" / "asset_validation_debug.jsonl"),
    )


def ensure_asset_directories(settings: VideoGenerationSettings | None = None) -> None:
    settings = settings or get_settings()
    for path in (
        settings.assets_dir / "backgrounds",
        settings.assets_dir / "templates",
        settings.assets_dir / "medicine_images" / "packages",
        settings.assets_dir / "medicine_images" / "products",
        settings.asset_cache_dir / "routes",
        settings.asset_cache_dir / "medicines",
        settings.asset_gallery_dir,
        settings.assets_dir / "placeholders",
        settings.assets_dir / "fonts",
        settings.output_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
