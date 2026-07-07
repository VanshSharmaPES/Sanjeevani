"""MoviePy-based deterministic prescription video generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .config import ensure_asset_directories, get_settings
from .safety_rules import SAFETY_DISCLAIMER, build_verified_script, sanitize_medicine_for_video
from .schemas import MedicineVideoInput, PrescriptionVideoInput, VideoGenerationResult
from .services.asset_resolver import AssetResolutionError, ResolvedMedicineAssets, resolve_assets_for_prescription
from .subtitle_writer import write_srt
from .template_manager import optional_ai_background, select_template
from .tts_engine import synthesize_narration
from .utils import draw_rounded_card, draw_wrapped_text, load_font, sanitize_filename


_TEMPLATE_COPY_KEYS = {
    "professional_only": "templateProfessionalOnly",
    "eye_drops": "templateEyeDrops",
    "ear_drops": "templateEarDrops",
    "nasal_spray": "templateNasalSpray",
    "inhaler": "templateInhaler",
    "ointment_topical": "templateOintmentTopical",
    "syrup_oral": "templateSyrupOral",
    "capsule_oral": "templateCapsuleOral",
    "tablet_oral": "templateTabletOral",
}


def _copy_text(medicine: MedicineVideoInput, key: str, fallback: str) -> str:
    value = medicine.video_copy.get(key) if getattr(medicine, "video_copy", None) else ""
    return str(value or fallback).strip() or fallback


def _localized_confidence_label(medicine: MedicineVideoInput, label: str) -> str:
    normalized = str(label or "").strip().casefold()
    if not normalized:
        return ""
    if "exact" in normalized and "package" in normalized:
        return _copy_text(medicine, "exactPackageMatch", label)
    if "likely" in normalized and ("dosage" in normalized or "form" in normalized):
        return _copy_text(medicine, "likelyDosageFormImage", label)
    if "generic" in normalized:
        return _copy_text(medicine, "genericDosageForm", label)
    if "review" in normalized:
        return _copy_text(medicine, "imageReviewRequired", label)
    return label


def _moviepy_imports() -> dict[str, Any]:
    try:
        from moviepy import AudioFileClip, VideoClip, VideoFileClip
    except Exception:
        from moviepy.editor import AudioFileClip, VideoClip, VideoFileClip
    return {
        "AudioFileClip": AudioFileClip,
        "VideoClip": VideoClip,
        "VideoFileClip": VideoFileClip,
    }


def _with_duration(clip: Any, duration: float) -> Any:
    return clip.with_duration(duration) if hasattr(clip, "with_duration") else clip.set_duration(duration)


def _with_audio(clip: Any, audio: Any) -> Any:
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def _resize_clip(clip: Any, size: tuple[int, int]) -> Any:
    if hasattr(clip, "resized"):
        return clip.resized(size)
    return clip.resize(size)


def _paste_contained(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int], bg: str = "#FFFFFF") -> bool:
    try:
        source = Image.open(source_path).convert("RGB")
    except Exception:
        return False
    x1, y1, x2, y2 = box
    max_w = x2 - x1
    max_h = y2 - y1
    source.thumbnail((max_w, max_h), Image.LANCZOS)
    background = Image.new("RGB", (max_w, max_h), bg)
    paste_x = (max_w - source.width) // 2
    paste_y = (max_h - source.height) // 2
    background.paste(source, (paste_x, paste_y))
    canvas.paste(background, (x1, y1))
    return True


def _paste_cover(
    canvas: Image.Image,
    source_path: Path,
    box: tuple[int, int, int, int],
    bg: str = "#FFFFFF",
    focus_x: float = 0.5,
    focus_y: float = 0.5,
) -> bool:
    try:
        source = Image.open(source_path).convert("RGB")
    except Exception:
        return False
    x1, y1, x2, y2 = box
    max_w = x2 - x1
    max_h = y2 - y1
    scale = max(max_w / max(source.width, 1), max_h / max(source.height, 1))
    resized = source.resize((max(1, int(source.width * scale)), max(1, int(source.height * scale))), Image.LANCZOS)
    overflow_x = max(0, resized.width - max_w)
    overflow_y = max(0, resized.height - max_h)
    crop_x = min(overflow_x, max(0, int(overflow_x * focus_x)))
    crop_y = min(overflow_y, max(0, int(overflow_y * focus_y)))
    cropped = resized.crop((crop_x, crop_y, crop_x + max_w, crop_y + max_h))
    background = Image.new("RGB", (max_w, max_h), bg)
    background.paste(cropped, (0, 0))
    canvas.paste(background, (x1, y1))
    return True


def _paste_product_image(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int]) -> bool:
    try:
        with Image.open(source_path) as source:
            source_w, source_h = source.size
    except Exception:
        return False
    x1, y1, x2, y2 = box
    slot_ratio = (x2 - x1) / max(y2 - y1, 1)
    source_ratio = source_w / max(source_h, 1)
    if source_ratio > slot_ratio * 1.15:
        return _paste_contained(canvas, source_path, box)
    return _paste_cover(canvas, source_path, box, focus_y=0.68)


def _draw_image_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    image_path: Path,
    fit_mode: str = "contain",
    confidence_label: str = "",
) -> None:
    small_font = load_font(15, bold=True)
    badge_font = load_font(12, bold=True)
    draw_rounded_card(draw, box, "#FFFFFF", "#CFE5DA")
    x1, y1, x2, y2 = box
    draw.text((x1 + 18, y1 + 12), label.upper(), font=small_font, fill="#6D8B7E")
    if confidence_label:
        badge_text = confidence_label.upper()
        text_box = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_w = min((text_box[2] - text_box[0]) + 18, (x2 - x1) - 36)
        badge_x2 = x2 - 18
        badge_x1 = badge_x2 - badge_w
        badge_y1 = y1 + 38
        badge_y2 = badge_y1 + 24
        badge_fill = "#E7FFF5" if "GENERIC" not in badge_text and "REVIEW" not in badge_text else "#FFF7E2"
        badge_text_fill = "#057A58" if "GENERIC" not in badge_text and "REVIEW" not in badge_text else "#A46100"
        draw.rounded_rectangle((badge_x1, badge_y1, badge_x2, badge_y2), radius=12, fill=badge_fill, outline="#CFE5DA")
        draw.text((badge_x1 + 9, badge_y1 + 5), badge_text[:38], font=badge_font, fill=badge_text_fill)
    image_box = (x1 + 12, y1 + 66, x2 - 12, y2 - 12)
    if fit_mode == "product":
        pasted = _paste_product_image(canvas, image_path, image_box)
    elif fit_mode == "cover":
        pasted = _paste_cover(canvas, image_path, image_box, focus_y=0.68)
    else:
        pasted = _paste_contained(canvas, image_path, image_box)
    if not pasted:
        raise ValueError(f"Unable to read approved image asset: {image_path}")


def _paste_demo_frame(canvas: Image.Image, frame: np.ndarray, box: tuple[int, int, int, int]) -> None:
    source = Image.fromarray(frame).convert("RGB")
    x1, y1, x2, y2 = box
    source.thumbnail((x2 - x1, y2 - y1), Image.LANCZOS)
    background = Image.new("RGB", (x2 - x1, y2 - y1), "#000000")
    background.paste(source, ((background.width - source.width) // 2, (background.height - source.height) // 2))
    canvas.paste(background, (x1, y1))


def _draw_video_frame(
    medicine: MedicineVideoInput,
    script_lines: list[str],
    assets: ResolvedMedicineAssets,
    demo_frame: np.ndarray,
) -> Image.Image:
    settings = get_settings()
    image = Image.new("RGB", (settings.width, settings.height), "#F4FBF7")
    draw = ImageDraw.Draw(image)

    small_font = load_font(17)
    template = select_template(medicine, settings)
    template_label = _copy_text(medicine, _TEMPLATE_COPY_KEYS.get(template.name, ""), template.label)
    dose_label = _copy_text(medicine, "dose", "Dose")

    draw.text((36, 26), "SANJEEVANI", font=load_font(26, bold=True), fill="#063B2B")
    draw.text((36, 58), _copy_text(medicine, "pageSubtitle", "Split-screen patient instruction video"), font=small_font, fill="#5B776C")
    draw_rounded_card(draw, (30, 94, 852, 620), "#FFFFFF", "#CFE5DA")
    draw_wrapped_text(draw, template_label, (54, 112), load_font(25, bold=True), "#063B2B", 760, max_lines=1)
    draw.text((54, 146), _copy_text(medicine, "approvedDemo", "Approved human demonstration template video"), font=small_font, fill="#557267")
    _paste_demo_frame(image, demo_frame, (54, 180, 828, 548))
    draw.rounded_rectangle((54, 562, 828, 606), radius=16, fill="#073B2A")
    draw_wrapped_text(
        draw,
        f"{medicine.medicine_name} | {dose_label}: {medicine.dosage} | {medicine.timing} | {medicine.frequency}",
        (72, 575),
        small_font,
        "#FFFFFF",
        738,
        max_lines=1,
    )
    _draw_image_card(
        image,
        draw,
        (880, 94, 1248, 342),
        _copy_text(medicine, "packageImage", "Medicine package image"),
        assets.package_image,
        confidence_label=_localized_confidence_label(medicine, assets.package_confidence_label),
    )
    product_fit_mode = (
        "contain"
        if str(assets.product_confidence_label or "").casefold() == "valid image not found"
        else "product" if template.name in {"tablet_oral", "capsule_oral"} else "contain"
    )
    _draw_image_card(
        image,
        draw,
        (880, 370, 1248, 620),
        _copy_text(medicine, "productImage", "Dosage form / strip image"),
        assets.product_image,
        fit_mode=product_fit_mode,
        confidence_label=_localized_confidence_label(medicine, assets.product_confidence_label),
    )
    draw.rounded_rectangle((30, 640, 1248, 700), radius=22, fill="#073B2A")
    draw.text((56, 654), _copy_text(medicine, "caption", "Caption"), font=small_font, fill="#9DE8C2")
    draw_wrapped_text(draw, " • ".join(script_lines[-3:]), (56, 676), small_font, "#FFFFFF", 1138, max_lines=1)
    return image


def _render_frame(frame: np.ndarray, output_path: Path) -> str:
    image = Image.fromarray(frame).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return str(output_path)


def _compose_video(medicine: MedicineVideoInput, script_lines: list[str], assets: ResolvedMedicineAssets, audio_path: str | None, output_path: Path, duration: int) -> np.ndarray:
    settings = get_settings()
    moviepy = _moviepy_imports()
    VideoClip = moviepy["VideoClip"]
    AudioFileClip = moviepy["AudioFileClip"]
    VideoFileClip = moviepy["VideoFileClip"]

    animation_fps = 8
    demo_clip = VideoFileClip(str(assets.human_demo_video))
    demo_duration = max(float(getattr(demo_clip, "duration", duration) or duration), 0.1)
    demo_last_frame_time = max(demo_duration - (1 / animation_fps), 0)

    @lru_cache(maxsize=128)
    def cached_frame(frame_index: int) -> np.ndarray:
        t = frame_index / animation_fps
        demo_time = min(t, demo_last_frame_time)
        demo_frame = demo_clip.get_frame(demo_time)
        return np.array(_draw_video_frame(medicine, script_lines, assets, demo_frame))

    def make_frame(t: float) -> np.ndarray:
        return cached_frame(int(t * animation_fps))

    first_frame = cached_frame(0)
    try:
        clip = VideoClip(frame_function=make_frame, duration=duration)
    except TypeError:
        clip = VideoClip(make_frame=make_frame, duration=duration)
    clip = clip.with_fps(settings.fps) if hasattr(clip, "with_fps") else clip.set_fps(settings.fps)

    audio = None
    if audio_path and Path(audio_path).exists():
        audio = AudioFileClip(audio_path)
        clip = _with_audio(clip, audio)

    write_kwargs = {
        "codec": "libx264",
        "fps": settings.fps,
        "preset": "medium",
        "bitrate": "3000k",
    }
    if audio:
        write_kwargs["audio_codec"] = "aac"
    else:
        write_kwargs["audio"] = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_path.with_name(f".{output_path.stem}.{uuid.uuid4().hex}.tmp{output_path.suffix}")
    try:
        clip.write_videofile(str(temp_output), **write_kwargs)
        temp_output.replace(output_path)
    finally:
        if audio:
            audio.close()
        clip.close()
        demo_clip.close()
        if temp_output.exists():
            temp_output.unlink()
    return first_frame


def generate_medicine_video(medicine: MedicineVideoInput | dict[str, Any], output_path: str | None = None) -> VideoGenerationResult:
    settings = get_settings()
    ensure_asset_directories(settings)
    try:
        if isinstance(medicine, dict):
            medicine = MedicineVideoInput.from_dict(medicine)
        medicine = sanitize_medicine_for_video(medicine)
        filename = sanitize_filename(medicine.medicine_name)
        output = Path(output_path) if output_path else settings.output_dir / f"{filename}.mp4"
        base = output.with_suffix("")
        frame_path = base.with_suffix(".png")
        subtitle_path = base.with_suffix(".srt")
        audio_path = base.with_suffix(".wav")

        script_lines = build_verified_script(medicine)
        resolved = resolve_assets_for_prescription({"patientName": medicine.patient_name, "language": medicine.language, "medicines": [medicine.to_dict()]})
        visual_assets = resolved.medicines[sanitize_filename(medicine.medicine_name)]
        write_srt(script_lines, subtitle_path, settings.duration_seconds)
        tts = synthesize_narration(" ".join(script_lines), audio_path, medicine.language, settings)

        template = select_template(medicine, settings)
        background = optional_ai_background(settings, template)
        warnings = [*list(getattr(visual_assets, "warnings", []) or []), *list(tts.warnings)]
        if background:
            warnings.append("AI background support is configured, but the deterministic template renderer is currently used.")

        first_frame = _compose_video(medicine, script_lines, visual_assets, tts.audio_path, output, settings.duration_seconds)
        _render_frame(first_frame, frame_path)
        return VideoGenerationResult(
            success=True,
            medicine_name=medicine.medicine_name,
            video_path=str(output),
            subtitle_path=str(subtitle_path),
            duration_seconds=settings.duration_seconds,
            warnings=warnings,
        )
    except Exception as exc:
        name = medicine.get("medicineName", "Unknown medicine") if isinstance(medicine, dict) else getattr(medicine, "medicine_name", "Unknown medicine")
        return VideoGenerationResult.failure(str(name), str(exc), settings.duration_seconds)


def generate_prescription_videos(
    prescription: PrescriptionVideoInput | dict[str, Any],
    output_dir: str | None = None,
) -> list[VideoGenerationResult]:
    settings = get_settings()
    if isinstance(prescription, dict):
        prescription = PrescriptionVideoInput.from_dict(prescription)
    target_dir = Path(output_dir) if output_dir else settings.output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[VideoGenerationResult] = []
    try:
        resolved_assets = resolve_assets_for_prescription(prescription)
    except AssetResolutionError as exc:
        for medicine in prescription.medicines:
            medicine_failures = [
                item for item in exc.failures
                if item.get("medicineName") in {medicine.medicine_name, None} or item.get("routeTemplate")
            ]
            if medicine_failures:
                error = "; ".join(f"{item.get('assetType')}: {item.get('stage')} - {item.get('reason')}" for item in medicine_failures)
            else:
                error = str(exc)
            results.append(VideoGenerationResult.failure(medicine.medicine_name, error, settings.duration_seconds))
        return results
    partial_failures = getattr(resolved_assets, "failures", []) or []
    for medicine in prescription.medicines:
        filename = sanitize_filename(medicine.medicine_name)
        if filename not in resolved_assets.medicines:
            medicine_failures = [
                item for item in partial_failures
                if item.get("medicineName") in {medicine.medicine_name, None} or item.get("routeTemplate")
            ]
            error = "; ".join(
                f"{item.get('assetType')}: {item.get('stage')} - {item.get('reason')}"
                for item in medicine_failures
            ) or "Required video assets were not resolved for this medicine."
            results.append(VideoGenerationResult.failure(medicine.medicine_name, error, settings.duration_seconds))
            continue
        try:
            asset = resolved_assets.medicines[filename]
            output = str(target_dir / f"{filename}.mp4")
            settings = get_settings()
            medicine = sanitize_medicine_for_video(medicine)
            base = Path(output).with_suffix("")
            frame_path = base.with_suffix(".png")
            subtitle_path = base.with_suffix(".srt")
            audio_path = base.with_suffix(".wav")
            script_lines = build_verified_script(medicine)
            write_srt(script_lines, subtitle_path, settings.duration_seconds)
            tts = synthesize_narration(" ".join(script_lines), audio_path, medicine.language, settings)
            first_frame = _compose_video(medicine, script_lines, asset, tts.audio_path, Path(output), settings.duration_seconds)
            _render_frame(first_frame, frame_path)
            results.append(
                VideoGenerationResult(
                    success=True,
                    medicine_name=medicine.medicine_name,
                    video_path=output,
                    subtitle_path=str(subtitle_path),
                    duration_seconds=settings.duration_seconds,
                    warnings=[*list(getattr(asset, "warnings", []) or []), *list(tts.warnings)],
                )
            )
        except Exception as exc:
            results.append(VideoGenerationResult.failure(medicine.medicine_name, str(exc), get_settings().duration_seconds))
    return results
