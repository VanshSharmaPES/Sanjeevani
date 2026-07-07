"""Generate a sample Sanjeevani medication video guide."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_generation import generate_prescription_videos


SAMPLE = {
    "patientName": "Patient",
    "language": "hi",
    "medicines": [
        {
            "medicineName": "Crocin Advance Tablet",
            "activeSalts": "Paracetamol (500mg)",
            "dosage": "1 Tablet",
            "frequency": "Twice a day (1-0-1)",
            "timing": "After meals (PC)",
            "duration": "As prescribed",
            "doctorNotes": "Consult prescription details for specific instructions.",
        }
    ],
}


if __name__ == "__main__":
    results = generate_prescription_videos(SAMPLE)
    for result in results:
        if result.success:
            print(f"[INFO] Generated video: {result.video_path}")
            print(f"[INFO] Generated subtitles: {result.subtitle_path}")
            for warning in result.warnings:
                print(f"[WARN] {warning}")
        else:
            print(f"[ERROR] {result.medicine_name}: {result.error}")
            raise SystemExit(1)
