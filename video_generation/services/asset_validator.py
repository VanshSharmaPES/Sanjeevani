"""Validation and scoring for externally fetched video assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    score: float
    reason: str
    width: int = 0
    height: int = 0
    duration: float = 0.0


class AssetValidator:
    def __init__(self, approved_domains: tuple[str, ...], min_score: float) -> None:
        self.approved_domains = approved_domains
        self.min_score = min_score

    def source_domain(self, url: str) -> str:
        return urlparse(url).netloc.casefold().removeprefix("www.")

    def _domain_score(self, url: str, source_domain: str = "") -> float:
        if not self.approved_domains:
            return 0.12
        domain = (source_domain or self.source_domain(url)).casefold().removeprefix("www.")
        return 0.25 if any(domain == item or domain.endswith(f".{item}") for item in self.approved_domains) else -0.35

    def validate_image(self, path: Path, source_url: str, exact_query_match: bool = True, source_domain: str = "") -> ValidationResult:
        if not path.exists() or path.stat().st_size <= 0:
            return ValidationResult(False, 0.0, "Downloaded image file is empty or missing")
        try:
            with Image.open(path) as image:
                width, height = image.size
                fmt = (image.format or "").casefold()
        except Exception:
            return ValidationResult(False, 0.0, "Downloaded file is not a readable image")
        if fmt not in {"jpeg", "jpg", "png", "webp"}:
            return ValidationResult(False, 0.0, f"Unsupported image MIME/format: {fmt or 'unknown'}", width, height)
        if path.stat().st_size < 5 * 1024:
            return ValidationResult(False, 0.2, "Image file is too small to be a reliable product image", width, height)
        if width < 300 or height < 300:
            return ValidationResult(False, 0.35, "Image resolution is too low", width, height)
        aspect_penalty = -0.1 if max(width, height) / max(min(width, height), 1) > 6 else 0
        score = 0.55 + self._domain_score(source_url, source_domain) + (0.15 if exact_query_match else 0) + aspect_penalty
        score = max(0.0, min(1.0, score))
        return ValidationResult(score >= self.min_score, score, "Image accepted" if score >= self.min_score else "Image confidence below threshold", width, height)

    def validate_video(self, path: Path, source_url: str, duration: float = 0.0, width: int = 0, height: int = 0) -> ValidationResult:
        if not path.exists() or path.stat().st_size <= 0:
            return ValidationResult(False, 0.0, "Downloaded video file is empty or missing")
        if path.suffix.casefold() not in {".mp4", ".mov", ".webm"}:
            return ValidationResult(False, 0.0, "Unsupported video file type")
        score = 0.7
        if 4 <= duration <= 30:
            score += 0.15
        if width >= 640 and height >= 360:
            score += 0.15
        score = max(0.0, min(1.0, score))
        reason = "Video accepted" if score >= self.min_score else "Video confidence below threshold"
        return ValidationResult(score >= self.min_score, score, reason, width, height, duration)
