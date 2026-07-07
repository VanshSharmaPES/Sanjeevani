"""Read/write cache manifest for resolved video assets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from video_generation.config import VideoGenerationSettings, get_settings


@dataclass(frozen=True)
class AssetRecord:
    asset_type: str
    local_path: str
    source_url: str
    provider: str
    source_domain: str
    confidence_score: float
    fetched_at: str
    approval_status: str = "auto_resolved"
    medicine_name: str = ""
    medicine_slug: str = ""
    route_template: str = ""
    gallery_id: str = ""
    ocr_text: str = ""
    vision_result: dict[str, Any] | None = None
    derived_crop: bool = False
    review_required: bool = False
    refreshed_at: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManifestStore:
    def __init__(self, settings: VideoGenerationSettings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.asset_manifest_path:
            raise ValueError("ASSET_MANIFEST_PATH is not configured")
        self.path = self.settings.asset_manifest_path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "assets": {}, "medicines": {}, "templates": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "assets": {}, "medicines": {}, "templates": {}}
        if not isinstance(data, dict):
            return {"version": 1, "assets": {}, "medicines": {}, "templates": {}}
        data.setdefault("version", 1)
        data.setdefault("assets", {})
        data.setdefault("medicines", {})
        data.setdefault("templates", {})
        return data

    def write(self, manifest: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def get_asset(self, key: str) -> AssetRecord | None:
        raw = self.read().get("assets", {}).get(key)
        if not isinstance(raw, dict):
            return None
        local_path = raw.get("local_path")
        if not local_path or not Path(str(local_path)).exists():
            return None
        try:
            return AssetRecord(**raw)
        except TypeError:
            return None

    def upsert_asset(self, key: str, record: AssetRecord, force_refresh: bool = False) -> None:
        manifest = self.read()
        existing = manifest["assets"].get(key)
        if existing and existing.get("approval_status") == "approved" and not force_refresh:
            return
        manifest["assets"][key] = asdict(record)
        self.write(manifest)
