"""Build a normalized medicine identity for image search and verification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from video_generation.schemas import MedicineVideoInput


FORM_ALIASES = {
    "tab": "tablet",
    "tabs": "tablet",
    "tablet": "tablet",
    "tablets": "tablet",
    "cap": "capsule",
    "caps": "capsule",
    "capsule": "capsule",
    "capsules": "capsule",
    "syp": "syrup",
    "syrup": "syrup",
    "susp": "suspension",
    "suspension": "suspension",
    "drop": "drops",
    "drops": "drops",
    "eyedrop": "eye drops",
    "eyedrops": "eye drops",
    "eardrop": "ear drops",
    "eardrops": "ear drops",
    "mdi": "inhaler",
    "metered dose inhaler": "inhaler",
    "inhaler": "inhaler",
    "cream": "cream",
    "ointment": "ointment",
    "gel": "gel",
    "tube": "tube",
}

FORM_WORDS = set(FORM_ALIASES) | {
    "oral",
    "ip",
    "usp",
    "pr",
    "sr",
    "xr",
    "mr",
    "dr",
    "er",
    "dt",
    "od",
}


@dataclass(frozen=True)
class MedicineIdentity:
    brand_name: str
    normalized_brand_name: str
    strength: str = ""
    dosage_form: str = ""
    manufacturer: str = ""
    pack_label: str = ""
    composition: str = ""
    route: str = ""
    release_type: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def search_core(self) -> str:
        parts = [self.brand_name, self.strength, self.dosage_form, self.manufacturer]
        return " ".join(part for part in parts if part).strip()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def extract_strength(*values: str) -> str:
    joined = " ".join(str(value or "") for value in values)
    matches: list[str] = []
    for amount, unit in re.findall(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|%)\b", joined, flags=re.IGNORECASE):
        normal_amount = amount.rstrip("0").rstrip(".") if "." in amount else amount
        item = f"{normal_amount} {unit.lower()}"
        if item not in matches:
            matches.append(item)
    return " + ".join(matches[:3])


def infer_dosage_form(*values: str) -> str:
    text = normalize_text(" ".join(str(value or "") for value in values))
    if "eye drops" in text or "eyedrops" in text:
        return "eye drops"
    if "ear drops" in text or "eardrops" in text:
        return "ear drops"
    if "nasal" in text or "nose" in text:
        return "nasal drops"
    if "metered dose inhaler" in text or "mdi" in text or "inhaler" in text:
        return "inhaler"
    for token in text.split():
        mapped = FORM_ALIASES.get(token)
        if mapped:
            return mapped
    return ""


def infer_release_type(value: str) -> str:
    text = normalize_text(value)
    for token in ("pr", "sr", "xr", "mr", "dr", "er", "dt", "od"):
        if token in text.split():
            return token.upper()
    return ""


def _brand_from_name(name: str) -> str:
    tokens = normalize_text(name).split()
    brand_tokens: list[str] = []
    for token in tokens:
        if token in FORM_WORDS:
            break
        if re.fullmatch(r"\d+(?:mg|mcg|g|ml|iu)", token):
            break
        if token.isdigit():
            break
        brand_tokens.append(token)
    if not brand_tokens and tokens:
        brand_tokens.append(tokens[0])
    return " ".join(brand_tokens).strip()


def _metadata_value(medicine: MedicineVideoInput, *names: str) -> str:
    for name in names:
        value = getattr(medicine, name, "")
        if value:
            return str(value).strip()
    return ""


def build_medicine_identity(medicine: MedicineVideoInput) -> MedicineIdentity:
    medicine_name = str(medicine.medicine_name or "").strip()
    composition = str(medicine.active_salts or "").strip()
    manufacturer = _metadata_value(medicine, "manufacturer", "manufacturer_name", "company")
    pack_label = _metadata_value(medicine, "pack_size_label", "pack_label", "packSizeLabel")
    dosage_form = infer_dosage_form(medicine_name, medicine.form, medicine.route, composition)
    strength = extract_strength(medicine_name, composition, pack_label)
    release_type = infer_release_type(medicine_name)
    brand = _brand_from_name(medicine_name) or medicine_name
    normalized_brand = normalize_text(brand)
    aliases = {normalized_brand}
    if dosage_form == "inhaler":
        aliases.update({"mdi", "metered dose inhaler", "inhaler device"})
    if dosage_form == "tablet":
        aliases.update({"tab", "tablet", "strip", "blister"})
    if dosage_form == "capsule":
        aliases.update({"cap", "capsule", "strip", "blister"})
    return MedicineIdentity(
        brand_name=brand,
        normalized_brand_name=normalized_brand,
        strength=strength,
        dosage_form=dosage_form,
        manufacturer=manufacturer,
        pack_label=pack_label,
        composition=composition,
        route=str(medicine.route or "").strip(),
        release_type=release_type,
        aliases=tuple(sorted(item for item in aliases if item)),
    )
