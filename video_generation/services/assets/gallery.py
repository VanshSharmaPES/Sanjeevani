"""Internal candidate gallery persisted for admin/debug review."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from video_generation.services.manifest_store import utc_now
from video_generation.utils import sanitize_filename


@dataclass(frozen=True)
class AssetCandidateRecord:
    image_url: str
    thumbnail_url: str
    source_page_url: str
    source_domain: str
    title: str
    snippet: str
    query_used: str
    asset_slot: str
    raw_rank: int
    provider: str
    fetched_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate: AssetCandidateRecord
    local_preview: str = ""
    ocr_text: str = ""
    ocr_score: float = 0.0
    ocr_complete: bool = False
    vision_result: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    rejection_reason: str = ""
    selected: bool = False
    review_required: bool = False
    derived_crop: bool = False


class CandidateGallery:
    def __init__(self, root: Path, medicine_slug: str, asset_slot: str) -> None:
        self.root = root
        self.medicine_slug = medicine_slug
        self.asset_slot = asset_slot
        self.gallery_id = f"{medicine_slug}_{asset_slot}"
        self.evaluations: list[CandidateEvaluation] = []

    @property
    def path(self) -> Path:
        return self.root / self.medicine_slug / f"{sanitize_filename(self.asset_slot)}.json"

    def add(self, evaluation: CandidateEvaluation) -> None:
        self.evaluations.append(evaluation)

    def mark_selected(self, image_url: str) -> None:
        updated: list[CandidateEvaluation] = []
        for evaluation in self.evaluations:
            updated.append(
                CandidateEvaluation(
                    candidate=evaluation.candidate,
                    local_preview=evaluation.local_preview,
                    ocr_text=evaluation.ocr_text,
                    ocr_score=evaluation.ocr_score,
                    ocr_complete=evaluation.ocr_complete,
                    vision_result=evaluation.vision_result,
                    score=evaluation.score,
                    rejection_reason=evaluation.rejection_reason,
                    selected=evaluation.candidate.image_url == image_url,
                    review_required=evaluation.review_required,
                    derived_crop=evaluation.derived_crop,
                )
            )
        self.evaluations = updated

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "galleryId": self.gallery_id,
            "medicineSlug": self.medicine_slug,
            "assetSlot": self.asset_slot,
            "createdAt": utc_now(),
            "candidates": [asdict(item) for item in sorted(self.evaluations, key=lambda entry: entry.score, reverse=True)],
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.path
