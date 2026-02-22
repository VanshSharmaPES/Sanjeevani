#!/usr/bin/env python3
# ai_engine.py
import os
import tempfile
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
import json
import base64

load_dotenv()

# ========== MODEL CONFIGURATION (Model Stacking) ==========
# Model 1: Vision model — focuses purely on reading/OCR from images
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
# Model 2: Text analysis model — focuses on medical reasoning and knowledge
ANALYSIS_MODEL = "llama-3.3-70b-versatile"

# ========== SYSTEM PROMPTS ==========

# --- Medicine Strip: Vision OCR prompt (Model 1) ---
MEDICINE_OCR_INSTRUCTION = """
You are a precision OCR specialist. Your ONLY job is to extract all visible text from this medicine image.
Extract the medicine name, any dosage/strength info, manufacturer name, active ingredients/composition,
and any other text visible on the strip, box, or label.
Return the result as JSON: {"extracted_text": "all text you can read from the image"}
"""

# --- Medicine Strip: Analysis prompt (Model 2) ---
MEDICINE_ANALYSIS_INSTRUCTION = """
You are a Medical AI specialist with deep pharmaceutical knowledge.
Given raw text extracted from a medicine image, analyze it to identify:
- The primary medicine name
- Active salts/ingredients
- Whether this is a high or normal dosage
- Medical conditions this medicine treats and what it does
- Suitable age groups
Provide comprehensive, accurate medical information.
"""

# --- Prescription: Vision OCR prompt (Model 1) ---
PRESCRIPTION_OCR_INSTRUCTION = """
You are an expert at reading doctor handwriting. Your ONLY job is to extract the raw text from this prescription image.
Doctors write in rushed, abbreviated, messy handwriting. You must:
- Read every single line carefully, including partially legible text.
- Preserve doctor abbreviations as-is: BD, TDS, OD, QID, SOS, HS, AC, PC, Tab, Cap, Syp, Inj, etc.
- If a word is partially legible, write your best interpretation with the original in brackets, e.g. "Amox[icillin]".
- Do NOT skip any medicine entry — even if you are uncertain, include your best guess.
- Capture dosage numbers (mg, ml), frequency, and any special instructions.
Return as JSON: {"extracted_text": "the full raw text from the prescription, line by line"}
"""

# --- Prescription: Analysis prompt (Model 2) ---
PRESCRIPTION_ANALYSIS_INSTRUCTION = """
You are a Medical AI pharmacist who is an expert at interpreting doctor prescriptions.
You will receive raw text extracted from a handwritten prescription. Your job is to:
- Interpret all doctor abbreviations: BD=twice daily, TDS/TID=thrice daily, OD=once daily, QID=four times daily, SOS=as needed, HS=at bedtime, AC=before meals, PC=after meals, Stat=immediately, Tab=Tablet, Cap=Capsule, Syp=Syrup, Inj=Injection.
- Match partial/abbreviated drug names to their full names (e.g. "Amox"=Amoxicillin, "Cefix"=Cefixime, "Azithro"=Azithromycin, "Paracet"=Paracetamol, "Metfor"=Metformin).
- For EACH medicine, identify its active salts, what the medicine does (purpose), and suggest 2-3 alternatives with the same salts.
- Extract every single medicine — do not skip any.
Provide accurate, detailed medical analysis.
"""

client = Groq(api_key=os.getenv("API_KEY"))

LANG_MAP = {
    'English': 'en',
    'Hindi': 'hi',
    'Kannada': 'kn',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Bengali': 'bn',
    'Marathi': 'mr',
    'Malayalam': 'ml',
}


def _call_vision_model(image_bytes, system_prompt):
    """Model 1 (Vision): Extract raw text from an image using the vision model."""
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": "Extract all text from this image. Return as JSON with key 'extracted_text'."}
                ]
            }
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content.strip()
    # Robustly extract the text — handle non-JSON or partial JSON responses
    try:
        parsed = json.loads(raw)
        # Accept any key that looks like it holds the extracted text
        for key in ("extracted_text", "text", "content", "result"):
            if key in parsed and isinstance(parsed[key], str):
                return parsed[key]
        # If no recognised key, join all string values
        text_values = [v for v in parsed.values() if isinstance(v, str)]
        if text_values:
            return " ".join(text_values)
        return raw
    except (json.JSONDecodeError, TypeError):
        # Model returned plain text instead of JSON — use it directly
        return raw


def _call_analysis_model(extracted_text, system_prompt, user_prompt):
    """Model 2 (Analysis): Analyze extracted text using the text-based reasoning model."""
    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extracted text from image:\n\n{extracted_text}\n\n{user_prompt}"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content.strip()
    # Strip any markdown code fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Remove first line (```json or ```) and last line (```)
        raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)


