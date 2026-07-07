"""Typed request/response structures for Sanjeevani video guides."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


AS_PRESCRIBED = "As prescribed by doctor."


def _clean(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return " ".join(text.split()) if text else default


def _safe_instruction(value: Any) -> str:
    return _clean(value, AS_PRESCRIBED)


@dataclass
class MedicineVideoInput:
    medicine_name: str
    active_salts: str = ""
    dosage: str = AS_PRESCRIBED
    frequency: str = AS_PRESCRIBED
    timing: str = AS_PRESCRIBED
    duration: str = AS_PRESCRIBED
    doctor_notes: str = ""
    patient_name: str = "Patient"
    language: str = "en"
    route: str = ""
    form: str = ""
    package_image_url: str = ""
    product_image_url: str = ""
    human_demo_video_url: str = ""
    warnings: list[str] = field(default_factory=list)
    video_copy: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MedicineVideoInput":
        name = _clean(data.get("medicineName") or data.get("medicine_name") or data.get("medicine") or data.get("name"))
        if not name:
            raise ValueError("medicineName is required")
        warnings = data.get("warnings") or []
        if isinstance(warnings, str):
            warnings = [warnings]
        return cls(
            medicine_name=name,
            active_salts=_clean(data.get("activeSalts") or data.get("active_salts") or data.get("composition") or data.get("salts")),
            dosage=_safe_instruction(data.get("dosage") or data.get("dose")),
            frequency=_safe_instruction(data.get("frequency")),
            timing=_safe_instruction(data.get("timing") or data.get("mealRelation")),
            duration=_safe_instruction(data.get("duration")),
            doctor_notes=_clean(data.get("doctorNotes") or data.get("doctor_notes") or data.get("instruction") or data.get("notes")),
            patient_name=_clean(data.get("patientName") or data.get("patient_name"), "Patient"),
            language=_clean(data.get("language") or data.get("languageCode"), "en"),
            route=_clean(data.get("route")),
            form=_clean(data.get("form") or data.get("dosageForm")),
            package_image_url=_clean(data.get("packageImageUrl") or data.get("package_image_url")),
            product_image_url=_clean(data.get("productImageUrl") or data.get("product_image_url")),
            human_demo_video_url=_clean(data.get("humanDemoVideoUrl") or data.get("human_demo_video_url")),
            warnings=[_clean(item) for item in warnings if _clean(item)],
            video_copy={
                _clean(key): _clean(value)
                for key, value in (data.get("videoCopy") or data.get("video_copy") or {}).items()
                if _clean(key) and _clean(value)
            } if isinstance(data.get("videoCopy") or data.get("video_copy"), dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PrescriptionVideoInput:
    medicines: list[MedicineVideoInput]
    patient_name: str = "Patient"
    language: str = "en"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrescriptionVideoInput":
        patient_name = _clean(data.get("patientName") or data.get("patient_name"), "Patient")
        language = _clean(data.get("language") or data.get("languageCode"), "en")
        raw_medicines = data.get("medicines")
        if raw_medicines is None:
            raw_medicines = [data]
        if not isinstance(raw_medicines, list) or not raw_medicines:
            raise ValueError("At least one medicine is required")
        medicines = []
        for item in raw_medicines:
            if not isinstance(item, dict):
                raise ValueError("Each medicine must be an object")
            merged = {"patientName": patient_name, "language": language, **item}
            medicines.append(MedicineVideoInput.from_dict(merged))
        return cls(medicines=medicines, patient_name=patient_name, language=language)


@dataclass
class VideoGenerationResult:
    success: bool
    medicine_name: str
    video_path: str
    subtitle_path: str
    duration_seconds: int
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    @classmethod
    def failure(cls, medicine_name: str, error: str, duration_seconds: int = 0) -> "VideoGenerationResult":
        return cls(
            success=False,
            medicine_name=medicine_name,
            video_path="",
            subtitle_path="",
            duration_seconds=duration_seconds,
            error=error,
        )

    def to_api_dict(self) -> dict[str, Any]:
        video_file = Path(self.video_path) if self.video_path else None
        filename = video_file.name if video_file else ""
        version = ""
        if video_file and video_file.exists():
            version = str(video_file.stat().st_mtime_ns)
        video_url = f"/api/video-guides/file/{filename}" if filename else ""
        if video_url and version:
            video_url = f"{video_url}?v={version}"
        return {
            "success": self.success,
            "medicineName": self.medicine_name,
            "videoPath": self.video_path,
            "videoUrl": video_url,
            "subtitlePath": self.subtitle_path,
            "durationSeconds": self.duration_seconds,
            "warnings": self.warnings,
            "error": self.error,
        }
