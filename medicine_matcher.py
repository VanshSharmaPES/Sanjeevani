"""Deterministic medicine-profile normalization and safety matching.

This module intentionally contains no AI or fuzzy-name matching. Alternate
candidates are eligible only when composition, dosage form, route, and release
type agree after conservative normalization.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


_SPACE_RE = re.compile(r"\s+")
_STRENGTH_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>mcg|ug|mg|gm|g|kg|ml|l|%|iu|units?)"
    r"(?:\s*/\s*(?:(?P<per_value>\d+(?:\.\d+)?)\s*)?"
    r"(?P<per_unit>mcg|ug|mg|gm|g|kg|ml|l|%|iu|units?))?",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = value.replace("µ", "u").replace("μ", "u")
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9%./+()-]+", " ", value)
    return _SPACE_RE.sub(" ", value).strip()


def _normalize_number(value: str) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else format(number, "g")


def _normalize_unit(unit: str) -> str:
    aliases = {
        "ug": "mcg", "gm": "g", "unit": "units", "iu": "iu",
    }
    unit = unit.casefold()
    return aliases.get(unit, unit)


def _normalize_strength(match: re.Match[str]) -> str:
    result = f"{_normalize_number(match.group('value'))}{_normalize_unit(match.group('unit'))}"
    if match.group("per_unit"):
        per_value = _normalize_number(match.group("per_value") or "1")
        result += f"/{per_value}{_normalize_unit(match.group('per_unit'))}"
    return result


def normalize_composition(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\b(ip|bp|usp|ph eur)\b", "", value)
    value = _STRENGTH_RE.sub(_normalize_strength, value)
    value = re.sub(r"\s*\+\s*", " + ", value)
    return _SPACE_RE.sub(" ", value).strip(" +")


def _split_composition(composition: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in composition:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "+" and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def parse_composition(composition: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for raw_part in _split_composition(str(composition or "")):
        part = normalize_composition(raw_part)
        strength_match = _STRENGTH_RE.search(part)
        strength = _normalize_strength(strength_match) if strength_match else ""
        ingredient = part
        if strength_match:
            ingredient = (part[:strength_match.start()] + part[strength_match.end():]).strip()
        ingredient = re.sub(r"[()]", " ", ingredient)
        ingredient = re.sub(r"\b(ip|bp|usp|eq(?:uivalent)? to|each tablet contains)\b", " ", ingredient)
        ingredient = _SPACE_RE.sub(" ", ingredient).strip(" -.,")
        if ingredient:
            parsed.append({
                "ingredient": ingredient,
                "strength": strength or None,
                "hasStrength": bool(strength),
            })
    return sorted(parsed, key=lambda item: (item["ingredient"], item["strength"] or ""))


def build_composition_key(composition: str) -> str:
    return "|".join(
        f"{part['ingredient']}@{part['strength'] or '?'}"
        for part in parse_composition(composition)
    )


def build_ingredient_key(composition: str) -> str:
    return "|".join(part["ingredient"] for part in parse_composition(composition))


def detect_dosage_form(name: str, pack_size_label: str) -> str:
    text = normalize_text(f"{name} {pack_size_label}")
    patterns = [
        ("powder_for_injection", r"\bpowder for injection\b"),
        ("eye_drop", r"\b(eye|ophthalmic) drops?\b"),
        ("ear_drop", r"\b(ear|otic) drops?\b"),
        ("nasal_drop", r"\b(nasal|nose) drops?\b"),
        ("oral_suspension", r"\boral suspension\b"),
        ("dry_syrup", r"\bdry syrup\b"),
        ("oral_solution", r"\boral solution\b"),
        ("inhalation", r"\b(inhaler|rotacaps?|respules?|inhalation)\b"),
        ("injection", r"\b(injections?|vials?|ampoules?|infusions?)\b"),
        ("suspension", r"\bsuspensions?\b"),
        ("syrup", r"\bsyrups?\b"),
        ("capsule", r"\bcapsules?\b"),
        ("tablet", r"\b(tablets?|tabs?)\b"),
        ("ointment", r"\bointments?\b"),
        ("cream", r"\bcreams?\b"),
        ("lotion", r"\blotions?\b"),
        ("gel", r"\bgels?\b"),
        ("spray", r"\bsprays?\b"),
    ]
    for form, pattern in patterns:
        if re.search(pattern, text):
            return form
    return "unknown"


def detect_route(dosage_form: str, name: str, pack_size_label: str) -> str:
    route_map = {
        "tablet": "oral", "capsule": "oral", "syrup": "oral",
        "suspension": "oral", "oral_suspension": "oral",
        "dry_syrup": "oral", "oral_solution": "oral",
        "injection": "parenteral", "powder_for_injection": "parenteral",
        "eye_drop": "ophthalmic", "ear_drop": "otic", "nasal_drop": "nasal",
        "cream": "topical", "ointment": "topical", "gel": "topical",
        "lotion": "topical", "spray": "topical", "inhalation": "inhalation",
    }
    return route_map.get(dosage_form, "unknown")


def detect_release_type(name: str, pack_size_label: str) -> str:
    text = normalize_text(f"{name} {pack_size_label}")
    named_patterns = [
        ("effervescent", r"\beffervescent\b"),
        ("chewable", r"\bchewable\b"),
        ("sr", r"\bsustained release\b"),
        ("cr", r"\bcontrolled release\b"),
        ("er", r"\bextended release\b"),
        ("pr", r"\bprolonged release\b"),
        ("mr", r"\bmodified release\b"),
        ("dt", r"\bdispersible\b"),
        ("md", r"\b(mouth|orally) dissolving\b"),
        ("od", r"\bonce daily\b"),
    ]
    for release, pattern in named_patterns:
        if re.search(pattern, text):
            return release
    for release in ("sr", "xr", "cr", "er", "pr", "mr", "dt", "md", "od"):
        if re.search(rf"\b{release}\b", text):
            return release
    return "normal"


def detect_formulation_variant(name: str, pack_size_label: str) -> str:
    text = normalize_text(f"{name} {pack_size_label}")
    if re.search(r"\b(advance|rapid|fast|optizorb|quick|quickgel)\b", text):
        return "fast_absorption"
    return "normal"


def build_medicine_profile(row: dict) -> dict:
    name = str(row.get("name") or row.get("medicineName") or "").strip()
    composition = str(row.get("composition") or row.get("activeSalts") or "").strip()
    unit = str(row.get("unit") or row.get("pack_size_label") or "").strip()
    dosage_form = str(row.get("dosage_form") or "") or detect_dosage_form(name, unit)
    return {
        **row,
        "name": name,
        "composition": composition,
        "unit": unit,
        "composition_key": str(row.get("composition_key") or "") or build_composition_key(composition),
        "ingredient_key": str(row.get("ingredient_key") or "") or build_ingredient_key(composition),
        "dosage_form": dosage_form,
        "route": str(row.get("route") or "") or detect_route(dosage_form, name, unit),
        "release_type": str(row.get("release_type") or "") or detect_release_type(name, unit),
        "formulation_variant": str(row.get("formulation_variant") or "") or detect_formulation_variant(name, unit),
        "has_missing_strength": any(not p["hasStrength"] for p in parse_composition(composition)),
    }


def compare_medicine_profiles(selected: dict, candidate: dict) -> dict:
    selected = build_medicine_profile(selected)
    candidate = build_medicine_profile(candidate)
    checks = {
        "compositionMatch": bool(selected["composition_key"]) and selected["composition_key"] == candidate["composition_key"],
        "formMatch": selected["dosage_form"] != "unknown" and selected["dosage_form"] == candidate["dosage_form"],
        "routeMatch": selected["route"] != "unknown" and selected["route"] == candidate["route"],
        "releaseMatch": selected["release_type"] == candidate["release_type"],
        "formulationMatch": selected["formulation_variant"] == candidate["formulation_variant"],
    }
    reasons = []
    if checks["compositionMatch"]:
        reasons.extend(["Same active ingredient composition", "Same strength"])
    if checks["formMatch"]:
        reasons.append("Same dosage form")
    if checks["routeMatch"]:
        reasons.append("Same route")
    if checks["releaseMatch"]:
        reasons.append("Same release type")
    if checks["formulationMatch"]:
        reasons.append("Same formulation variant")
    block_reasons = [label for key, label in {
        "compositionMatch": "Composition or strength differs",
        "formMatch": "Dosage form differs or is unknown",
        "routeMatch": "Route differs or is unknown",
        "releaseMatch": "Release type differs",
    }.items() if not checks[key]]
    candidate_active = not bool(candidate.get("is_discontinued") or candidate.get("isDiscontinued"))
    if not candidate_active:
        block_reasons.append("Candidate is discontinued")
    return {
        **checks,
        "eligible": all(checks[key] for key in ("compositionMatch", "formMatch", "routeMatch", "releaseMatch")) and candidate_active,
        "candidateActive": candidate_active,
        "missingStrengthReviewRequired": selected["has_missing_strength"] or candidate["has_missing_strength"],
        "formulationReviewRequired": not checks["formulationMatch"],
        "matchReasons": reasons,
        "blockReasons": block_reasons,
    }
