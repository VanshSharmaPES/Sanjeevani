"""OCR/visible-text verification for medicine image candidates.

The verifier uses pytesseract when it is installed. In normal local setups where
OCR binaries are not available, it still scores source/title/query text and
marks OCR as incomplete instead of pretending a verified OCR result exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

from .identity import MedicineIdentity, normalize_text


@dataclass(frozen=True)
class OcrVerificationResult:
    text: str
    score: float
    brand_match: bool
    strength_match: bool
    manufacturer_match: bool
    dosage_form_match: bool
    composition_match: bool
    wrong_brand: bool = False
    complete: bool = False
    source: str = "metadata"


def _safe_tesseract_text(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image

        return str(pytesseract.image_to_string(Image.open(path)) or "")
    except Exception:
        return ""


def _contains_or_fuzzy(needle: str, haystack: str, threshold: int = 86) -> bool:
    needle = normalize_text(needle)
    haystack = normalize_text(haystack)
    if not needle:
        return True
    if needle in haystack:
        return True
    return fuzz.partial_ratio(needle, haystack) >= threshold


def _component_match(value: str, text: str, threshold: int = 86) -> bool:
    value = normalize_text(value)
    if not value:
        return True
    return _contains_or_fuzzy(value, text, threshold)


def _strength_match(value: str, text: str) -> bool:
    value = normalize_text(value)
    text = normalize_text(text)
    if not value:
        return True
    if _contains_or_fuzzy(value, text, threshold=92):
        return True
    for amount in [token for token in value.split() if token.isdigit()]:
        if amount in text.split():
            return True
    return False


def verify_candidate_text(
    image_path: Path | None,
    identity: MedicineIdentity,
    metadata_text: str,
    enable_ocr: bool = True,
) -> OcrVerificationResult:
    extracted = _safe_tesseract_text(image_path) if enable_ocr and image_path else ""
    combined = " ".join(part for part in (extracted, metadata_text) if part).strip()
    brand_match = _component_match(identity.normalized_brand_name, combined, threshold=88)
    strength_match = _strength_match(identity.strength, combined)
    manufacturer_match = _component_match(identity.manufacturer, combined, threshold=84)
    dosage_form_match = _component_match(identity.dosage_form, combined, threshold=84)

    composition_tokens = [token for token in normalize_text(identity.composition).split() if len(token) >= 5 and not token.isdigit()]
    composition_match = True
    if composition_tokens:
        matched = sum(1 for token in composition_tokens[:4] if _contains_or_fuzzy(token, combined, threshold=85))
        composition_match = matched >= 1

    score = 0.0
    score += 0.42 if brand_match else 0.0
    score += 0.22 if strength_match else 0.0
    score += 0.14 if manufacturer_match else 0.0
    score += 0.12 if dosage_form_match else 0.0
    score += 0.10 if composition_match else 0.0
    score = max(0.0, min(1.0, score))
    return OcrVerificationResult(
        text=combined,
        score=score,
        brand_match=brand_match,
        strength_match=strength_match,
        manufacturer_match=manufacturer_match,
        dosage_form_match=dosage_form_match,
        composition_match=composition_match,
        wrong_brand=False,
        complete=bool(extracted),
        source="tesseract" if extracted else "metadata",
    )
