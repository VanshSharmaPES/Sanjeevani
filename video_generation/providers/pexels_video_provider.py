"""Pexels-backed route demonstration video provider."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from video_generation.config import VideoGenerationSettings


ROUTE_QUERIES = {
    "tablet_oral": "person taking pill with water close up hands medical",
    "capsule_oral": "person taking pill with water close up hands medical",
    "syrup_oral": "person taking liquid medicine spoon close up",
    "eye_drops": "person applying eye drops close up",
    "nasal_drops": "person using nasal spray close up",
    "nasal_spray": "person using nasal spray close up",
    "inhaler": "person using inhaler close up",
    "ointment_topical": "person applying cream medicine close up",
}


@dataclass(frozen=True)
class VideoCandidate:
    url: str
    provider: str
    source_domain: str
    width: int
    height: int
    duration: float


class PexelsVideoProvider:
    provider_name = "pexels"

    def __init__(self, settings: VideoGenerationSettings) -> None:
        self.settings = settings

    def search(self, route_template: str) -> list[VideoCandidate]:
        if not self.settings.pexels_api_key:
            return []
        query = ROUTE_QUERIES.get(route_template, ROUTE_QUERIES["tablet_oral"])
        params = urllib.parse.urlencode({"query": query, "per_page": 8, "orientation": "landscape"})
        request = urllib.request.Request(
            f"https://api.pexels.com/videos/search?{params}",
            headers={"Authorization": self.settings.pexels_api_key, "User-Agent": "SanjeevaniVideoAssetResolver/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        candidates: list[VideoCandidate] = []
        for item in payload.get("videos", []):
            duration = float(item.get("duration") or 0)
            files = sorted(
                item.get("video_files", []),
                key=lambda file: int(file.get("width") or 0) * int(file.get("height") or 0),
                reverse=True,
            )
            for file in files:
                url = str(file.get("link") or "")
                width = int(file.get("width") or 0)
                height = int(file.get("height") or 0)
                if url and width >= 640 and height >= 360:
                    domain = urlparse(url).netloc.casefold().removeprefix("www.")
                    candidates.append(VideoCandidate(url, self.provider_name, domain, width, height, duration))
                    break
        return candidates

    def download(self, candidate: VideoCandidate, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".download" + target.suffix)
        request = urllib.request.Request(candidate.url, headers={"User-Agent": "SanjeevaniVideoAssetResolver/1.0"})
        with urllib.request.urlopen(request, timeout=40) as response, temp.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
        temp.replace(target)
        return target

