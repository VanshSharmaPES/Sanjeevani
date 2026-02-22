#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic script to test the prescription analysis pipeline."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from ai_engine import (
    _call_vision_model_freetext,
    PRESCRIPTION_OCR_SYSTEM, PRESCRIPTION_OCR_USER,
    analyze_prescription_image
)

IMG_PATH = "test_medicine.jpg"
with open(IMG_PATH, "rb") as f:
    img_bytes = f.read()

print("=== STAGE 1: Free-text Vision OCR ===")
try:
    text = _call_vision_model_freetext(img_bytes, PRESCRIPTION_OCR_SYSTEM, PRESCRIPTION_OCR_USER)
    print(f"OCR len: {len(text)}")
    print(f"OCR preview: {repr(text[:500])}")
except Exception as e:
    print(f"VISION ERROR: {type(e).__name__}: {e}")
    text = ""

print()
print("=== STAGE 2: Full end-to-end analyze_prescription_image ===")
try:
    data, audio_path = analyze_prescription_image(img_bytes, "English")
    if "error" in data:
        print(f"ENGINE ERROR: {data['error']}")
    else:
        meds = data.get("medicines", [])
        print(f"Medicines found: {len(meds)}")
        for m in meds:
            print(f"  - {m.get('name')} | {m.get('dosage')} | {m.get('frequency')} | {m.get('meal_relation')}")
        print(f"Overall advice (first 200): {str(data.get('overall_advice',''))[:200]}")
        print(f"Audio path: {audio_path}")
        print(f"Audio exists: {audio_path and os.path.exists(audio_path)}")
        if audio_path and os.path.exists(audio_path):
            print(f"Audio size: {os.path.getsize(audio_path)} bytes")
            os.remove(audio_path)
            print("Audio cleaned up.")
except Exception as e:
    import traceback
    print(f"PIPELINE ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