def analyze_medicine_image(image_bytes, target_language="English"):
    """Two-stage pipeline: Vision OCR → Medical Analysis for medicine strips."""
    try:
        # === STAGE 1: Vision Model — extract raw text ===
        extracted_text = _call_vision_model(image_bytes, MEDICINE_OCR_INSTRUCTION)

        # === STAGE 2: Analysis Model — interpret extracted text ===
        analysis_prompt = f"""
Based on the extracted medicine text below, provide a detailed medical analysis.

Return JSON structure:
{{
    "is_medicine": true,
    "medicine_name": "Name of the medicine",
    "active_salts": ["salt1", "salt2"],
    "dosage_strength": "e.g. 500mg, 10mg etc.",
    "is_high_dosage": true or false,
    "dosage_info": "Explain whether this is a high or normal dosage and why",
    "conditions": ["list of medical conditions this medicine is used for"],
    "what_it_does": "A clear explanation of what this medicine does in the body and how it works",
    "suitable_age_group": "e.g. Adults (18+), Children (6-12), All ages, etc.",
    "advice": "Comprehensive safety advice including dosage level, conditions, what it does, and age group suitability — translated into {target_language}"
}}

If the text does not appear to be from a medicine, return:
{{
    "is_medicine": false,
    "medicine_name": "Unknown",
    "active_salts": [],
    "dosage_strength": "N/A",
    "is_high_dosage": false,
    "dosage_info": "N/A",
    "conditions": [],
    "what_it_does": "N/A",
    "suitable_age_group": "N/A",
    "advice": "This does not appear to be a medicine."
}}
"""
        data = _call_analysis_model(extracted_text, MEDICINE_ANALYSIS_INSTRUCTION, analysis_prompt)

        # Build descriptive audio text
        name = data.get("medicine_name", "Unknown")
        dosage_info = data.get("dosage_info", "")
        what_it_does = data.get("what_it_does", "")
        conditions = ", ".join(data.get("conditions", []))
        age_group = data.get("suitable_age_group", "")
        advice = data.get("advice", "")

        audio_text = f"Medicine: {name}. "
        if what_it_does:
            audio_text += f"What it does: {what_it_does}. "
        if dosage_info:
            audio_text += f"{dosage_info}. "
        if conditions:
            audio_text += f"Used for: {conditions}. "
        if age_group:
            audio_text += f"Suitable age group: {age_group}. "
        audio_text += advice

        audio_path = None
        try:
            tts = gTTS(text=audio_text, lang=LANG_MAP.get(target_language, 'en'))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            tmp.close()
            audio_path = tmp.name
        except Exception as tts_err:
            print(f"[WARN] Medicine audio generation failed: {tts_err}")

        return data, audio_path

    except Exception as e:
        return {"error": f"Scan Failed: {str(e)}"}, None


def analyze_prescription_image(image_bytes, target_language="English"):
    """Two-stage pipeline: Vision OCR → Medical Analysis for prescriptions."""
    try:
        # === STAGE 1: Vision Model — extract raw prescription text ===
        extracted_text = _call_vision_model(image_bytes, PRESCRIPTION_OCR_INSTRUCTION)

        # === STAGE 2: Analysis Model — interpret medicines from extracted text ===
        analysis_prompt = f"""
Based on the raw prescription text below, extract and analyze every medicine mentioned.

For each medicine provide:
- name: full medicine name (interpret any abbreviations)
- dosage: strength (e.g. 500mg, 250mg)
- frequency: how often, in plain language (e.g. BD -> "twice a day")
- timing: when to take, in plain language (e.g. AC -> "before meals")
- meal_relation: one of "before breakfast", "after breakfast", "before lunch", "after lunch", "before dinner", "after dinner", "before meals", "after meals", "with food", "empty stomach", "at bedtime", or "anytime"
- active_salts: the active pharmaceutical ingredients
- alternatives: 2-3 alternative brand medicines with the same active salts
- purpose: what this medicine does, what condition it treats, and why the doctor likely prescribed it

Return JSON:
{{
    "medicines": [
        {{
            "name": "Medicine Name",
            "dosage": "500mg",
            "frequency": "twice a day",
            "timing": "after meals",
            "order": 1,
            "meal_relation": "after meals",
            "active_salts": ["Paracetamol"],
            "alternatives": ["Crocin", "Calpol", "Dolo"],
            "purpose": "Paracetamol is a pain reliever and fever reducer. It is likely prescribed to manage pain or reduce fever."
        }}
    ],
    "overall_advice": "A detailed, conversational summary specifying exactly which medicine to take and when (e.g. 'First, take Medicine-A 500mg after breakfast. Then take Medicine-B 250mg after lunch...'), including what each medicine does. Translated into {target_language}."
}}
"""
        data = _call_analysis_model(extracted_text, PRESCRIPTION_ANALYSIS_INSTRUCTION, analysis_prompt)

        # Normalize medicines entries
        medicines = data.get("medicines", []) or []
        for idx, med in enumerate(medicines, start=1):
            if "order" not in med:
                med["order"] = idx
            if "meal_relation" not in med:
                med["meal_relation"] = med.get("timing", "anytime")
            if "active_salts" not in med:
                med["active_salts"] = []
            if "alternatives" not in med:
                med["alternatives"] = []
            if "purpose" not in med:
                med["purpose"] = "Not available"

        medicines_sorted = sorted(medicines, key=lambda m: m.get("order", 999))
        data["medicines"] = medicines_sorted

        # Build detailed audio: specify each medicine, what it does, and when to take it
        audio_parts = []
        for med in medicines_sorted:
            part = f"Medicine {med.get('order', '')}: {med.get('name', 'Unknown')}. "
            purpose = med.get("purpose", "")
            if purpose:
                part += f"This medicine {purpose}. "
            part += f"Take {med.get('dosage', '')} {med.get('frequency', '')} {med.get('meal_relation', '')}. "
            alts = med.get("alternatives", [])
            if alts:
                part += f"If unavailable, you can use: {', '.join(alts)}. "
            audio_parts.append(part)

        overall = data.get("overall_advice", "")
        full_audio_text = " ".join(audio_parts) + " " + overall

        audio_path = None
        try:
            tts = gTTS(text=full_audio_text, lang=LANG_MAP.get(target_language, 'en'))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp.name)
            tmp.close()
            audio_path = tmp.name
        except Exception as tts_err:
            print(f"[WARN] Prescription audio generation failed: {tts_err}")

        return data, audio_path

    except Exception as e:
        return {"error": f"Prescription Scan Failed: {str(e)}"}, None
