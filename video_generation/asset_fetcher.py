"""Fetch and validate external assets for prescription video guides."""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import VideoGenerationSettings, get_settings
from .schemas import MedicineVideoInput
from .template_manager import select_template
from .utils import sanitize_filename


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024


@dataclass(frozen=True)
class VideoVisualAssets:
    package_image: Path | None
    product_image: Path | None
    human_demo_video: Path


def _load_manifest(settings: VideoGenerationSettings) -> dict[str, Any]:
    path = settings.asset_manifest_path
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_entry(medicine: MedicineVideoInput, settings: VideoGenerationSettings) -> dict[str, Any]:
    manifest = _load_manifest(settings)
    medicines = manifest.get("medicines") if isinstance(manifest.get("medicines"), dict) else {}
    entry = medicines.get(sanitize_filename(medicine.medicine_name), {})
    return entry if isinstance(entry, dict) else {}


def _template_entry(template_name: str, settings: VideoGenerationSettings) -> dict[str, Any]:
    manifest = _load_manifest(settings)
    templates = manifest.get("templates") if isinstance(manifest.get("templates"), dict) else {}
    entry = templates.get(template_name, {})
    return entry if isinstance(entry, dict) else {}


def _extension_from_url(url: str, allowed: set[str], default_ext: str) -> str:
    suffix = Path(urlparse(url).path).suffix.casefold()
    return suffix if suffix in allowed else default_ext


def _download_asset(url: str, target: Path, allowed_extensions: set[str], max_bytes: int) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported asset URL scheme for {url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_suffix(f".download{target.suffix}")
    request = urllib.request.Request(url, headers={"User-Agent": "SanjeevaniVideoAssetFetcher/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise ValueError(f"Asset is too large: {url}")
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            guessed_ext = mimetypes.guess_extension(content_type) or target.suffix
            if guessed_ext == ".jpe":
                guessed_ext = ".jpg"
            if guessed_ext.casefold() not in allowed_extensions and target.suffix.casefold() not in allowed_extensions:
                raise ValueError(f"Unsupported asset content type: {content_type or 'unknown'}")
            total = 0
            with temp_target.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Asset is too large: {url}")
                    handle.write(chunk)
    except urllib.error.URLError as exc:
        raise ValueError(f"Unable to fetch asset from {url}: {exc}") from exc
    temp_target.replace(target)
    return target


def _find_local_asset(folder: Path, stem: str, allowed_extensions: set[str]) -> Path | None:
    for suffix in allowed_extensions:
        path = folder / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def _resolve_image(kind: str, medicine: MedicineVideoInput, url: str, settings: VideoGenerationSettings) -> Path | None:
    stem = sanitize_filename(medicine.medicine_name)
    folder = settings.assets_dir / "medicine_images" / kind
    local = _find_local_asset(folder, stem, IMAGE_EXTENSIONS)
    if local:
        return local
    if url and settings.enable_asset_downloads:
        ext = _extension_from_url(url, IMAGE_EXTENSIONS, ".jpg")
        return _download_asset(url, folder / f"{stem}{ext}", IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
    return None


def _resolve_human_demo_video(medicine: MedicineVideoInput, url: str, settings: VideoGenerationSettings) -> Path | None:
    template = select_template(medicine, settings)
    folder = settings.assets_dir / "templates"
    local = _find_local_asset(folder, template.name, VIDEO_EXTENSIONS)
    if local:
        return local
    if url and settings.enable_asset_downloads:
        ext = _extension_from_url(url, VIDEO_EXTENSIONS, ".mp4")
        return _download_asset(url, folder / f"{template.name}{ext}", VIDEO_EXTENSIONS, MAX_VIDEO_BYTES)
    return None


def resolve_visual_assets(medicine: MedicineVideoInput, settings: VideoGenerationSettings | None = None) -> VideoVisualAssets:
    settings = settings or get_settings()
    medicine_entry = _manifest_entry(medicine, settings)
    template = select_template(medicine, settings)
    template_entry = _template_entry(template.name, settings)

    package_url = medicine.package_image_url or str(medicine_entry.get("packageImageUrl") or "")
    product_url = medicine.product_image_url or str(medicine_entry.get("productImageUrl") or "")
    demo_url = medicine.human_demo_video_url or str(medicine_entry.get("humanDemoVideoUrl") or template_entry.get("videoUrl") or "")

    package_image = _resolve_image("packages", medicine, package_url, settings)
    product_image = _resolve_image("products", medicine, product_url, settings)
    human_demo_video = _resolve_human_demo_video(medicine, demo_url, settings)

    if not human_demo_video:
        raise ValueError(
            f"Missing required human demonstration template video for {template.name}. "
            "Add a local approved template video or configure a template URL in "
            "video_generation/assets/asset_manifest.json."
        )

    return VideoVisualAssets(package_image=package_image, product_image=product_image, human_demo_video=human_demo_video)
