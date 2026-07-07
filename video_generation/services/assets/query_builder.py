"""Exact query generation for package and dosage/device image slots."""

from __future__ import annotations

from .identity import MedicineIdentity


def _join(*parts: str) -> str:
    return " ".join(str(part or "").strip() for part in parts if str(part or "").strip())


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(item.split()).casefold()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(" ".join(item.split()))
    return result


def build_asset_queries(identity: MedicineIdentity, asset_slot: str) -> list[str]:
    slot = "dosage" if asset_slot in {"tablet", "strip", "product", "dosage_form", "dosage"} else "package"
    brand = identity.brand_name
    strength = identity.strength
    form = identity.dosage_form
    manufacturer = identity.manufacturer
    pack_label = identity.pack_label

    if slot == "package":
        queries = [
            _join(brand, strength, form, manufacturer, "box pack"),
            _join(brand, strength, form, manufacturer, "package image"),
            _join(brand, pack_label, manufacturer, "medicine pack"),
            _join(brand, strength, form, "site:1mg.com"),
            _join(brand, strength, form, "site:apollopharmacy.in"),
            _join(brand, strength, form, "site:netmeds.com"),
            _join(brand, strength, form, "site:pharmeasy.in"),
            _join(brand, strength, form, "site:truemeds.in"),
        ]
        return _dedupe(queries)

    if form == "inhaler":
        specific = [
            "inhaler device canister",
            "metered dose inhaler device",
            "inhaler product image",
        ]
    elif form in {"eye drops", "ear drops", "nasal drops"}:
        specific = ["drops bottle nozzle", "dropper bottle", "medicine bottle"]
    elif form in {"ointment", "cream", "gel", "tube"}:
        specific = ["tube", "ointment tube", "cream tube"]
    elif form in {"syrup", "suspension"}:
        specific = ["syrup bottle", "medicine bottle", "measuring cup"]
    elif form == "capsule":
        specific = ["capsule strip blister", "capsule foil strip"]
    else:
        specific = ["tablet strip blister", "tablet foil strip"]

    queries = [_join(brand, strength, form, item) for item in specific]
    queries.extend(
        [
            _join(brand, strength, form, "site:1mg.com"),
            _join(brand, strength, form, "site:apollopharmacy.in"),
            _join(brand, strength, form, "site:netmeds.com"),
            _join(brand, strength, form, "site:pharmeasy.in"),
            _join(brand, strength, form, "site:truemeds.in"),
        ]
    )
    return _dedupe(queries)
