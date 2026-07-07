"""Print local dependency status for Sanjeevani video generation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_generation.utils import dependency_report


if __name__ == "__main__":
    report = dependency_report()
    for name, ok in report.items():
        print(f"{name}: {'OK' if ok else 'MISSING'}")
