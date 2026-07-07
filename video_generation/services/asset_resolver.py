"""Strict online asset resolver for prescription video generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse, urlunparse

from PIL import Image, ImageDraw

from video_generation.config import VideoGenerationSettings, ensure_asset_directories, get_settings
from video_generation.providers.approved_pharmacy_image_provider import ApprovedPharmacyImageCandidate, ApprovedPharmacyImageProvider
from video_generation.providers.brave_image_provider import BraveImageCandidate, BraveImageProvider
from video_generation.providers.google_image_provider import GoogleImageProvider, ImageCandidate
from video_generation.providers.pexels_video_provider import PexelsVideoProvider, VideoCandidate
from video_generation.providers.serpapi_image_provider import SerpApiImageCandidate, SerpApiImageProvider
from video_generation.schemas import MedicineVideoInput, PrescriptionVideoInput
from video_generation.services.assets.gallery import AssetCandidateRecord, CandidateEvaluation, CandidateGallery
from video_generation.services.assets.identity import MedicineIdentity, build_medicine_identity
from video_generation.services.assets.ocr_verifier import OcrVerificationResult, verify_candidate_text
from video_generation.services.assets.query_builder import build_asset_queries
from video_generation.services.assets.scorer import score_candidate
from video_generation.services.asset_validator import AssetValidator, ValidationResult
from video_generation.services.manifest_store import AssetRecord, ManifestStore, utc_now
from video_generation.template_manager import select_template
from video_generation.utils import draw_wrapped_text, load_font, sanitize_filename

try:
    from ai_engine import ASSET_VALIDATION_POLICY_VERSION, validate_asset_pair_distinctness, validate_medicine_asset_image
except Exception:
    ASSET_VALIDATION_POLICY_VERSION = "strict_identity_v2"
    validate_asset_pair_distinctness = None
    validate_medicine_asset_image = None


class AssetResolutionError(Exception):
    def __init__(self, message: str, failures: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.failures = failures or []


@dataclass(frozen=True)
class ResolvedMedicineAssets:
    medicine_name: str
    medicine_slug: str
    route_template: str
    package_image: Path
    product_image: Path
    human_demo_video: Path
    package_confidence_label: str = "Exact package match"
    product_confidence_label: str = "Image review required"
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedPrescriptionAssets:
    medicines: dict[str, ResolvedMedicineAssets] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)


def detect_route_template(medicine: MedicineVideoInput) -> str:
    template = select_template(medicine, get_settings())
    if template.name == "nasal_spray":
        return "nasal_drops"
    return template.name


def _asset_key(*parts: str) -> str:
    return ":".join(parts)


def _record_path(record: AssetRecord | None) -> Path | None:
    if not record:
        return None
    path = Path(record.local_path)
    return path if path.exists() else None


COMMON_NAME_TOKENS = {
    "tablet",
    "tablets",
    "tab",
    "tabs",
    "capsule",
    "capsules",
    "cap",
    "caps",
    "strip",
    "bottle",
    "syrup",
    "suspension",
    "oral",
    "mg",
    "mcg",
    "g",
    "ml",
}

SERPAPI_REJECT_PARTS = {
    "medicine-substitute",
    "/substitutes",
    "alternatives/",
    "/avatar",
    "/author",
    "/consult",
    "/doctor",
    "/doctors",
    "/expert",
    "/experts",
    "/people",
    "/person",
    "/profile",
    "/profiles",
    "/team",
    "/user",
    "/users",
    "mobile404",
    "default_image",
    "noimage",
    "no-image",
    "placeholder",
    "medicine_image",
    "ui_revamp_mobile404",
    "othergeneralwarnings",
    "pregnancy.svg",
    "alcohol.svg",
    "breastfeeding.svg",
    "conditions/",
    "blog/",
}

TRUSTED_MEDICINE_IMAGE_DOMAINS = {
    "1mg.com",
    "assets.1mg.com",
    "apollopharmacy.in",
    "apollo247.in",
    "cdn01.pharmeasy.in",
    "images.apollo247.in",
    "onemg.gumlet.io",
    "pharmeasy.in",
    "frankrosspharmacy.com",
    "medineeds.in",
    "truemeds.in",
    "netmeds.com",
    "medplusmart.com",
}

PREFERRED_PHARMACY_DOMAINS = (
    "1mg.com",
    "apollopharmacy.in",
    "apollo247.in",
    "netmeds.com",
    "pharmeasy.in",
    "truemeds.in",
    "medplusmart.com",
)

CORE_OPAQUE_IMAGE_DOMAINS = {
    "1mg.com",
    "apollopharmacy.in",
    "apollo247.in",
    "images.apollo247.in",
    "netmeds.com",
    "onemg.gumlet.io",
    "pharmeasy.in",
    "cdn01.pharmeasy.in",
}

MAX_STRICT_IMAGE_CANDIDATES = 10

PROFILE_IMAGE_URL_PARTS = {
    "/avatar",
    "/author",
    "/consult",
    "/doctor",
    "/doctors",
    "/expert",
    "/experts",
    "/people",
    "/person",
    "/profile",
    "/profiles",
    "/team",
    "/user",
    "/users",
}

PROFILE_TEXT_HINTS = {
    "avatar",
    "author",
    "consult",
    "doctor",
    "doctors",
    "expert",
    "experts",
    "people",
    "person",
    "physician",
    "patient",
    "clinic",
    "hospital",
    "profile",
    "profiles",
    "team",
    "user",
    "users",
}

PACKAGE_IDENTITY_HINTS = {
    "back",
    "box",
    "carton",
    "label",
    "pack",
    "package",
    "image_1",
    "productimage",
}

PACKAGE_ONLY_IMAGE_HINTS = {
    "box-front",
    "box-back",
    "box_1",
    "box_2",
    "box-1",
    "box-2",
    "carton",
    "packaging",
    "package",
    "pack-front",
    "pack-back",
}

DOSAGE_FORM_IMAGE_HINTS = {
    "bottle-front",
    "bottle_1",
    "bottle-1",
    "dropper",
    "nozzle",
    "strip",
    "blister",
    "foil",
    "aluminium",
    "aluminum",
    "tablet-front",
    "capsule",
    "tube",
    "inhaler",
    "device",
}

ORAL_SOLID_FORMS = {"tablet", "capsule"}

PLACEHOLDER_IMAGE_HINTS = {
    "defaultimage",
    "default_image",
    "mobile404",
    "noimage",
    "no-image",
    "placeholder",
}

URL_PRODUCT_FORM_TOKENS = COMMON_NAME_TOKENS | {
    "drop",
    "drops",
    "cream",
    "gel",
    "inhaler",
    "lotion",
    "ointment",
    "spray",
    "tube",
}

URL_ASSET_NOISE_TOKENS = {
    "assets",
    "cache",
    "cdn",
    "cloud",
    "crop",
    "cropped",
    "free",
    "image",
    "images",
    "item",
    "original",
    "picture",
    "pictures",
    "plain",
    "product",
    "productimage",
    "products",
    "resize",
    "small",
    "thumbnail",
    "thumb",
    "upload",
    "uploads",
    "watermark",
    "wrkr",
}


def _match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _compact_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _canonical_page_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _url_path_text(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return unquote(f"{parsed.netloc}{parsed.path}").casefold()


def _looks_like_profile_or_person_url(url: str) -> bool:
    text = _url_path_text(url)
    if not text:
        return False
    if "onemg.gumlet.io/" in text and not any(part in text for part in ("/a_ignore", "l_watermark", "watermark", "/cropped/", "w_480", "h_480", "c_fit")):
        return True
    if any(part in text for part in PROFILE_IMAGE_URL_PARTS):
        return True
    if re.search(r"(?:^|[/_.-])(doctor|doctors|profile|avatar|expert|consult|physician|patient|clinic|hospital|people|person|team|user|users)(?:[/_.-]|$)", text):
        return True
    if re.search(r"(?:^|[/_.-])dr[_-][a-z]{2,}", text) and not any(hint in text for hint in (*PACKAGE_IDENTITY_HINTS, *DOSAGE_FORM_IMAGE_HINTS, "tablet", "capsule", "syrup", "drop", "inhaler", "ointment", "cream")):
        return True
    return False


def _looks_like_profile_or_person_text(text: str) -> bool:
    tokens = set(_match_text(text).split())
    return bool(tokens & PROFILE_TEXT_HINTS)


def _image_url_has_placeholder_hint(url: str) -> bool:
    compact = _compact_match_text(_url_path_text(url))
    return any(hint.replace("-", "") in compact for hint in PLACEHOLDER_IMAGE_HINTS)


def _image_url_conflicts_with_requested_medicine(medicine: MedicineVideoInput, url: str) -> bool:
    path_text = _match_text(unquote(urlparse(url).path))
    if not path_text:
        return False
    tokens = path_text.split()
    brand = _primary_name_token(medicine)
    if brand and brand in tokens:
        return False
    strength_terms = _strength_terms(medicine, include_active_salts=False)
    has_requested_strength = bool(strength_terms) and _has_strength(path_text, strength_terms)
    if not any(token in URL_PRODUCT_FORM_TOKENS for token in tokens) and not has_requested_strength:
        return False
    meaningful_tokens = [
        token
        for token in tokens
        if len(token) >= 4
        and not token.isdigit()
        and token not in URL_PRODUCT_FORM_TOKENS
        and token not in URL_ASSET_NOISE_TOKENS
    ]
    return bool(brand and meaningful_tokens)


def _image_url_contains_requested_brand(medicine: MedicineVideoInput, url: str) -> bool:
    brand = _primary_name_token(medicine)
    return bool(brand and brand in _match_text(unquote(urlparse(url).path)).split())


def _image_url_is_opaque_product_asset(medicine: MedicineVideoInput, url: str) -> bool:
    path_text = _match_text(unquote(urlparse(url).path))
    if not path_text:
        return True
    tokens = path_text.split()
    strength_terms = _strength_terms(medicine, include_active_salts=False)
    return not any(token in URL_PRODUCT_FORM_TOKENS for token in tokens) and not (strength_terms and _has_strength(path_text, strength_terms))


def _primary_name_token(medicine: MedicineVideoInput) -> str:
    for token in re.findall(r"[a-z0-9]+", medicine.medicine_name.casefold()):
        if token.isdigit() or token in COMMON_NAME_TOKENS:
            continue
        if re.fullmatch(r"\d+(mg|mcg|g|ml)", token):
            continue
        return token
    return ""


def _required_active_identity_tokens(medicine: MedicineVideoInput) -> list[str]:
    name_tokens = set(_match_text(medicine.medicine_name).split())
    blocked = COMMON_NAME_TOKENS | {"ip", "usp", "w", "v"}
    tokens: list[str] = []
    for token in _match_text(medicine.active_salts).split():
        if token in blocked or token.isdigit() or len(token) < 4:
            continue
        if token in name_tokens and token not in tokens:
            tokens.append(token)
    return tokens


def _image_search_name(medicine: MedicineVideoInput) -> str:
    return medicine.medicine_name


def _strength_terms(medicine: MedicineVideoInput, include_active_salts: bool = True) -> list[tuple[str, str]]:
    text = medicine.medicine_name.casefold()
    if include_active_salts:
        text = f"{text} {medicine.active_salts}".casefold()
    terms: list[tuple[str, str]] = []
    for amount, unit in re.findall(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", text):
        normal_amount = amount.rstrip("0").rstrip(".") if "." in amount else amount
        term = (normal_amount, unit)
        if term not in terms:
            terms.append(term)
        if unit == "g":
            try:
                mg_amount = str(int(float(amount) * 1000))
                mg_term = (mg_amount, "mg")
                if mg_term not in terms:
                    terms.append(mg_term)
            except ValueError:
                pass
    return terms


def _has_strength(text: str, terms: list[tuple[str, str]]) -> bool:
    if not terms:
        return True
    compact = _compact_match_text(text)
    for amount, unit in terms:
        if f"{amount}{unit}" in compact:
            return True
        if unit == "mg":
            try:
                numeric = float(amount)
                if numeric >= 1000 and numeric % 1000 == 0:
                    grams = int(numeric / 1000)
                    if f"{grams}g" in compact:
                        return True
            except ValueError:
                pass
    return False


def _has_product_identity(medicine: MedicineVideoInput, text: str) -> bool:
    brand = _primary_name_token(medicine)
    normalized = _match_text(text)
    if brand and brand not in normalized.split():
        return False
    return _has_strength(text, _strength_terms(medicine, include_active_salts=False))


def _search_asset_type(asset_type: str) -> str:
    return "dosage_form" if asset_type == "tablet" else asset_type


def _expected_asset_validation_type(asset_type: str) -> str:
    return "package" if asset_type == "package" else "dosage_form"


def _form_kind(medicine: MedicineVideoInput) -> str:
    text = _match_text(" ".join([medicine.medicine_name, medicine.active_salts, medicine.form, medicine.route]))
    if any(token in text for token in ("capsule", "capsules")):
        return "capsule"
    if any(token in text for token in ("syrup", "suspension", "oral solution")):
        return "syrup"
    if any(token in text for token in ("eye", "ophthalmic", "eyedrops")):
        return "eye_drops"
    if any(token in text for token in ("ear", "otic", "eardrops")):
        return "ear_drops"
    if any(token in text for token in ("nasal", "nose")):
        return "nasal_drops"
    if any(token in text for token in ("inhaler", "respule", "inhalation", "spray")):
        return "inhaler"
    if any(token in text for token in ("ointment", "cream", "gel", "lotion", "topical")):
        return "topical"
    return "tablet"


def _requires_exact_strip(medicine: MedicineVideoInput) -> bool:
    return _form_kind(medicine) in ORAL_SOLID_FORMS


def _has_dosage_form_hint(medicine: MedicineVideoInput, text: str) -> bool:
    lower = text.casefold()
    kind = _form_kind(medicine)
    if kind in ORAL_SOLID_FORMS:
        return any(hint in lower for hint in ("strip", "blister", "foil", "tablet-front", "capsule-front"))
    if kind == "syrup":
        return any(hint in lower for hint in ("syrup", "suspension", "bottle", "measuring", "cup"))
    if kind in {"eye_drops", "ear_drops", "nasal_drops"}:
        return any(hint in lower for hint in ("drop", "drops", "dropper", "nozzle", "bottle", "spray"))
    if kind == "inhaler":
        return any(hint in lower for hint in ("inhaler", "device", "spray"))
    if kind == "topical":
        return any(hint in lower for hint in ("tube", "ointment", "cream", "gel", "lotion"))
    return any(hint in lower for hint in DOSAGE_FORM_IMAGE_HINTS)


def _canonical_image_identity(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return _compact_match_text(url)
    return _compact_match_text(f"{parsed.netloc}{parsed.path}")


def _urls_are_similar(first: str, second: str) -> bool:
    first_id = _canonical_image_identity(first)
    second_id = _canonical_image_identity(second)
    if not first_id or not second_id:
        return False
    if first_id == second_id:
        return True
    first_name = Path(urlparse(first).path).stem.casefold()
    second_name = Path(urlparse(second).path).stem.casefold()
    return bool(first_name and second_name and first_name == second_name)


def _image_average_hash(path: Path) -> tuple[int, ...] | None:
    try:
        image = Image.open(path).convert("L").resize((8, 8), Image.Resampling.LANCZOS)
    except Exception:
        return None
    pixels = list(image.getdata())
    if not pixels:
        return None
    average = sum(pixels) / len(pixels)
    return tuple(1 if pixel >= average else 0 for pixel in pixels)


def _images_are_duplicate_like(first: Path, second: Path) -> bool:
    first_hash = _image_average_hash(first)
    second_hash = _image_average_hash(second)
    if not first_hash or not second_hash:
        return False
    distance = sum(1 for a, b in zip(first_hash, second_hash) if a != b)
    if distance <= 4:
        return True
    try:
        first_image = Image.open(first).convert("RGB").resize((96, 96), Image.Resampling.LANCZOS)
        second_image = Image.open(second).convert("RGB").resize((96, 96), Image.Resampling.LANCZOS)
    except Exception:
        return False
    diff_total = 0
    for left, right in zip(first_image.getdata(), second_image.getdata()):
        diff_total += sum(abs(left[channel] - right[channel]) for channel in range(3))
    mean_diff = diff_total / (96 * 96 * 3)
    return mean_diff < 10


class StrictAssetResolver:
    def __init__(self, settings: VideoGenerationSettings | None = None) -> None:
        self.settings = settings or get_settings()
        ensure_asset_directories(self.settings)
        self.store = ManifestStore(self.settings)
        validator_domains = tuple(dict.fromkeys((*self.settings.approved_image_domains, *TRUSTED_MEDICINE_IMAGE_DOMAINS)))
        self.validator = AssetValidator(validator_domains, self.settings.min_asset_score)
        self.approved_pharmacy = ApprovedPharmacyImageProvider(self.settings)
        self.serpapi = SerpApiImageProvider(self.settings)
        self.brave = BraveImageProvider(self.settings)
        self.google = GoogleImageProvider(self.settings)
        self.pexels = PexelsVideoProvider(self.settings)

    def resolve_prescription(self, prescription_data: PrescriptionVideoInput | dict[str, Any], force_refresh: bool = False) -> ResolvedPrescriptionAssets:
        prescription = prescription_data if isinstance(prescription_data, PrescriptionVideoInput) else PrescriptionVideoInput.from_dict(prescription_data)
        failures: list[dict[str, Any]] = []
        resolved: dict[str, ResolvedMedicineAssets] = {}
        for medicine in prescription.medicines:
            try:
                item = self.resolve_medicine(medicine, force_refresh=force_refresh)
                resolved[item.medicine_slug] = item
            except AssetResolutionError as exc:
                failures.extend(exc.failures)
        if failures and not resolved:
            summary = "; ".join(f"{item.get('medicineName') or item.get('routeTemplate')}: {item.get('assetType')} - {item.get('reason')}" for item in failures)
            raise AssetResolutionError(summary, failures)
        return ResolvedPrescriptionAssets(medicines=resolved, failures=failures)

    def resolve_medicine(self, medicine: MedicineVideoInput, force_refresh: bool = False) -> ResolvedMedicineAssets:
        slug = sanitize_filename(medicine.medicine_name)
        route_template = detect_route_template(medicine)
        failures: list[dict[str, Any]] = []

        route_video = self._resolve_route_video(route_template, force_refresh, failures)
        image_failures: list[dict[str, Any]] = []
        package_image = self._resolve_image(medicine, slug, "package", force_refresh, image_failures)
        if not package_image:
            image_failures.append({
                "medicineName": medicine.medicine_name,
                "assetType": "package image",
                "stage": "validation",
                "reason": "No validated package image passed medicine identity checks.",
            })
        package_record = self.store.get_asset(_asset_key("medicine_image", slug, "package"))
        product_image = self._resolve_image(
            medicine,
            slug,
            "tablet",
            force_refresh,
            image_failures,
            distinct_from=package_image,
            distinct_source_url=package_record.source_url if package_record else "",
        )
        if not product_image and package_image:
            product_image = self._derive_dosage_image_from_package(medicine, slug, package_image, package_record, force_refresh, image_failures)
        if not product_image:
            image_failures.append({
                "medicineName": medicine.medicine_name,
                "assetType": "dosage form image",
                "stage": "validation",
                "reason": "No validated dosage/strip image passed medicine identity checks.",
            })

        if failures or not route_video:
            raise AssetResolutionError("Unable to resolve required route video asset", [*failures, *image_failures])

        asset_warnings = self._asset_warnings_from_failures(medicine, image_failures)
        package_confidence_label = self._confidence_label(slug, "package")
        product_confidence_label = self._confidence_label(slug, "tablet")
        if not package_image:
            reason = self._failure_reason_for_asset(image_failures, medicine.medicine_name, "package")
            package_image = self._create_missing_image_card(medicine, slug, "package", reason, force_refresh)
            package_confidence_label = "Valid image not found"
        if not product_image:
            reason = self._failure_reason_for_asset(image_failures, medicine.medicine_name, "tablet")
            product_image = self._create_missing_image_card(medicine, slug, "tablet", reason, force_refresh)
            product_confidence_label = "Valid image not found"

        return ResolvedMedicineAssets(
            medicine_name=medicine.medicine_name,
            medicine_slug=slug,
            route_template=route_template,
            package_image=package_image,
            product_image=product_image,
            human_demo_video=route_video,
            package_confidence_label=package_confidence_label,
            product_confidence_label=product_confidence_label,
            warnings=asset_warnings,
        )

    def _candidate_gallery_candidates(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        asset_type: str,
    ) -> tuple[list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate], CandidateGallery]:
        gallery = CandidateGallery(self.settings.asset_gallery_dir, slug, asset_type)
        identity = build_medicine_identity(medicine)
        slot = "package" if asset_type == "package" else "dosage"
        queries = build_asset_queries(identity, slot)
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate] = []
        seen: set[str] = set()
        try:
            serpapi_candidates = self.serpapi.search(
                identity.search_core or medicine.medicine_name,
                _search_asset_type(asset_type),
                queries=queries,
                per_query_limit=8,
                max_candidates=32,
            )
        except Exception:
            serpapi_candidates = []
        for candidate in serpapi_candidates:
            if candidate.url.casefold() in seen:
                continue
            seen.add(candidate.url.casefold())
            candidates.append(candidate)

        discovered = self._approved_candidates_from_serpapi_product_pages(medicine, asset_type, serpapi_candidates)
        for candidate in discovered:
            if candidate.url.casefold() in seen:
                continue
            seen.add(candidate.url.casefold())
            candidates.append(candidate)

        return self._rank_gallery_metadata_candidates(medicine, asset_type, candidates), gallery

    def _rank_gallery_metadata_candidates(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate],
    ) -> list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate]:
        identity = build_medicine_identity(medicine)
        slot = "package" if asset_type == "package" else "dosage"
        scored: list[tuple[float, int, ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate]] = []
        for index, candidate in enumerate(candidates):
            metadata_text = self._candidate_metadata_text(candidate)
            ocr_result = verify_candidate_text(None, identity, metadata_text, enable_ocr=False)
            score = score_candidate(
                identity,
                slot,
                candidate.source_domain,
                getattr(candidate, "query_used", ""),
                metadata_text,
                ocr_result,
                None,
                0.65,
            )
            if score.hard_reject_reason and "Brand identity" not in score.hard_reject_reason:
                continue
            scored.append((score.final_score, -index, candidate))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [candidate for _, _, candidate in scored]

    def _resolve_route_video(self, route_template: str, force_refresh: bool, failures: list[dict[str, Any]]) -> Path | None:
        key = _asset_key("route_video", route_template)
        if not force_refresh:
            cached = _record_path(self.store.get_asset(key))
            if cached:
                return cached
        local_route = self.settings.asset_cache_dir / "routes" / f"{route_template}.mp4"
        if local_route.exists():
            return local_route
        if not self.settings.pexels_api_key:
            failures.append({"routeTemplate": route_template, "assetType": "route demo video", "stage": "provider_config", "reason": "PEXELS_API_KEY is not configured"})
            return None
        target = self.settings.asset_cache_dir / "routes" / f"{route_template}.mp4"
        best_failure = "No high-confidence route video found"
        try:
            candidates = self.pexels.search(route_template)
        except Exception as exc:
            failures.append({"routeTemplate": route_template, "assetType": "route demo video", "stage": "internet_fetch", "reason": str(exc)})
            return None
        for candidate in candidates:
            try:
                path = self.pexels.download(candidate, target)
                validation = self.validator.validate_video(path, candidate.url, candidate.duration, candidate.width, candidate.height)
                if validation.valid:
                    self._save_record(key, "route_demo_video", path, candidate, validation, route_template=route_template, force_refresh=force_refresh)
                    return path
                best_failure = validation.reason
                path.unlink(missing_ok=True)
            except Exception as exc:
                best_failure = str(exc)
        failures.append({"routeTemplate": route_template, "assetType": "route demo video", "stage": "validation", "reason": best_failure})
        return None

    def _resolve_image(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        asset_type: str,
        force_refresh: bool,
        failures: list[dict[str, Any]],
        distinct_from: Path | None = None,
        distinct_source_url: str = "",
    ) -> Path | None:
        key = _asset_key("medicine_image", slug, asset_type)
        best_failure = "No high-confidence image result found"
        if not force_refresh:
            cached_record = self.store.get_asset(key)
            cached = _record_path(cached_record)
            if cached:
                reject_reason = self._cached_image_reject_reason(medicine, asset_type, cached, cached_record, distinct_from, distinct_source_url)
                if reject_reason:
                    best_failure = f"Rejected cached image: {reject_reason}"
                    if self.settings.asset_cache_dir in cached.parents:
                        cached.unlink(missing_ok=True)
                else:
                    reject_reason, vision_validation = self._vision_asset_reject_reason(medicine, asset_type, cached, cached_record, distinct_from)
                    if not reject_reason:
                        if cached_record and vision_validation:
                            self._refresh_record_vision_result(key, cached_record, asset_type, vision_validation)
                        return cached
                    best_failure = f"Rejected cached image: {reject_reason}"
                    if self.settings.asset_cache_dir in cached.parents:
                        cached.unlink(missing_ok=True)
        if not force_refresh:
            local = self._find_existing_image(medicine, slug, asset_type)
            if local:
                reject_reason = self._local_image_reject_reason(medicine, asset_type, local, distinct_from)
                if reject_reason:
                    best_failure = f"Rejected local image: {reject_reason}"
                    if self.settings.asset_cache_dir in local.parents:
                        local.unlink(missing_ok=True)
                    local = None
            if local:
                reject_reason, _ = self._vision_asset_reject_reason(medicine, asset_type, local, None, distinct_from)
                if not reject_reason:
                    return local
                best_failure = f"Rejected local image: {reject_reason}"
        target = self.settings.asset_cache_dir / "medicines" / slug / f"{asset_type}.jpg"
        if asset_type in {"package", "tablet"} and self.settings.enable_asset_downloads and self.settings.serpapi_api_key:
            gallery_candidates, gallery = self._candidate_gallery_candidates(medicine, slug, asset_type)
            if gallery_candidates:
                gallery_path = self._download_best_image_candidate(
                    medicine,
                    slug,
                    asset_type,
                    key,
                    target,
                    None,
                    gallery_candidates,
                    failures,
                    force_refresh,
                    best_failure,
                    append_failure=False,
                    distinct_from=distinct_from,
                    distinct_source_url=distinct_source_url,
                    gallery=gallery,
                )
                if gallery_path:
                    return gallery_path
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate] = []
        provider = None
        serpapi_candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate] | None = None
        serpapi_search_error = ""
        if asset_type in {"package", "tablet"} and self.settings.serpapi_api_key:
            provider = self.serpapi
            try:
                serpapi_candidates = self.serpapi.search(_image_search_name(medicine), _search_asset_type(asset_type))
            except Exception as exc:
                serpapi_search_error = str(exc)
                best_failure = f"SerpAPI {asset_type} search failed: {exc}"
            else:
                priority_candidates = (
                    self._preferred_package_image_candidates(medicine, serpapi_candidates)
                    if asset_type == "package"
                    else self._preferred_tablet_strip_candidates(medicine, serpapi_candidates)
                )
                if priority_candidates:
                    priority_path = self._download_best_image_candidate(
                        medicine,
                        slug,
                        asset_type,
                        key,
                        target,
                        self.serpapi,
                        priority_candidates,
                        failures,
                        force_refresh,
                        best_failure,
                        append_failure=False,
                        distinct_from=distinct_from,
                        distinct_source_url=distinct_source_url,
                    )
                    if priority_path:
                        return priority_path
        if asset_type in {"package", "tablet"}:
            provider = self.approved_pharmacy
            try:
                candidates = self.approved_pharmacy.search(medicine.medicine_name, asset_type)
            except Exception as exc:
                best_failure = f"Approved pharmacy page fetch failed: {exc}"
            if candidates:
                approved_path = self._download_best_image_candidate(
                    medicine,
                    slug,
                    asset_type,
                    key,
                    target,
                    provider,
                    candidates,
                    failures,
                    force_refresh,
                    best_failure,
                    append_failure=False,
                    distinct_from=distinct_from,
                    distinct_source_url=distinct_source_url,
                )
                if approved_path:
                    return approved_path

        if self.settings.serpapi_api_key:
            provider = self.serpapi
            if serpapi_search_error:
                failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "internet_fetch", "reason": f"SerpAPI failed: {serpapi_search_error}"})
                return None
            if serpapi_candidates is None:
                try:
                    candidates = self.serpapi.search(_image_search_name(medicine), _search_asset_type(asset_type))
                except Exception as exc:
                    failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "internet_fetch", "reason": f"SerpAPI failed: {exc}"})
                    return None
            else:
                candidates = serpapi_candidates
            discovered_candidates = self._approved_candidates_from_serpapi_product_pages(medicine, asset_type, candidates)
            if discovered_candidates:
                discovered_path = self._download_best_image_candidate(
                    medicine,
                    slug,
                    asset_type,
                    key,
                    target,
                    self.approved_pharmacy,
                    discovered_candidates,
                    failures,
                    force_refresh,
                    best_failure,
                    append_failure=False,
                    distinct_from=distinct_from,
                    distinct_source_url=distinct_source_url,
                )
                if discovered_path:
                    return discovered_path
        elif self.settings.brave_search_api_key:
            provider = self.brave
            try:
                candidates = self.brave.search(medicine.medicine_name, _search_asset_type(asset_type))
            except Exception as exc:
                failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "internet_fetch", "reason": f"Brave Search failed: {exc}"})
                return None
        elif self.settings.google_cse_api_key and self.settings.google_cse_id:
            provider = self.google
            try:
                candidates = self.google.search(medicine.medicine_name, _search_asset_type(asset_type))
            except Exception as exc:
                failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "internet_fetch", "reason": f"Google CSE failed: {exc}"})
                return None
        else:
            failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "provider_config", "reason": "SERPAPI_API_KEY is not configured"})
            return None
        resolved = self._download_best_image_candidate(
            medicine,
            slug,
            asset_type,
            key,
            target,
            provider,
            candidates,
            failures,
            force_refresh,
            best_failure,
            append_failure=True,
            distinct_from=distinct_from,
            distinct_source_url=distinct_source_url,
        )
        return resolved

    def _preferred_package_image_candidates(
        self,
        medicine: MedicineVideoInput,
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate],
    ) -> list[SerpApiImageCandidate]:
        scored: list[tuple[int, SerpApiImageCandidate]] = []
        for candidate in candidates:
            if not isinstance(candidate, SerpApiImageCandidate):
                continue
            text = f"{candidate.title} {candidate.page_url} {candidate.url} {candidate.source}".casefold()
            if self._is_rejected_result_text(text):
                continue
            if _looks_like_profile_or_person_text(text):
                continue
            if _looks_like_profile_or_person_url(candidate.url) or _looks_like_profile_or_person_url(candidate.page_url):
                continue
            if not self._is_allowed_source_domain(candidate.source_domain):
                continue
            if not _has_product_identity(medicine, f"{candidate.title} {candidate.page_url}"):
                continue
            score = 8
            if any(hint in text for hint in PACKAGE_IDENTITY_HINTS):
                score += 6
            if "strip" in text or "blister" in text:
                score += 2
            if "back" in text or "label" in text:
                score += 5
            if "front" in text and not any(hint in text for hint in ("back", "box", "carton", "label", "pack", "package", "image_1")):
                score -= 5
            score += self._source_domain_preference_score(candidate.source_domain)
            scored.append((score, candidate))
        return [candidate for _, candidate in sorted(scored, key=lambda item: item[0], reverse=True)]

    def _preferred_tablet_strip_candidates(
        self,
        medicine: MedicineVideoInput,
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate],
    ) -> list[SerpApiImageCandidate]:
        scored: list[tuple[int, SerpApiImageCandidate]] = []
        for candidate in candidates:
            if not isinstance(candidate, SerpApiImageCandidate):
                continue
            text = f"{candidate.title} {candidate.page_url} {candidate.url} {candidate.source}".casefold()
            if self._is_rejected_result_text(text):
                continue
            if _looks_like_profile_or_person_text(text):
                continue
            if _looks_like_profile_or_person_url(candidate.url) or _looks_like_profile_or_person_url(candidate.page_url):
                continue
            if not self._is_allowed_source_domain(candidate.source_domain):
                continue
            if not _has_product_identity(medicine, f"{candidate.title} {candidate.page_url}"):
                continue
            if not _has_dosage_form_hint(medicine, text):
                continue
            score = 8 + self._source_domain_preference_score(candidate.source_domain)
            if "strip" in text or "blister" in text:
                score += 10
            if "foil" in text:
                score += 6
            if any(hint in text for hint in PACKAGE_ONLY_IMAGE_HINTS):
                score -= 8
            scored.append((score, candidate))
        return [candidate for _, candidate in sorted(scored, key=lambda item: item[0], reverse=True)]

    def _download_best_image_candidate(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        asset_type: str,
        key: str,
        target: Path,
        provider: ApprovedPharmacyImageProvider | SerpApiImageProvider | BraveImageProvider | GoogleImageProvider | None,
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate],
        failures: list[dict[str, Any]],
        force_refresh: bool,
        best_failure: str = "No high-confidence image result found",
        append_failure: bool = True,
        distinct_from: Path | None = None,
        distinct_source_url: str = "",
        gallery: CandidateGallery | None = None,
    ) -> Path | None:
        identity = build_medicine_identity(medicine)
        asset_slot = "package" if asset_type == "package" else "dosage"
        accepted: list[tuple[
            float,
            Path,
            ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
            ValidationResult,
            OcrVerificationResult,
            dict[str, Any] | None,
            bool,
        ]] = []
        checked_paths: list[Path] = []
        for stale_candidate in target.parent.glob(f".{target.stem}.*{target.suffix}"):
            stale_candidate.unlink(missing_ok=True)
        for index, candidate in enumerate(candidates[:MAX_STRICT_IMAGE_CANDIDATES]):
            reject_reason = self._candidate_reject_reason(medicine, asset_type, candidate, distinct_source_url)
            if reject_reason:
                best_failure = reject_reason
                self._add_gallery_evaluation(gallery, candidate, asset_type, index, rejection_reason=reject_reason)
                continue
            source_domain_allowed = self._is_allowed_source_domain(candidate.source_domain)
            requires_vision_override = bool(self.settings.approved_image_domains and not source_domain_allowed)
            try:
                candidate_target = target.parent / f".{target.stem}.{index}{target.suffix}"
                candidate_provider = provider or self._provider_for_candidate(candidate)
                path = candidate_provider.download(candidate, candidate_target)
                checked_paths.append(path)
                validation = self.validator.validate_image(path, candidate.url, exact_query_match=True, source_domain=candidate.source_domain)
                can_try_vision_override = (
                    self.settings.enable_vision_image_validation
                    and validate_medicine_asset_image is not None
                    and validation.width >= 300
                    and validation.height >= 300
                    and "confidence below threshold" in validation.reason.casefold()
                )
                if validation.valid or can_try_vision_override:
                    visual_reject_reason = self._asset_visual_reject_reason(asset_type, path)
                    if visual_reject_reason:
                        best_failure = visual_reject_reason
                        self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, rejection_reason=visual_reject_reason)
                        path.unlink(missing_ok=True)
                        continue
                    if asset_type != "package" and distinct_from and distinct_from.exists() and _images_are_duplicate_like(path, distinct_from):
                        best_failure = "Rejected dosage-form image because it duplicates the package image"
                        self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, rejection_reason=best_failure)
                        path.unlink(missing_ok=True)
                        continue
                    vision_reject_reason, vision_validation = self._vision_asset_reject_reason(medicine, asset_type, path, candidate, distinct_from)
                    if vision_reject_reason:
                        best_failure = vision_reject_reason
                        self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, vision_result=vision_validation, rejection_reason=vision_reject_reason)
                        path.unlink(missing_ok=True)
                        continue
                    if requires_vision_override and not vision_validation:
                        best_failure = f"Rejected unapproved source domain without Llama 4 verification: {candidate.source_domain}"
                        self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, rejection_reason=best_failure, review_required=True)
                        path.unlink(missing_ok=True)
                        continue
                    if vision_validation:
                        validation = ValidationResult(
                            True,
                            max(validation.score, float(vision_validation.get("finalScore", vision_validation.get("confidence", validation.score)) or validation.score)),
                            "Image accepted by rule and Llama 4 vision validation",
                            validation.width,
                            validation.height,
                            validation.duration,
                        )
                    elif requires_vision_override:
                        best_failure = f"Rejected unapproved source domain: {candidate.source_domain}"
                        self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, rejection_reason=best_failure, review_required=True)
                        path.unlink(missing_ok=True)
                        continue
                    ocr_result = verify_candidate_text(
                        path,
                        identity,
                        self._candidate_metadata_text(candidate),
                        enable_ocr=self.settings.enable_ocr_image_validation,
                    )
                    candidate_score = score_candidate(
                        identity,
                        asset_slot,
                        candidate.source_domain,
                        str(getattr(candidate, "query_used", "")),
                        self._candidate_metadata_text(candidate),
                        ocr_result,
                        vision_validation,
                        validation.score,
                    )
                    if candidate_score.hard_reject_reason:
                        best_failure = candidate_score.hard_reject_reason
                        self._add_gallery_evaluation(
                            gallery,
                            candidate,
                            asset_type,
                            index,
                            local_preview=path,
                            ocr_result=ocr_result,
                            vision_result=vision_validation,
                            score=candidate_score.final_score,
                            rejection_reason=best_failure,
                            review_required=candidate_score.review_required_source,
                        )
                        path.unlink(missing_ok=True)
                        continue
                    if candidate_score.final_score < self.settings.min_asset_score:
                        best_failure = f"Candidate score below threshold ({candidate_score.final_score:.2f} < {self.settings.min_asset_score:.2f})"
                        self._add_gallery_evaluation(
                            gallery,
                            candidate,
                            asset_type,
                            index,
                            local_preview=path,
                            ocr_result=ocr_result,
                            vision_result=vision_validation,
                            score=candidate_score.final_score,
                            rejection_reason=best_failure,
                            review_required=candidate_score.review_required_source,
                        )
                        path.unlink(missing_ok=True)
                        continue
                    final_score = candidate_score.final_score + (self._source_domain_preference_score(candidate.source_domain) / 100)
                    self._add_gallery_evaluation(
                        gallery,
                        candidate,
                        asset_type,
                        index,
                        local_preview=path,
                        ocr_result=ocr_result,
                        vision_result=vision_validation,
                        score=final_score,
                        review_required=candidate_score.review_required_source,
                    )
                    accepted.append((final_score, path, candidate, validation, ocr_result, vision_validation, candidate_score.review_required_source))
                    continue
                best_failure = validation.reason
                self._add_gallery_evaluation(gallery, candidate, asset_type, index, local_preview=path, rejection_reason=validation.reason)
                path.unlink(missing_ok=True)
            except Exception as exc:
                best_failure = str(exc)
                self._add_gallery_evaluation(gallery, candidate, asset_type, index, rejection_reason=str(exc))
        if accepted:
            accepted.sort(key=lambda item: item[0], reverse=True)
            _, best_path, best_candidate, best_validation, best_ocr, best_vision, review_required = accepted[0]
            if asset_type != "package":
                cropped = self._tighten_dosage_image_with_verified_crop(medicine, slug, best_path, target, best_candidate, best_validation)
                if cropped:
                    best_path, best_validation = cropped
                    checked_paths.append(best_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if best_path != target:
                best_path.replace(target)
            for path in checked_paths:
                if path != target and path.exists():
                    path.unlink(missing_ok=True)
            if gallery:
                gallery.mark_selected(best_candidate.url)
                gallery.save()
            self._save_record(
                key,
                f"{asset_type}_image",
                target,
                best_candidate,
                best_validation,
                medicine,
                slug,
                force_refresh=force_refresh,
                gallery_id=gallery.gallery_id if gallery else "",
                ocr_text=best_ocr.text,
                vision_result=best_vision,
                review_required=review_required,
            )
            return target
        if append_failure:
            failures.append({"medicineName": medicine.medicine_name, "assetType": f"{asset_type} image", "stage": "validation", "reason": best_failure})
        if gallery:
            gallery.save()
        return None

    def _approved_candidates_from_serpapi_product_pages(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        candidates: list[ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate],
    ) -> list[ApprovedPharmacyImageCandidate]:
        discovered: list[ApprovedPharmacyImageCandidate] = []
        seen_pages: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, SerpApiImageCandidate):
                continue
            page_url = _canonical_page_url(candidate.page_url)
            if not page_url or page_url in seen_pages:
                continue
            if self._is_rejected_result_text(f"{candidate.title} {page_url} {candidate.source}"):
                continue
            if _looks_like_profile_or_person_text(f"{candidate.title} {page_url} {candidate.source}"):
                continue
            if _looks_like_profile_or_person_url(candidate.url) or _looks_like_profile_or_person_url(page_url):
                continue
            if not _has_product_identity(medicine, f"{candidate.title} {page_url}"):
                continue
            required_active_tokens = _required_active_identity_tokens(medicine)
            page_identity_tokens = set(_match_text(f"{candidate.title} {page_url} {candidate.source}").split())
            if required_active_tokens and not any(token in page_identity_tokens for token in required_active_tokens):
                continue
            seen_pages.add(page_url)
            try:
                discovered.extend(self.approved_pharmacy._extract_candidates(page_url, medicine.medicine_name, asset_type))
            except Exception:
                continue
        return discovered

    def _candidate_reject_reason(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
        distinct_source_url: str = "",
    ) -> str:
        page_url = getattr(candidate, "page_url", "")
        source = getattr(candidate, "source", "")
        text = f"{candidate.title} {page_url} {candidate.url} {source}".casefold()
        if self._is_rejected_result_text(text):
            return "Rejected substitute, placeholder, or non-product image result"
        if _looks_like_profile_or_person_text(text):
            return "Rejected profile, doctor, or non-product image result"
        if _looks_like_profile_or_person_url(candidate.url) or _looks_like_profile_or_person_url(page_url):
            return "Rejected profile, doctor, or non-product image result"
        if _image_url_has_placeholder_hint(candidate.url):
            return "Rejected placeholder or missing-product image result"
        if _image_url_conflicts_with_requested_medicine(medicine, candidate.url):
            return "Rejected image result because the image file points to a different medicine"
        if isinstance(candidate, SerpApiImageCandidate) and _image_url_is_opaque_product_asset(medicine, candidate.url) and not _image_url_contains_requested_brand(medicine, candidate.url):
            source_domain = candidate.source_domain.casefold().removeprefix("www.")
            if not any(source_domain == domain or source_domain.endswith(f".{domain}") for domain in CORE_OPAQUE_IMAGE_DOMAINS):
                return "Rejected opaque image URL from a source that cannot be verified as the requested medicine"
        if asset_type != "package":
            if distinct_source_url and _urls_are_similar(candidate.url, distinct_source_url):
                return "Rejected dosage-form image because candidate URL matches the package image"
            if distinct_source_url and page_url and _urls_are_similar(page_url, distinct_source_url):
                return "Rejected dosage-form image because candidate page matches the package image"
            if any(hint in text for hint in PACKAGE_ONLY_IMAGE_HINTS) and not any(hint in text for hint in DOSAGE_FORM_IMAGE_HINTS):
                return "Rejected dosage-form image because result points to package/box artwork"
            if any(hint in text for hint in ("box-front", "box-back", "pack-front", "pack-back")):
                return "Rejected dosage-form image because result points to package/box artwork"
            if _requires_exact_strip(medicine) and not _has_dosage_form_hint(medicine, text):
                return "Rejected dosage-form image because no strip/blister evidence was found"
        if not isinstance(candidate, SerpApiImageCandidate):
            required_active_tokens = _required_active_identity_tokens(medicine)
            source_identity_tokens = set(_match_text(f"{page_url} {candidate.url} {source}").split())
            if required_active_tokens and not any(token in source_identity_tokens for token in required_active_tokens):
                return "Rejected image result because it does not match requested active formulation"
        if isinstance(candidate, SerpApiImageCandidate):
            if not _has_product_identity(medicine, f"{candidate.title} {candidate.page_url}"):
                return "Rejected image result because it does not match requested medicine name and strength"
            identity_text = f"{candidate.title} {candidate.page_url} {candidate.url}"
            identity_tokens = set(_match_text(identity_text).split())
            required_active_tokens = _required_active_identity_tokens(medicine)
            if required_active_tokens and not any(token in identity_tokens for token in required_active_tokens):
                return "Rejected image result because it does not match requested active formulation"
            if self._is_allowed_source_domain(candidate.source_domain):
                return ""
            url_text = candidate.url.casefold()
            brand = _primary_name_token(medicine)
            if brand and brand not in _match_text(url_text).split():
                return "Rejected raw SerpAPI image because image URL does not contain requested brand"
            if not _has_strength(url_text, _strength_terms(medicine, include_active_salts=False)):
                return "Rejected raw SerpAPI image because image URL does not contain requested strength"
        return ""

    def _asset_visual_reject_reason(self, asset_type: str, path: Path) -> str:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            return f"Rejected {asset_type} image because it is not readable"
        image.thumbnail((220, 220), Image.LANCZOS)
        pixels = list(image.getdata())
        if not pixels:
            return f"Rejected {asset_type} image because it is empty"
        total = len(pixels)
        colored_ratio = sum(1 for r, g, b in pixels if max(r, g, b) - min(r, g, b) > 28 and min(r, g, b) < 245) / total
        dark_ratio = sum(1 for r, g, b in pixels if (r + g + b) / 3 < 140) / total
        skin_ratio = sum(1 for r, g, b in pixels if r > 95 and g > 40 and b > 20 and r > g * 1.05 and r > b * 1.25 and abs(r - g) > 12) / total
        if skin_ratio > 0.22 and dark_ratio > 0.05:
            return f"Rejected {asset_type} image because it appears to contain a person instead of a medicine asset"
        if asset_type == "package" and colored_ratio < 0.015 and dark_ratio < 0.01:
            return "Rejected package image because it appears to be an unbranded plain strip without readable label or package detail"
        return ""

    def _candidate_context(
        self,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate | AssetRecord | None,
    ) -> dict[str, Any]:
        if not candidate:
            return {}
        if isinstance(candidate, AssetRecord):
            return {
                "image_url": candidate.source_url,
                "url": candidate.source_url,
                "source_domain": candidate.source_domain,
                "source": candidate.provider,
                "title": candidate.medicine_name,
            }
        return {
            "image_url": candidate.url,
            "url": candidate.url,
            "source_domain": candidate.source_domain,
            "source": getattr(candidate, "source", ""),
            "title": candidate.title,
            "page_url": getattr(candidate, "page_url", ""),
        }

    def _candidate_metadata_text(
        self,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate | AssetRecord,
    ) -> str:
        return " ".join(
            str(value or "")
            for value in (
                getattr(candidate, "title", ""),
                getattr(candidate, "source", ""),
                getattr(candidate, "source_domain", ""),
                getattr(candidate, "page_url", ""),
                getattr(candidate, "url", getattr(candidate, "source_url", "")),
                getattr(candidate, "snippet", ""),
                getattr(candidate, "query_used", ""),
            )
        )

    def _provider_for_candidate(
        self,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
    ) -> ApprovedPharmacyImageProvider | SerpApiImageProvider | BraveImageProvider | GoogleImageProvider:
        if isinstance(candidate, ApprovedPharmacyImageCandidate):
            return self.approved_pharmacy
        if isinstance(candidate, SerpApiImageCandidate):
            return self.serpapi
        if isinstance(candidate, BraveImageCandidate):
            return self.brave
        return self.google

    def _candidate_record(
        self,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
        asset_type: str,
        fallback_rank: int,
    ) -> AssetCandidateRecord:
        return AssetCandidateRecord(
            image_url=candidate.url,
            thumbnail_url=str(getattr(candidate, "thumbnail_url", "")),
            source_page_url=str(getattr(candidate, "page_url", "")),
            source_domain=candidate.source_domain,
            title=candidate.title,
            snippet=str(getattr(candidate, "snippet", "")),
            query_used=str(getattr(candidate, "query_used", "")),
            asset_slot="package" if asset_type == "package" else "dosage",
            raw_rank=int(getattr(candidate, "raw_rank", 0) or fallback_rank),
            provider=candidate.provider,
        )

    def _add_gallery_evaluation(
        self,
        gallery: CandidateGallery | None,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
        asset_type: str,
        index: int,
        *,
        local_preview: Path | None = None,
        ocr_result: OcrVerificationResult | None = None,
        vision_result: dict[str, Any] | None = None,
        score: float = 0.0,
        rejection_reason: str = "",
        review_required: bool = False,
        derived_crop: bool = False,
    ) -> None:
        if gallery is None:
            return
        gallery.add(
            CandidateEvaluation(
                candidate=self._candidate_record(candidate, asset_type, index + 1),
                local_preview=str(local_preview or ""),
                ocr_text=ocr_result.text if ocr_result else "",
                ocr_score=ocr_result.score if ocr_result else 0.0,
                ocr_complete=ocr_result.complete if ocr_result else False,
                vision_result=vision_result or {},
                score=score,
                rejection_reason=rejection_reason,
                review_required=review_required,
                derived_crop=derived_crop,
            )
        )

    def _vision_asset_reject_reason(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        path: Path,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate | AssetRecord | None = None,
        distinct_from: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        if not self.settings.enable_vision_image_validation or validate_medicine_asset_image is None:
            return "", None
        try:
            validation = validate_medicine_asset_image(
                path.read_bytes(),
                medicine.medicine_name,
                medicine.active_salts,
                _expected_asset_validation_type(asset_type),
                context=self._candidate_context(candidate),
                debug=self.settings.asset_validation_debug,
            )
        except Exception as exc:
            return f"Vision validation crashed: {exc}", None

        reject_reason = str(validation.get("rejectReason") or "")
        if reject_reason.startswith("Vision asset validation failed:"):
            return reject_reason, validation
        if not validation.get("accepted"):
            return reject_reason or "Vision model rejected image asset", validation
        strict_reject_reason = self._strict_vision_reject_reason(validation)
        if strict_reject_reason:
            return strict_reject_reason, validation

        if distinct_from and distinct_from.exists() and asset_type != "package" and validate_asset_pair_distinctness is not None:
            package_validation = validate_medicine_asset_image(
                distinct_from.read_bytes(),
                medicine.medicine_name,
                medicine.active_salts,
                "package",
                context={"local_path": str(distinct_from), "title": f"{medicine.medicine_name} package image"},
                debug=self.settings.asset_validation_debug,
            )
            package_reject = str(package_validation.get("rejectReason") or "")
            if package_reject.startswith("Vision asset validation failed:"):
                return package_reject, validation
            pair_validation = validate_asset_pair_distinctness(package_validation, validation)
            if not pair_validation.get("isDistinctEnough"):
                return pair_validation.get("rejectReason") or "Package and dosage-form assets are not distinct", validation
        return "", validation

    def _strict_vision_reject_reason(self, vision_result: dict[str, Any] | None) -> str:
        if not isinstance(vision_result, dict):
            return "Llama 4 exact image verification did not run"
        if vision_result.get("policyVersion") != ASSET_VALIDATION_POLICY_VERSION:
            return "Llama 4 image verification used an outdated validation policy"
        if not vision_result.get("accepted"):
            return str(vision_result.get("rejectReason") or "Llama 4 image verification rejected this asset")
        if vision_result.get("isUnrelated"):
            return str(vision_result.get("rejectReason") or "Llama 4 marked this image as unrelated")
        if not vision_result.get("expectedTypeMatches"):
            return str(vision_result.get("rejectReason") or "Image does not match the requested asset slot")
        if not vision_result.get("brandMatches"):
            return str(vision_result.get("rejectReason") or "Medicine brand identity was not verified")
        if vision_result.get("requiresStrengthMatch") and not vision_result.get("strengthMatches"):
            return str(vision_result.get("rejectReason") or "Medicine strength was not verified")
        if vision_result.get("requiresDosageFormMatch") and not vision_result.get("dosageFormMatches"):
            return str(vision_result.get("rejectReason") or "Medicine dosage form was not verified")
        if not (vision_result.get("medicineNameVisible") or vision_result.get("saltVisible")):
            return str(vision_result.get("rejectReason") or "Visible medicine identity text was not verified")
        if not vision_result.get("qualityOk"):
            return str(vision_result.get("rejectReason") or "Image quality was not verified")
        if not vision_result.get("safetyOk"):
            return str(vision_result.get("rejectReason") or "Image safety was not verified")
        if float(vision_result.get("confidence") or 0.0) < self.settings.asset_validation_min_confidence:
            return f"Llama 4 confidence below threshold ({float(vision_result.get('confidence') or 0.0):.2f} < {self.settings.asset_validation_min_confidence:.2f})"
        return ""

    def _vision_result_is_strictly_verified(self, vision_result: dict[str, Any] | None) -> bool:
        return not self._strict_vision_reject_reason(vision_result)

    def _refresh_record_vision_result(
        self,
        key: str,
        record: AssetRecord,
        asset_type: str,
        vision_result: dict[str, Any],
    ) -> None:
        confidence = max(
            float(record.confidence_score or 0.0),
            float(vision_result.get("finalScore") or vision_result.get("confidence") or 0.0),
        )
        verified = self._vision_result_is_strictly_verified(vision_result)
        updated = replace(
            record,
            confidence_score=max(0.0, min(1.0, confidence)),
            approval_status="llama4_verified_exact" if verified else "image_review_required",
            vision_result=vision_result,
            review_required=not verified,
            refreshed_at=utc_now(),
        )
        self.store.upsert_asset(key, updated, force_refresh=True)

    def _source_domain_preference_score(self, source_domain: str) -> int:
        domain = source_domain.casefold().removeprefix("www.")
        for index, preferred in enumerate(PREFERRED_PHARMACY_DOMAINS):
            if domain == preferred or domain.endswith(f".{preferred}"):
                return max(2, 14 - index * 2)
        return 0

    def _cached_image_reject_reason(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        path: Path,
        record: AssetRecord | None,
        distinct_from: Path | None,
        distinct_source_url: str = "",
    ) -> str:
        if record and record.provider == "template_missing_verified_image_card":
            return "cached missing-image card is regenerated after a fresh validation attempt"
        if record and record.provider == "verified_medicine_identity_card":
            return "cached generated medicine card is no longer allowed"
        if record and record.provider == "local_generic_dosage_form":
            return "cached generic fallback image is no longer allowed"
        if record and _image_url_has_placeholder_hint(record.source_url):
            return "cached image is a placeholder or missing-product image"
        if record and _image_url_conflicts_with_requested_medicine(medicine, record.source_url):
            return "cached image source points to a different medicine"
        if record and _image_url_is_opaque_product_asset(medicine, record.source_url) and not _image_url_contains_requested_brand(medicine, record.source_url):
            source_domain = record.source_domain.casefold().removeprefix("www.")
            if not any(source_domain == domain or source_domain.endswith(f".{domain}") for domain in CORE_OPAQUE_IMAGE_DOMAINS):
                return "cached opaque image source is not from a verifiable core medicine image provider"
        if asset_type != "package":
            if distinct_from and distinct_from.exists() and _images_are_duplicate_like(path, distinct_from):
                return "cached dosage-form image duplicates the package image"
            if record:
                text = f"{record.source_url} {record.provider} {record.source_domain} {record.approval_status}"
                if distinct_source_url and _urls_are_similar(record.source_url, distinct_source_url):
                    return "cached dosage-form image URL matches the package image"
                if _requires_exact_strip(medicine) and not _has_dosage_form_hint(medicine, text):
                    return "cached dosage-form image does not include strip/blister evidence"
        return ""

    def _local_image_reject_reason(
        self,
        medicine: MedicineVideoInput,
        asset_type: str,
        path: Path,
        distinct_from: Path | None,
    ) -> str:
        if asset_type != "package" and distinct_from and distinct_from.exists() and _images_are_duplicate_like(path, distinct_from):
            return "local dosage-form image duplicates the package image"
        return ""

    def _tighten_dosage_image_with_verified_crop(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        source_path: Path,
        target: Path,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate,
        fallback_validation: ValidationResult,
    ) -> tuple[Path, ValidationResult] | None:
        try:
            source = Image.open(source_path).convert("RGB")
        except Exception:
            return None
        source_area = source.width * source.height
        if source_area <= 0:
            return None

        accepted: list[tuple[float, Path, ValidationResult]] = []
        for index, box in enumerate(self._package_dosage_crop_boxes(source_path)):
            x1, y1, x2, y2 = box
            crop_area = max(0, x2 - x1) * max(0, y2 - y1)
            if crop_area <= 0 or crop_area > source_area * 0.82:
                continue
            crop_path = target.parent / f".{target.stem}.verified_strip_crop.{index}{target.suffix}"
            try:
                crop = source.crop(box)
                crop.save(crop_path, quality=94)
                validation = self.validator.validate_image(crop_path, candidate.url, exact_query_match=True, source_domain=candidate.source_domain)
                can_try_vision = (
                    validation.valid
                    or (
                        self.settings.enable_vision_image_validation
                        and validate_medicine_asset_image is not None
                        and validation.width >= 300
                        and validation.height >= 300
                        and "confidence below threshold" in validation.reason.casefold()
                    )
                )
                if not can_try_vision:
                    crop_path.unlink(missing_ok=True)
                    continue
                visual_reject_reason = self._asset_visual_reject_reason("tablet", crop_path)
                if visual_reject_reason:
                    crop_path.unlink(missing_ok=True)
                    continue
                vision_reject_reason, vision_validation = self._vision_asset_reject_reason(medicine, "tablet", crop_path, candidate, None)
                if vision_reject_reason:
                    crop_path.unlink(missing_ok=True)
                    continue
                if vision_validation:
                    validation = ValidationResult(
                        True,
                        max(validation.score, float(vision_validation.get("finalScore", vision_validation.get("confidence", validation.score)) or validation.score)),
                        "Dosage crop accepted by Llama 4 vision validation",
                        validation.width,
                        validation.height,
                        validation.duration,
                    )
                if validation.valid:
                    accepted.append((validation.score, crop_path, validation))
                else:
                    crop_path.unlink(missing_ok=True)
            except Exception:
                crop_path.unlink(missing_ok=True)

        if not accepted:
            return None
        accepted.sort(key=lambda item: item[0], reverse=True)
        _, best_crop, best_validation = accepted[0]
        for _, path, _ in accepted[1:]:
            path.unlink(missing_ok=True)
        return best_crop, ValidationResult(
            True,
            max(best_validation.score, fallback_validation.score),
            "Verified dosage/strip crop derived from fetched product image",
            best_validation.width,
            best_validation.height,
            best_validation.duration,
        )

    def _package_dosage_crop_boxes(self, package_path: Path) -> list[tuple[int, int, int, int]]:
        try:
            image = Image.open(package_path).convert("RGB")
        except Exception:
            return []
        width, height = image.size
        if width < 300 or height < 300:
            return []

        # Ignore the bottom band first; search-result composites often contain source watermarks there.
        work_bottom = max(1, int(height * 0.86))
        pixels = image.load()
        column_hits: list[int] = []
        for x in range(width):
            hits = 0
            for y in range(work_bottom):
                r, g, b = pixels[x, y]
                if not (r > 245 and g > 245 and b > 245):
                    hits += 1
            column_hits.append(hits)

        threshold = max(6, int(work_bottom * 0.018))
        segments: list[tuple[int, int]] = []
        start: int | None = None
        gap = 0
        max_gap = max(8, width // 90)
        for x, hits in enumerate(column_hits):
            if hits >= threshold:
                if start is None:
                    start = x
                gap = 0
            elif start is not None:
                gap += 1
                if gap > max_gap:
                    end = x - gap
                    if end - start > width * 0.08:
                        segments.append((start, end))
                    start = None
                    gap = 0
        if start is not None and width - start > width * 0.08:
            segments.append((start, width - 1))

        boxes: list[tuple[int, int, int, int]] = []
        for start_x, end_x in segments:
            y_values: list[int] = []
            for x in range(max(0, start_x), min(width, end_x + 1)):
                for y in range(work_bottom):
                    r, g, b = pixels[x, y]
                    if not (r > 245 and g > 245 and b > 245):
                        y_values.append(y)
            if not y_values:
                continue
            y1 = max(0, min(y_values) - int(height * 0.035))
            y2 = min(work_bottom, max(y_values) + int(height * 0.035))
            x1 = max(0, start_x - int(width * 0.025))
            x2 = min(width, end_x + int(width * 0.025))
            if x2 - x1 >= 180 and y2 - y1 >= 180:
                boxes.append((x1, y1, x2, y2))

        # Prefer non-leftmost components for composite package+strip images, then try broad right-side crops.
        boxes = sorted(boxes, key=lambda box: (box[0], (box[2] - box[0]) * (box[3] - box[1])), reverse=True)
        broad_boxes = [
            (int(width * 0.46), int(height * 0.08), width, int(height * 0.86)),
            (int(width * 0.38), int(height * 0.08), width, int(height * 0.86)),
            (0, int(height * 0.08), width, int(height * 0.86)),
        ]
        deduped: list[tuple[int, int, int, int]] = []
        for box in [*boxes, *broad_boxes]:
            x1, y1, x2, y2 = box
            if x2 - x1 < 180 or y2 - y1 < 180:
                continue
            if box not in deduped:
                deduped.append(box)
        return deduped[:6]

    def _derive_dosage_image_from_package(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        package_path: Path,
        package_record: AssetRecord | None,
        force_refresh: bool,
        failures: list[dict[str, Any]],
    ) -> Path | None:
        key = _asset_key("medicine_image", slug, "tablet")
        target = self.settings.asset_cache_dir / "medicines" / slug / "tablet.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        best_failure = "No verified dosage crop found inside package image"

        try:
            source = Image.open(package_path).convert("RGB")
        except Exception as exc:
            failures.append({"medicineName": medicine.medicine_name, "assetType": "dosage form image", "stage": "validation", "reason": f"Unable to inspect package image for dosage crop: {exc}"})
            return None

        accepted: list[tuple[float, Path, ValidationResult, dict[str, Any] | None]] = []
        checked: list[Path] = []
        for index, box in enumerate(self._package_dosage_crop_boxes(package_path)):
            crop_path = target.parent / f".{target.stem}.package_crop.{index}{target.suffix}"
            try:
                crop = source.crop(box)
                crop.save(crop_path, quality=94)
                checked.append(crop_path)
                validation = self.validator.validate_image(
                    crop_path,
                    package_record.source_url if package_record else str(package_path),
                    exact_query_match=True,
                    source_domain=package_record.source_domain if package_record else "local",
                )
                if not validation.valid:
                    best_failure = validation.reason
                    continue
                visual_reject_reason = self._asset_visual_reject_reason("tablet", crop_path)
                if visual_reject_reason:
                    best_failure = visual_reject_reason
                    continue
                vision_reject_reason, vision_validation = self._vision_asset_reject_reason(
                    medicine,
                    "tablet",
                    crop_path,
                    AssetRecord(
                        asset_type="tablet_image",
                        medicine_name=medicine.medicine_name,
                        medicine_slug=slug,
                        route_template="",
                        local_path=str(crop_path),
                        source_url=f"{package_record.source_url if package_record else package_path}#dosage-crop-{index}",
                        provider="derived_from_package_image",
                        source_domain=package_record.source_domain if package_record else "local",
                        confidence_score=validation.score,
                        fetched_at=utc_now(),
                        approval_status="vision_crop_candidate",
                    ),
                    distinct_from=None,
                )
                if vision_reject_reason:
                    best_failure = vision_reject_reason
                    continue
                if vision_validation:
                    validation = ValidationResult(
                        True,
                        max(validation.score, float(vision_validation.get("finalScore", vision_validation.get("confidence", validation.score)) or validation.score)),
                        "Dosage crop accepted by rule and Llama 4 vision validation",
                        validation.width,
                        validation.height,
                        validation.duration,
                    )
                accepted.append((validation.score, crop_path, validation, vision_validation))
            except Exception as exc:
                best_failure = str(exc)

        if accepted:
            accepted.sort(key=lambda item: item[0], reverse=True)
            _, best_path, best_validation, best_vision = accepted[0]
            if best_path != target:
                best_path.replace(target)
            for path in checked:
                if path != target and path.exists():
                    path.unlink(missing_ok=True)
            record = AssetRecord(
                asset_type="tablet_image",
                medicine_name=medicine.medicine_name,
                medicine_slug=slug,
                route_template="",
                local_path=str(target),
                source_url=f"{package_record.source_url if package_record else package_path}#dosage-crop",
                provider="derived_from_package_image",
                source_domain=package_record.source_domain if package_record else "local",
                confidence_score=best_validation.score,
                fetched_at=utc_now(),
                approval_status="llama4_verified_dosage_crop",
                derived_crop=True,
                vision_result=best_vision,
                refreshed_at=utc_now(),
            )
            self.store.upsert_asset(key, record, force_refresh=force_refresh)
            return target

        for path in checked:
            path.unlink(missing_ok=True)
        failures.append({"medicineName": medicine.medicine_name, "assetType": "dosage form image", "stage": "vision_validation", "reason": best_failure})
        return None

    def _failure_reason_for_asset(self, failures: list[dict[str, Any]], medicine_name: str, asset_type: str) -> str:
        expected = {"package image"} if asset_type == "package" else {"tablet image", "dosage form image"}
        for failure in reversed(failures):
            if failure.get("medicineName") != medicine_name:
                continue
            if str(failure.get("assetType") or "").casefold() not in expected:
                continue
            stage = str(failure.get("stage") or "").strip()
            reason = str(failure.get("reason") or "").strip()
            if stage and reason:
                return f"{stage}: {reason}"
            return reason or stage or "No validated image was found."
        return "No validated image was found."

    def _asset_warnings_from_failures(self, medicine: MedicineVideoInput, failures: list[dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        seen: set[str] = set()
        for failure in failures:
            if failure.get("medicineName") != medicine.medicine_name:
                continue
            asset_type = str(failure.get("assetType") or "image").strip()
            stage = str(failure.get("stage") or "validation").strip()
            reason = str(failure.get("reason") or "No validated image was found.").strip()
            warning = f"{asset_type}: {stage} failed - {reason}"
            if warning not in seen:
                seen.add(warning)
                warnings.append(warning)
        return warnings

    def _create_missing_image_card(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        asset_type: str,
        reason: str,
        force_refresh: bool,
    ) -> Path:
        key = _asset_key("medicine_image", slug, asset_type)
        target = self.settings.asset_cache_dir / "medicines" / slug / f"{asset_type}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)

        is_package = asset_type == "package"
        title = "VALID PACKAGE IMAGE NOT FOUND" if is_package else "VALID DOSAGE / STRIP IMAGE NOT FOUND"
        slot = "Medicine package image" if is_package else "Dosage form / strip image"

        image = Image.new("RGB", (720, 480), "#F4FBF7")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((24, 24, 696, 456), radius=34, fill="#FFFFFF", outline="#F2C46D", width=4)
        draw.rounded_rectangle((44, 44, 676, 112), radius=22, fill="#7A3F00")
        draw.text((66, 62), title, font=load_font(22, bold=True), fill="#FFF8E8")
        draw.text((66, 92), "Template guide generated without showing an unverified medicine image", font=load_font(13), fill="#FFE2A6")

        label_font = load_font(13, bold=True)
        value_font = load_font(24, bold=True)
        body_font = load_font(18)
        muted = "#6F5840"
        dark = "#063B2B"

        y = 142
        draw.text((54, y), "MEDICINE", font=label_font, fill=muted)
        y += 22
        y = draw_wrapped_text(draw, medicine.medicine_name, (54, y), value_font, dark, 610, max_lines=2) + 14

        draw.text((54, y), "IMAGE SLOT", font=label_font, fill=muted)
        y += 22
        y = draw_wrapped_text(draw, slot, (54, y), body_font, dark, 610, max_lines=1) + 14

        draw.text((54, y), "VALIDATION FAILURE", font=label_font, fill=muted)
        y += 22
        y = draw_wrapped_text(draw, reason or "No validated image was found.", (54, y), body_font, "#4A3220", 610, max_lines=4) + 16

        draw.rounded_rectangle((44, 402, 676, 438), radius=16, fill="#FFF7E2", outline="#F2C46D")
        draw_wrapped_text(
            draw,
            "Do not identify this medicine visually from the image panel. Follow the written prescription details.",
            (58, 412),
            load_font(13, bold=True),
            "#6D4300",
            604,
            max_lines=1,
        )
        image.save(target, quality=92)

        record = AssetRecord(
            asset_type=f"{asset_type}_missing_image_card",
            medicine_name=medicine.medicine_name,
            medicine_slug=slug,
            route_template="",
            local_path=str(target),
            source_url=f"local://valid-image-not-found/{asset_type}",
            provider="template_missing_verified_image_card",
            source_domain="local",
            confidence_score=0.0,
            fetched_at=utc_now(),
            approval_status="missing_verified_image",
            review_required=True,
            refreshed_at=utc_now(),
        )
        self.store.upsert_asset(key, record, force_refresh=force_refresh)
        return target

    def _create_medicine_identity_card(
        self,
        medicine: MedicineVideoInput,
        slug: str,
        asset_type: str,
        force_refresh: bool,
        image_failures: list[dict[str, Any]],
    ) -> Path:
        key = _asset_key("medicine_image", slug, asset_type)
        target = self.settings.asset_cache_dir / "medicines" / slug / f"{asset_type}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)

        title = "VERIFIED MEDICINE DETAILS" if asset_type == "package" else "VERIFIED DOSAGE DETAILS"
        subtitle = "Verified from selected prescription fields"

        image = Image.new("RGB", (720, 480), "#F4FBF7")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((24, 24, 696, 456), radius=34, fill="#FFFFFF", outline="#CFE5DA", width=3)
        draw.rounded_rectangle((44, 44, 676, 106), radius=20, fill="#073B2A")
        draw.text((66, 62), title, font=load_font(22, bold=True), fill="#FFFFFF")
        draw.text((66, 92), subtitle, font=load_font(13), fill="#BDEBD2")

        y = 134
        label_font = load_font(13, bold=True)
        value_font = load_font(24, bold=True)
        body_font = load_font(18)
        muted = "#5B776C"
        dark = "#063B2B"

        draw.text((54, y), "MEDICINE", font=label_font, fill=muted)
        y += 22
        y = draw_wrapped_text(draw, medicine.medicine_name, (54, y), value_font, dark, 610, max_lines=2) + 10

        if medicine.active_salts:
            draw.text((54, y), "ACTIVE INGREDIENTS", font=label_font, fill=muted)
            y += 22
            y = draw_wrapped_text(draw, medicine.active_salts, (54, y), body_font, dark, 610, max_lines=2) + 10

        details = [
            ("Dose", medicine.dosage),
            ("Frequency", medicine.frequency),
            ("Timing", medicine.timing),
            ("Form", medicine.form or _form_kind(medicine).replace("_", " ")),
            ("Route", medicine.route or detect_route_template(medicine).replace("_", " ")),
        ]
        x_positions = (54, 376)
        for index, (label, value) in enumerate(details):
            x = x_positions[index % 2]
            row_y = y + (index // 2) * 58
            draw.text((x, row_y), label.upper(), font=label_font, fill=muted)
            draw_wrapped_text(draw, value or "As prescribed", (x, row_y + 20), body_font, dark, 284, max_lines=1)

        footer = "Unverified internet images are not shown for patient safety."
        draw.rounded_rectangle((44, 410, 676, 438), radius=14, fill="#EAF6F0", outline="#CFE5DA")
        draw_wrapped_text(draw, footer, (58, 417), load_font(13), "#45685A", 604, max_lines=1)
        image.save(target, quality=92)

        record = AssetRecord(
            asset_type="medicine_identity_card",
            medicine_name=medicine.medicine_name,
            medicine_slug=slug,
            route_template="",
            local_path=str(target),
            source_url=f"local://verified-medicine-details/{asset_type}",
            provider="verified_medicine_identity_card",
            source_domain="local",
            confidence_score=1.0,
            fetched_at=utc_now(),
            approval_status="identity_card",
        )
        self.store.upsert_asset(key, record, force_refresh=force_refresh)
        return target

    def _confidence_label(self, slug: str, asset_type: str) -> str:
        record = self.store.get_asset(_asset_key("medicine_image", slug, asset_type))
        if asset_type == "package":
            if record and record.provider == "template_missing_verified_image_card":
                return "Valid image not found"
            if record and record.provider == "verified_medicine_identity_card":
                return "Verified details only"
            if record and self._vision_result_is_strictly_verified(record.vision_result):
                return "Exact package match"
            return "Image review required"
        if record and record.provider == "template_missing_verified_image_card":
            return "Valid image not found"
        if record and record.provider == "verified_medicine_identity_card":
            return "Image review required"
        if record and self._vision_result_is_strictly_verified(record.vision_result):
            return "Verified dosage/strip image" if record.derived_crop else "Exact dosage form match"
        return "Image review required"

    def _is_allowed_source_domain(self, source_domain: str) -> bool:
        domain = source_domain.casefold().removeprefix("www.")
        allowed_domains = (*self.settings.approved_image_domains, *TRUSTED_MEDICINE_IMAGE_DOMAINS)
        return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains)

    def _is_rejected_result_text(self, text: str) -> bool:
        lower = text.casefold()
        return any(part in lower for part in SERPAPI_REJECT_PARTS)

    def _find_existing_image(self, medicine: MedicineVideoInput, slug: str, asset_type: str) -> Path | None:
        cache_dir = self.settings.asset_cache_dir / "medicines" / slug
        legacy_kind = "packages" if asset_type == "package" else "products"
        legacy_dir = self.settings.assets_dir / "medicine_images" / legacy_kind
        stems = [asset_type, slug]
        for folder in (cache_dir, legacy_dir):
            for stem in stems:
                for suffix in (".jpg", ".jpeg", ".png", ".webp"):
                    path = folder / f"{stem}{suffix}"
                    if path.exists():
                        return path
        return None

    def _save_record(
        self,
        key: str,
        asset_type: str,
        path: Path,
        candidate: ApprovedPharmacyImageCandidate | SerpApiImageCandidate | BraveImageCandidate | ImageCandidate | VideoCandidate,
        validation: ValidationResult,
        medicine: MedicineVideoInput | None = None,
        slug: str = "",
        route_template: str = "",
        force_refresh: bool = False,
        gallery_id: str = "",
        ocr_text: str = "",
        vision_result: dict[str, Any] | None = None,
        derived_crop: bool = False,
        review_required: bool = False,
    ) -> None:
        is_medicine_image = asset_type in {"package_image", "tablet_image"}
        strict_verified = self._vision_result_is_strictly_verified(vision_result) if is_medicine_image else True
        record = AssetRecord(
            asset_type=asset_type,
            medicine_name=medicine.medicine_name if medicine else "",
            medicine_slug=slug,
            route_template=route_template,
            local_path=str(path),
            source_url=candidate.url,
            provider=candidate.provider,
            source_domain=candidate.source_domain,
            confidence_score=validation.score,
            fetched_at=utc_now(),
            approval_status="llama4_verified_exact" if is_medicine_image and strict_verified else ("image_review_required" if is_medicine_image else "auto_resolved"),
            gallery_id=gallery_id,
            ocr_text=ocr_text,
            vision_result=vision_result,
            derived_crop=derived_crop,
            review_required=review_required or (is_medicine_image and not strict_verified),
            refreshed_at=utc_now(),
        )
        self.store.upsert_asset(key, record, force_refresh=force_refresh)


def resolve_assets_for_prescription(prescription_data: PrescriptionVideoInput | dict[str, Any], force_refresh: bool = False) -> ResolvedPrescriptionAssets:
    return StrictAssetResolver().resolve_prescription(prescription_data, force_refresh=force_refresh)
