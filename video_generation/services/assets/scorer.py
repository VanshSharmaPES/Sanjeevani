"""Candidate scoring and hard-rejection policy for medicine image assets."""

from __future__ import annotations

from dataclasses import dataclass

from .identity import MedicineIdentity, normalize_text
from .ocr_verifier import OcrVerificationResult


FULLY_TRUSTED_DOMAINS = {
    "1mg.com",
    "onemg.gumlet.io",
    "assets.1mg.com",
    "apollopharmacy.in",
    "apollo247.in",
    "images.apollo247.in",
    "netmeds.com",
    "pharmeasy.in",
    "cdn01.pharmeasy.in",
    "truemeds.in",
    "assets.truemeds.in",
    "medplusmart.com",
}

REVIEW_REQUIRED_DOMAINS = {
    "indiamart.com",
    "platinumrx.in",
    "medingen.in",
    "tradeindia.com",
    "emedicalwala.com",
    "jindalmedicalstore.in",
}

BAD_TEXT_HINTS = {
    "avatar",
    "blog",
    "doctor",
    "expert",
    "logo",
    "noimage",
    "no image",
    "placeholder",
    "profile",
    "substitute",
}


@dataclass(frozen=True)
class CandidateScore:
    source_score: float
    query_relevance_score: float
    ocr_score: float
    vision_score: float
    image_quality_score: float
    final_score: float
    review_required_source: bool
    hard_reject_reason: str = ""


def source_category(source_domain: str) -> tuple[float, bool]:
    domain = source_domain.casefold().removeprefix("www.")
    if any(domain == item or domain.endswith(f".{item}") for item in FULLY_TRUSTED_DOMAINS):
        return 1.0, False
    if any(domain == item or domain.endswith(f".{item}") for item in REVIEW_REQUIRED_DOMAINS):
        return 0.55, True
    return 0.42, True


def _query_relevance(identity: MedicineIdentity, query: str, text: str, asset_slot: str) -> float:
    query_text = normalize_text(f"{query} {text}")
    score = 0.0
    if identity.normalized_brand_name and identity.normalized_brand_name in query_text:
        score += 0.42
    if identity.strength and normalize_text(identity.strength) in query_text:
        score += 0.18
    if identity.dosage_form and normalize_text(identity.dosage_form) in query_text:
        score += 0.16
    if identity.manufacturer and normalize_text(identity.manufacturer) in query_text:
        score += 0.10
    if asset_slot == "package" and any(token in query_text for token in ("box", "pack", "package", "carton", "label")):
        score += 0.14
    if asset_slot != "package" and any(token in query_text for token in ("strip", "blister", "device", "canister", "dropper", "tube", "bottle", "inhaler")):
        score += 0.14
    return min(1.0, score)


def _vision_score(vision_result: dict | None) -> tuple[float, str]:
    if not vision_result:
        return 0.0, ""
    if vision_result.get("accepted") is False:
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier rejected candidate")
    if vision_result.get("isUnrelated") or vision_result.get("containsPerson"):
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier found unrelated or unsafe content")
    if vision_result.get("brandMatches") is False:
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier found wrong brand")
    if vision_result.get("requiresStrengthMatch") and vision_result.get("strengthMatches") is False:
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier could not confirm requested strength")
    if vision_result.get("requiresDosageFormMatch") and vision_result.get("dosageFormMatches") is False:
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier could not confirm requested dosage form")
    if not (vision_result.get("medicineNameVisible") or vision_result.get("saltVisible")):
        return 0.0, str(vision_result.get("rejectReason") or "Vision verifier could not see medicine identity text")
    score = float(vision_result.get("finalScore") or vision_result.get("confidence") or 0.0)
    return max(0.0, min(1.0, score)), ""


def score_candidate(
    identity: MedicineIdentity,
    asset_slot: str,
    source_domain: str,
    query_used: str,
    metadata_text: str,
    ocr_result: OcrVerificationResult,
    vision_result: dict | None,
    image_quality_score: float,
) -> CandidateScore:
    text = normalize_text(metadata_text)
    for hint in BAD_TEXT_HINTS:
        if hint in text:
            return CandidateScore(0, 0, 0, 0, 0, 0, True, f"Rejected bad candidate hint: {hint}")
    vision_brand_match = bool(vision_result and vision_result.get("brandMatches") is True)
    vision_strength_match = bool(vision_result and vision_result.get("strengthMatches") is True)
    vision_form_match = bool(vision_result and vision_result.get("dosageFormMatches") is True)
    if identity.normalized_brand_name and identity.normalized_brand_name not in text and not ocr_result.brand_match and not vision_brand_match:
        return CandidateScore(0, 0, 0, 0, 0, 0, True, "Brand identity is not visible in candidate metadata or OCR text")
    if identity.strength and not ocr_result.strength_match and not vision_strength_match:
        return CandidateScore(0, 0, 0, 0, 0, 0, True, "Strength identity is not verified in candidate metadata, OCR, or vision result")
    if identity.dosage_form and not ocr_result.dosage_form_match and not vision_form_match:
        return CandidateScore(0, 0, 0, 0, 0, 0, True, "Dosage form is not verified in candidate metadata, OCR, or vision result")

    source_score, review_required = source_category(source_domain)
    query_score = _query_relevance(identity, query_used, metadata_text, asset_slot)
    vision_score, vision_reject = _vision_score(vision_result)
    if vision_reject:
        return CandidateScore(source_score, query_score, ocr_result.score, vision_score, image_quality_score, 0, review_required, vision_reject)

    final_score = (
        source_score * 0.20
        + query_score * 0.15
        + ocr_result.score * 0.30
        + vision_score * 0.25
        + image_quality_score * 0.10
    )
    return CandidateScore(
        source_score=source_score,
        query_relevance_score=query_score,
        ocr_score=ocr_result.score,
        vision_score=vision_score,
        image_quality_score=image_quality_score,
        final_score=max(0.0, min(1.0, final_score)),
        review_required_source=review_required,
    )
