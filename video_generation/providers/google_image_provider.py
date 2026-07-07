"""Google Custom Search image provider for branded medicine assets."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from video_generation.config import VideoGenerationSettings


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    provider: str
    source_domain: str
    title: str


class GoogleImageProvider:
    provider_name = "google_cse"

    def __init__(self, settings: VideoGenerationSettings) -> None:
        self.settings = settings

    def search(self, medicine_name: str, asset_type: str) -> list[ImageCandidate]:
        if not self.settings.google_cse_api_key or not self.settings.google_cse_id:
            return []
        if asset_type == "package":
            query = f"{medicine_name} medicine package"
        else:
            query = f"{medicine_name} tablet strip product image"
        params = urllib.parse.urlencode(
            {
                "key": self.settings.google_cse_api_key,
                "cx": self.settings.google_cse_id,
                "q": query,
                "searchType": "image",
                "num": 8,
                "safe": "active",
            }
        )
        request = urllib.request.Request(
            f"https://www.googleapis.com/customsearch/v1?{params}",
            headers={"User-Agent": "SanjeevaniVideoAssetResolver/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        candidates: list[ImageCandidate] = []
        for item in payload.get("items", []):
            url = str(item.get("link") or "")
            if not url:
                continue
            domain = urlparse(url).netloc.casefold().removeprefix("www.")
            candidates.append(ImageCandidate(url=url, provider=self.provider_name, source_domain=domain, title=str(item.get("title") or "")))
        return candidates

    def download(self, candidate: ImageCandidate, target: Path) -> Path:
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

