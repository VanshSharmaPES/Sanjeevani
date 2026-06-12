#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verification script to test the prescription verification check and dynamic feedback loop."""
import sys
import os
import json
import hashlib

# Adjust path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
from db import _get_conn, get_recent_corrected_prescriptions, find_cached_prescription
from ai_engine import _is_prescription_text

def run_test():
    print("=== [STEP 1] Testing _is_prescription_text Verification ===")
    
    # 1. Non-prescription/random text
    random_text = "This is a beautiful landscape photo of a sunny day with clouds in the sky and trees."
    result_random = _is_prescription_text(random_text)
    print(f"Random text check: {result_random} (Expected: False)")
    
    # 2. Prescription text with doctor indicators & dosage form
    prescription_text_1 = "Dr. Sharma MBBS Rx Tab. Paracetamol 500mg 1-0-1 for 5 days"
    result_presc_1 = _is_prescription_text(prescription_text_1)
    print(f"Prescription 1 check: {result_presc_1} (Expected: True)")
    
    # 3. Prescription text containing only common medicine name
    prescription_text_2 = "dolo 650 for fever"
    result_presc_2 = _is_prescription_text(prescription_text_2)
    print(f"Prescription 2 check: {result_presc_2} (Expected: True)")

    if result_random is True or result_presc_1 is False or result_presc_2 is False:
        print("❌ FAIL: _is_prescription_text verification check behaves incorrectly!")
        return

    print("✅ PASS: Verification checks passed perfectly.")
    
    print("\n=== [STEP 2] Testing /api/feedback/prescription Endpoint ===")
    
    # Clean up test hash from database before starting
    test_hash = hashlib.md5("test_ocr_text_raw".encode("utf-8")).hexdigest()
    conn = _get_conn()
    conn.execute("DELETE FROM prescription_cache WHERE ocr_hash = ?", (test_hash,))
    conn.execute("DELETE FROM medicines WHERE name = ?", ("TestFeedbackMed",))
    conn.commit()
    conn.close()
    
    client = app.test_client()
    
    # Mock corrected data payload
    mock_corrected_data = {
        "diagnosis": "Test Diagnosis Fever",
        "patient_info": {"name": "Test Patient", "age": "25", "date": "12-06-2026"},
        "medicines": [
            {
                "name": "TestFeedbackMed",
                "dosage": "500 mg",
                "form": "Tablet",
                "frequency": "Twice a day",
                "timing": "After meals",
                "active_salts": ["Paracetamol"],
                "purpose": "Reducing body fever",
                "side_effects": ["Drowsiness"]
            }
        ]
    }
    
    payload = {
        "ocr_hash": test_hash,
        "corrected_data": mock_corrected_data
      # Wait, let's also pass original text using cache_prescription helper first so that the raw text is stored!
    }
    
    # Write initial cache entry with ocr_text so few-shot learning can use it
    from db import cache_prescription
    cache_prescription(test_hash, {"medicines": []}, ocr_text="test_ocr_text_raw")
    
    response = client.post(
        "/api/feedback/prescription",
        data=json.dumps(payload),
        content_type="application/json"
    )
    
    print(f"Feedback endpoint response status: {response.status_code}")
    response_data = json.loads(response.data.decode("utf-8"))
    print(f"Feedback endpoint response payload: {response_data}")
    
    if response.status_code != 200 or not response_data.get("success"):
        print("❌ FAIL: Feedback endpoint did not return success!")
        return
        
    print("✅ PASS: Feedback endpoint accepted corrections.")

    print("\n=== [STEP 3] Verifying Database Storage & Autocomplete Auto-Indexing ===")
    
    # 1. Check cache entry is marked corrected
    conn = _get_conn()
    row = conn.execute("SELECT corrected, result_json FROM prescription_cache WHERE ocr_hash = ?", (test_hash,)).fetchone()
    conn.close()
    
    if not row:
        print("❌ FAIL: Cache entry not found in prescription_cache!")
        return
        
    print(f"Cache entry corrected flag: {row['corrected']} (Expected: 1)")
    cached_json = json.loads(row["result_json"])
    print(f"Cached diagnosis: {cached_json.get('diagnosis')} (Expected: 'Test Diagnosis Fever')")
    
    if row["corrected"] != 1 or cached_json.get("diagnosis") != "Test Diagnosis Fever":
        print("❌ FAIL: Cache entry was not correctly updated or marked as corrected!")
        return
        
    # 2. Check medicine auto-indexed in medicines lookup table
    from db import search_medicines
    results = search_medicines("TestFeedbackMed")
    print(f"Medicines lookup results for 'TestFeedbackMed': {results}")
    
    if not results or results[0]["medicineName"] != "TestFeedbackMed":
        print("❌ FAIL: Medicine 'TestFeedbackMed' was not auto-indexed in medicines lookup database!")
        return
        
    print("✅ PASS: Database storage and autocomplete indexing verified successfully.")

    print("\n=== [STEP 4] Verifying Dynamic Few-Shot learning (RAG) ===")
    
    examples = get_recent_corrected_prescriptions(limit=2)
    print(f"Recent corrected prescriptions for few-shot prompts: {len(examples)}")
    for i, ex in enumerate(examples, 1):
        print(f"  Example {i} OCR text: {repr(ex['ocr_text'])}")
        print(f"  Example {i} corrected JSON keys: {list(ex['result_json'].keys())}")
        
    if not examples or not any(ex["ocr_text"] == "test_ocr_text_raw" for ex in examples):
        print("❌ FAIL: Corrected prescription was not retrieved for dynamic RAG!")
        return
        
    print("✅ PASS: Dynamic few-shot learning examples correctly loaded.")
    print("\n🎉 ALL TESTS PASSED! Verification check and feedback training loop are working perfectly!")

if __name__ == "__main__":
    run_test()
