"""Deterministic safety rules for patient video guides."""

from __future__ import annotations

from dataclasses import replace

from .schemas import AS_PRESCRIBED, MedicineVideoInput


SAFETY_DISCLAIMER = "Follow your doctor's prescription."
DO_NOT_CHANGE_DOSE = "Do not change dosage without medical advice."
PROFESSIONAL_ADMINISTRATION = "Administer only by a qualified healthcare professional."

_INJECTION_TERMS = {"injection", "injectable", "iv", "intravenous", "im", "vial", "ampoule", "infusion"}


def _copy_text(medicine: MedicineVideoInput, key: str, fallback: str) -> str:
    value = medicine.video_copy.get(key) if getattr(medicine, "video_copy", None) else ""
    return str(value or fallback).strip() or fallback


def is_injection_like(medicine: MedicineVideoInput) -> bool:
    text = f"{medicine.route} {medicine.form} {medicine.medicine_name}".casefold()
    return any(term in text for term in _INJECTION_TERMS)


def sanitize_medicine_for_video(medicine: MedicineVideoInput) -> MedicineVideoInput:
    follow_prescription = _copy_text(medicine, "followPrescription", SAFETY_DISCLAIMER)
    do_not_change_dose = _copy_text(medicine, "noDoseChange", DO_NOT_CHANGE_DOSE)
    professional_administration = _copy_text(medicine, "professionalAdministration", PROFESSIONAL_ADMINISTRATION)
    as_prescribed = _copy_text(medicine, "asPrescribed", AS_PRESCRIBED)
    warnings = [item for item in medicine.warnings if item]
    if follow_prescription not in warnings:
        warnings.append(follow_prescription)
    if do_not_change_dose not in warnings:
        warnings.append(do_not_change_dose)
    doctor_notes = medicine.doctor_notes
    if is_injection_like(medicine):
        doctor_notes = professional_administration
        if professional_administration not in warnings:
            warnings.insert(0, professional_administration)
    return replace(
        medicine,
        dosage=medicine.dosage or as_prescribed,
        timing=medicine.timing or as_prescribed,
        frequency=medicine.frequency or as_prescribed,
        duration=medicine.duration or as_prescribed,
        doctor_notes=doctor_notes,
        warnings=warnings,
    )


def build_verified_script(medicine: MedicineVideoInput) -> list[str]:
    medicine = sanitize_medicine_for_video(medicine)
    label_medicine = _copy_text(medicine, "medicine", "Medicine")
    label_active = _copy_text(medicine, "activeIngredients", "Active ingredients")
    label_dose = _copy_text(medicine, "dose", "Dose")
    label_timing = _copy_text(medicine, "timing", "Timing")
    label_frequency = _copy_text(medicine, "frequency", "Frequency")
    label_duration = _copy_text(medicine, "duration", "Duration")
    label_note = _copy_text(medicine, "doctorNote", "Doctor note")
    follow_prescription = _copy_text(medicine, "followPrescription", SAFETY_DISCLAIMER)
    lines = [
        f"{label_medicine}: {medicine.medicine_name}",
    ]
    if medicine.active_salts:
        lines.append(f"{label_active}: {medicine.active_salts}")
    lines.extend([
        f"{label_dose}: {medicine.dosage}",
        f"{label_timing}: {medicine.timing}",
        f"{label_frequency}: {medicine.frequency}",
        f"{label_duration}: {medicine.duration}",
    ])
    if medicine.doctor_notes:
        lines.append(f"{label_note}: {medicine.doctor_notes}")
    lines.append(follow_prescription)
    return lines


def narration_text(medicine: MedicineVideoInput) -> str:
    return " ".join(build_verified_script(medicine))
