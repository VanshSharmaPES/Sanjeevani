"""Safe visual template selection for medicine video guides."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import VideoGenerationSettings
from .schemas import MedicineVideoInput


@dataclass(frozen=True)
class VisualTemplate:
    name: str
    label: str
    accent: str
    icon: str
    background_path: Path | None = None
    warnings: tuple[str, ...] = ()


def select_template(medicine: MedicineVideoInput, settings: VideoGenerationSettings) -> VisualTemplate:
    route_form = f"{medicine.route} {medicine.form} {medicine.medicine_name}".casefold()
    if any(term in route_form for term in ("injection", "injectable", "vial", "ampoule", "infusion")):
        return VisualTemplate("professional_only", "Healthcare professional administration", "#B45309", "HCP")
    if any(term in route_form for term in ("eye", "ophthalmic")):
        return VisualTemplate("eye_drops", "Human demonstration: applying eye drops", "#0EA5E9", "EYE")
    if any(term in route_form for term in ("ear", "otic")):
        return VisualTemplate("ear_drops", "Human demonstration: applying ear drops", "#8B5CF6", "EAR")
    if "nasal" in route_form or "nose" in route_form:
        return VisualTemplate("nasal_spray", "Human demonstration: using nasal medicine", "#06B6D4", "NASAL")
    if "inhaler" in route_form or "respule" in route_form or "inhalation" in route_form:
        return VisualTemplate("inhaler", "Human demonstration: using an inhaler", "#2563EB", "AIR")
    if any(term in route_form for term in ("cream", "ointment", "gel", "lotion", "topical")):
        return VisualTemplate("ointment_topical", "Human demonstration: applying topical medicine", "#059669", "SKIN")
    if any(term in route_form for term in ("syrup", "suspension", "solution")):
        return VisualTemplate("syrup_oral", "Human demonstration: drinking measured syrup", "#16A34A", "ML")
    if "capsule" in route_form:
        return VisualTemplate("capsule_oral", "Human demonstration: taking capsule with water", "#059669", "CAP")
    return VisualTemplate("tablet_oral", "Human demonstration: taking tablet with water", "#059669", "TAB")


def optional_ai_background(settings: VideoGenerationSettings, template: VisualTemplate) -> Path | None:
    if not settings.enable_ai_video_background:
        return None
    if not settings.local_video_model_path or not settings.local_video_model_path.exists():
        return None
    candidate = settings.assets_dir / "backgrounds" / f"{template.name}.mp4"
    return candidate if candidate.exists() else None
