"""Brave Search image provider for medicine package/tablet assets."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from video_generation.config import VideoGenerationSettings


@dataclass(frozen=True)
class BraveImageCandidate:
    url: str
    provider: str
    source_domain: str
    title: str
    page_url: str = ""


class BraveImageProvider:
    provider_name = "brave_search"

    def __init__(self, settings: VideoGenerationSettings) -> None:
        self.settings = settings

    def search(self, medicine_name: str, asset_type: str) -> list[BraveImageCandidate]:
        if not self.settings.brave_search_api_key:
            return []
        query = (
            f"{medicine_name} medicine package strip"
            if asset_type == "package"
            else f"{medicine_name} tablet strip product image"
        )
        params = urllib.parse.urlencode(
            {
                "q": query,
                "count": 20,
                "country": "IN",
                "search_lang": "en",
                "safesearch": "strict",
                "spellcheck": "true",
            }
        )
        request = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/images/search?{params}",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.settings.brave_search_api_key,
                "User-Agent": "SanjeevaniVideoAssetResolver/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        candidates: list[BraveImageCandidate] = []
        for item in payload.get("results", []):
            image_url = (
                (item.get("properties") or {}).get("url")
                or (item.get("thumbnail") or {}).get("src")
                or item.get("image")
                or ""
            )
            page_url = str(item.get("url") or item.get("source") or "")
            if not image_url:
                continue
            source_domain = urlparse(page_url or image_url).netloc.casefold().removeprefix("www.")
            candidates.append(
                BraveImageCandidate(
                    url=str(image_url),
                    provider=self.provider_name,
                    source_domain=source_domain,
                    title=str(item.get("title") or ""),
                    page_url=page_url,
                )
            )
        return candidates

    def download(self, candidate: BraveImageCandidate, target: Path) -> Path:
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
