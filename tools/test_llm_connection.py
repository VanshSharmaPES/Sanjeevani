#!/usr/bin/env python3
"""Check whether Sanjeevani can call the configured LLM provider."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_engine import ANALYSIS_MODEL, client


def main() -> int:
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": "Return only OK."},
                {"role": "user", "content": "Health check"},
            ],
            temperature=0,
            max_tokens=8,
        )
    except Exception as exc:
        print(f"LLM FAILED: {exc}")
        return 2
    content = (response.choices[0].message.content or "").strip()
    print(f"LLM OK: {content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
