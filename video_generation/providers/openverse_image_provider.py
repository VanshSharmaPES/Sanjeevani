"""Openverse provider for licensed generic imagery.

In strict branded medicine mode, this provider is deliberately not used for
exact package/tablet assets unless a future metadata layer proves exact match.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class OpenverseCandidate:
    url: str
    provider: str
    source_domain: str
    title: str
    license: str


class OpenverseImageProvider:
    provider_name = "openverse"

    def search_generic(self, query: str) -> list[OpenverseCandidate]:
        params = urllib.parse.urlencode({"q": query, "page_size": 8})
        request = urllib.request.Request(
            f"https://api.openverse.engineering/v1/images/?{params}",
            headers={"User-Agent": "SanjeevaniVideoAssetResolver/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        candidates: list[OpenverseCandidate] = []
        for item in payload.get("results", []):
            url = str(item.get("url") or "")
            if not url:
                continue
            domain = urlparse(url).netloc.casefold().removeprefix("www.")
            candidates.append(
                OpenverseCandidate(
                    url=url,
                    provider=self.provider_name,
                    source_domain=domain,
                    title=str(item.get("title") or ""),
                    license=str(item.get("license") or ""),
                )
            )
        return candidates
