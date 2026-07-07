"""SerpAPI Google Images provider for medicine package/tablet assets."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from video_generation.config import VideoGenerationSettings


@dataclass(frozen=True)
class SerpApiImageCandidate:
    url: str
    provider: str
    source_domain: str
    title: str
    page_url: str = ""
    source: str = ""
    thumbnail_url: str = ""
    snippet: str = ""
    query_used: str = ""
    raw_rank: int = 0


class SerpApiImageProvider:
    provider_name = "serpapi_google_images"

    def __init__(self, settings: VideoGenerationSettings) -> None:
        self.settings = settings

    def search(
        self,
        medicine_name: str,
        asset_type: str,
        queries: list[str] | None = None,
        per_query_limit: int = 8,
        max_candidates: int = 30,
    ) -> list[SerpApiImageCandidate]:
        if not self.settings.serpapi_api_key:
            return []
        candidates: list[SerpApiImageCandidate] = []
        seen_urls: set[str] = set()
        last_error: Exception | None = None
        search_queries = queries or self._queries(medicine_name, asset_type)
        for query in search_queries:
            try:
                query_candidates = self._search_query(query)
            except Exception as exc:
                last_error = exc
                continue
            for candidate in query_candidates[: max(1, per_query_limit)]:
                identity = candidate.url.casefold()
                if identity in seen_urls:
                    continue
                seen_urls.add(identity)
                candidates.append(candidate)
                if len(candidates) >= max_candidates:
                    return candidates
        if candidates:
            return candidates
        if last_error:
            raise last_error
        return candidates

    def _queries(self, medicine_name: str, asset_type: str) -> list[str]:
        lower_name = medicine_name.casefold()
        asset_type = asset_type.strip().casefold()
        if asset_type == "package":
            return [
                f"{medicine_name} site:1mg.com medicine",
                f"{medicine_name} site:pharmeasy.in medicine",
                f"{medicine_name} medicine box pack",
            ]
        elif asset_type == "strip":
            return [
                f"{medicine_name} strip blister tablet capsule",
                f"{medicine_name} site:1mg.com strip blister",
                f"{medicine_name} site:netmeds.com strip blister",
            ]
        elif asset_type in {"dosage_form", "tablet", "product", "product_image"}:
            if any(term in lower_name for term in ("ointment", "cream", "gel", "lotion", "topical")):
                return [
                    f"{medicine_name} tube ointment cream",
                    f"{medicine_name} medicine product image",
                    f"{medicine_name} site:1mg.com",
                ]
            elif any(term in lower_name for term in ("syrup", "suspension")):
                return [
                    f"{medicine_name} syrup bottle",
                    f"{medicine_name} medicine product image",
                    f"{medicine_name} site:1mg.com",
                ]
            elif any(term in lower_name for term in ("eye drops", "eyedrops", "ear drops", "eardrops", "nasal", "drops", "drop")):
                return [
                    f"{medicine_name} drops bottle nozzle",
                    f"{medicine_name} medicine product image",
                    f"{medicine_name} site:1mg.com",
                ]
            elif any(term in lower_name for term in ("inhaler", "spray")):
                return [
                    f"{medicine_name} inhaler product image",
                    f"{medicine_name} inhaler device medicine",
                    f"{medicine_name} site:1mg.com inhaler",
                ]
            elif "capsule" in lower_name:
                return [
                    f"{medicine_name} capsule strip blister",
                    f"{medicine_name} site:1mg.com strip blister",
                    f"{medicine_name} medicine product image",
                ]
            else:
                return [
                    f"{medicine_name} strip blister tablet",
                    f"{medicine_name} site:1mg.com strip blister",
                    f"{medicine_name} medicine product image",
                ]
        elif any(term in lower_name for term in ("ointment", "cream", "gel", "lotion", "topical")):
            return [f"{medicine_name} tube ointment cream", f"{medicine_name} medicine product image"]
        elif any(term in lower_name for term in ("syrup", "suspension", "drops", "drop", "inhaler", "spray")):
            return [f"{medicine_name} bottle dosage form", f"{medicine_name} medicine product image"]
        elif "capsule" in lower_name:
            return [f"{medicine_name} capsule strip blister", f"{medicine_name} medicine product image"]
        else:
            return [f"{medicine_name} strip blister tablet", f"{medicine_name} medicine product image"]

    def _search_query(self, query: str) -> list[SerpApiImageCandidate]:
        params = urllib.parse.urlencode(
            {
                "engine": "google_images",
                "q": query,
                "api_key": self.settings.serpapi_api_key,
                "gl": "in",
                "hl": "en",
                "safe": "active",
                "ijn": "0",
            }
        )
        request = urllib.request.Request(
            f"https://serpapi.com/search.json?{params}",
            headers={"Accept": "application/json", "User-Agent": "SanjeevaniVideoAssetResolver/1.0"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if isinstance(payload.get("error"), str):
            raise ValueError(payload["error"])

        candidates: list[SerpApiImageCandidate] = []
        results = payload.get("images_results") or payload.get("image_results") or []
        for rank, item in enumerate(results, start=1):
            image_url = str(item.get("original") or item.get("thumbnail") or "")
            page_url = str(item.get("link") or item.get("source") or "")
            if not image_url:
                continue
            source_domain = urlparse(page_url or image_url).netloc.casefold().removeprefix("www.")
            candidates.append(
                SerpApiImageCandidate(
                    url=image_url,
                    provider=self.provider_name,
                    source_domain=source_domain,
                    title=str(item.get("title") or ""),
                    page_url=page_url,
                    source=str(item.get("source") or ""),
                    thumbnail_url=str(item.get("thumbnail") or ""),
                    snippet=str(item.get("snippet") or ""),
                    query_used=query,
                    raw_rank=rank,
                )
            )
        return candidates

    def download(self, candidate: SerpApiImageCandidate, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".download" + target.suffix)
        request = urllib.request.Request(candidate.url, headers={"User-Agent": "SanjeevaniVideoAssetResolver/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response, temp.open("wb") as handle:
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
