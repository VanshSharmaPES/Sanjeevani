#!/usr/bin/env python3
"""Validate one medicine asset image with the Sanjeevani vision validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_engine import validate_medicine_asset_image


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a local medicine package/strip/dosage image.")
    parser.add_argument("--image", required=True, help="Path to the local image file.")
    parser.add_argument("--medicine", required=True, help="Expected medicine name.")
    parser.add_argument("--salt", default="", help="Expected active salts/ingredients.")
    parser.add_argument(
        "--type",
        default="unknown",
        choices=("package", "strip", "dosage_form", "human_demo", "unknown"),
        help="Expected asset type.",
    )
    parser.add_argument("--debug", action="store_true", help="Append result to asset validation debug log.")
    args = parser.parse_args()

    image_path = Path(args.image)
    result = validate_medicine_asset_image(
        image_path.read_bytes(),
        args.medicine,
        args.salt,
        args.type,
        context={"local_path": str(image_path), "title": f"{args.medicine} {args.type} test image"},
        debug=args.debug,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    if result.get("accepted"):
        print(f"ACCEPTED score={result.get('finalScore')} confidence={result.get('confidence')}")
        return 0
    print(f"REJECTED reason={result.get('rejectReason')}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
