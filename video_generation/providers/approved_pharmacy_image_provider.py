"""Approved pharmacy-page image provider for branded Indian medicine assets."""

from __future__ import annotations

import html
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from video_generation.config import VideoGenerationSettings
from video_generation.utils import sanitize_filename


IMAGE_URL_PATTERN = re.compile(r"https?://[^\"'\\\s<>]+(?:jpg|jpeg|png|webp)(?:\?[^\"'\\\s<>]*)?", re.IGNORECASE)

KNOWN_PRODUCT_PAGES = {
    "dolo_500": [
        "https://www.1mg.com/drugs/dolo-500-tablet-26676",
    ],
    "dolo_500_tablet": [
        "https://www.1mg.com/drugs/dolo-500-tablet-26676",
    ],
    "dolo_650": [
        "https://www.1mg.com/drugs/dolo-650-tablet-74467",
    ],
    "dolo_650_tablet": [
        "https://www.1mg.com/drugs/dolo-650-tablet-74467",
    ],
}

PREFERRED_IMAGE_TOKENS = {
    "dolo_500": {
        "package": ("plotopezwmczsrdyy3nq", "h5qrkr7nuboytdf2bihb"),
        "tablet": ("sqv0zwlvafyxwst2r0i5",),
    },
    "dolo_500_tablet": {
        "package": ("plotopezwmczsrdyy3nq", "h5qrkr7nuboytdf2bihb"),
        "tablet": ("sqv0zwlvafyxwst2r0i5",),
    },
    "dolo_650": {
        "package": ("mu5bahqxfrp28cut6que",),
        "tablet": ("ko6rsu9xwrdb7hrmmszr",),
    },
    "dolo_650_tablet": {
        "package": ("mu5bahqxfrp28cut6que",),
        "tablet": ("ko6rsu9xwrdb7hrmmszr",),
    },
}

APPROVED_IMAGE_HOSTS = {
    "onemg.gumlet.io",
    "cdn01.pharmeasy.in",
    "images.apollo247.in",
}

REJECT_URL_PARTS = {
    "site-icons",
    "apple-touch-icon",
    "payment",
    "wallet",
    "amazon",
    "pay",
    "marketing",
    "external_link",
    "dopamine-assets",
    "static/images",
    "logo",
    "banner",
    "pd-cms",
    "cms/pictures",
    "mobile404",
    "default_image",
    "noimage",
    "no-image",
    "placeholder",
    "medicine_image",
    "generalwarnings",
    "pregnancy",
    "alcohol",
    "breastfeeding",
    "conditions/",
    "blog/",
    "avatar",
    "doctor",
    "expert",
    "profile",
    "user",
}

ONEMG_PRODUCT_HINTS = (
    "/a_ignore",
    "l_watermark",
    "watermark",
    "/cropped/",
    "w_480",
    "h_480",
    "c_fit",
)


@dataclass(frozen=True)
class ApprovedPharmacyImageCandidate:
    url: str
    provider: str
    source_domain: str
    title: str
    page_url: str = ""
    source: str = ""


class ApprovedPharmacyImageProvider:
    provider_name = "approved_pharmacy_page"

    def __init__(self, settings: VideoGenerationSettings) -> None:
        self.settings = settings

    def search(self, medicine_name: str, asset_type: str) -> list[ApprovedPharmacyImageCandidate]:
        slug = sanitize_filename(medicine_name)
        pages = KNOWN_PRODUCT_PAGES.get(slug, [])
        candidates: list[ApprovedPharmacyImageCandidate] = []
        for page_url in pages:
            candidates.extend(self._extract_candidates(page_url, medicine_name, asset_type))
        preferred = PREFERRED_IMAGE_TOKENS.get(slug, {}).get(asset_type, ())
        if preferred:
            exact = [candidate for candidate in candidates if any(token in candidate.url for token in preferred)]
            if exact:
                candidates = exact
        return sorted(
            candidates,
            key=lambda candidate: self._score_url(candidate.url, asset_type, preferred),
            reverse=True,
        )

    def _extract_candidates(self, page_url: str, medicine_name: str, asset_type: str) -> list[ApprovedPharmacyImageCandidate]:
        request = urllib.request.Request(
            page_url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 SanjeevaniVideoAssetResolver/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8", errors="ignore")

        seen: set[str] = set()
        results: list[ApprovedPharmacyImageCandidate] = []
        for raw_url in IMAGE_URL_PATTERN.findall(body):
            image_url = html.unescape(raw_url).replace("\\u002F", "/")
            image_url = image_url.split("&quot;")[0]
            parsed = urlparse(image_url)
            host = parsed.netloc.casefold().removeprefix("www.")
            path = parsed.path.casefold()
            if host not in APPROVED_IMAGE_HOSTS:
                continue
            if any(part in path for part in REJECT_URL_PARTS):
                continue
            if image_url in seen:
                continue
            seen.add(image_url)
            score_hint = self._score_url(image_url, asset_type)
            if score_hint <= 0:
                continue
            results.append(
                ApprovedPharmacyImageCandidate(
                    url=image_url,
                    provider=self.provider_name,
                    source_domain=host,
                    title=f"{medicine_name} {asset_type} image",
                    page_url=page_url,
                    source="approved pharmacy product page",
                )
            )
        return results

    def _score_url(self, image_url: str, asset_type: str, preferred_tokens: tuple[str, ...] = ()) -> int:
        lower = image_url.casefold()
        score = 0
        if any(token.casefold() in lower for token in preferred_tokens):
            score += 50
        if "onemg.gumlet.io" in lower:
            score += 4
            if not any(part in lower for part in ONEMG_PRODUCT_HINTS):
                score -= 120
        if "/a_ignore" in lower or "watermark" in lower:
            score += 3
        if "l_watermark_346" in lower:
            score += 4
        if "w_480" in lower or "h_480" in lower:
            score += 2
        if lower.endswith((".jpg", ".jpeg")) or ".jpg?" in lower or ".jpeg?" in lower:
            score += 2
        if ".png" in lower:
            score -= 2
        if any(part in lower for part in REJECT_URL_PARTS):
            score -= 100
        if asset_type == "package":
            score += 1
        elif asset_type in {"tablet", "dosage_form", "strip"}:
            if any(part in lower for part in ("box-front", "box-back", "pack-front", "pack-back", "carton")):
                score -= 80
            if any(part in lower for part in ("bottle-front", "dropper", "nozzle", "strip", "blister", "tablet-front", "capsule", "tube", "inhaler")):
                score += 12
        return score

    def download(self, candidate: ApprovedPharmacyImageCandidate, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".download" + target.suffix)
        request = urllib.request.Request(
            candidate.url,
            headers={
                "Accept": "image/jpeg,image/png,image/webp,image/*,*/*;q=0.8",
                "Referer": candidate.page_url or "https://www.1mg.com/",
                "User-Agent": "Mozilla/5.0 SanjeevaniVideoAssetResolver/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response, temp.open("wb") as handle:
            total = 0
            while True:
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                total += len(chunk)
                if total > 8 * 1024 * 1024:
                    raise ValueError("Image exceeds 8MB limit")
                handle.write(chunk)
        temp.replace(target)
        return target
