#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ai_engine.py
import os
import io
import re
import sys
import tempfile
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
import json
import base64
from PIL import Image

load_dotenv()

# Force UTF-8 output on Windows to prevent charmap codec crashes from Unicode model responses
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ========== MODEL CONFIGURATION ==========
# Vision model: used for OCR (reading images)
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
# Analysis model: used for medical reasoning from extracted text
ANALYSIS_MODEL = "llama-3.3-70b-versatile"

# Max characters for TTS (gTTS times out on very long inputs)
MAX_AUDIO_CHARS = 1800

# ========== SYSTEM PROMPTS ==========

# --- Medicine Strip: Vision OCR ---
MEDICINE_OCR_INSTRUCTION = """
You are a precision OCR specialist. Your ONLY job is to extract all visible text from this medicine image.
Extract the medicine name, any dosage/strength info, manufacturer name, active ingredients/composition,
and any other text visible on the strip, box, or label.
Return the result as JSON: {"extracted_text": "all text you can read from the image"}
"""

# --- Medicine Strip: Analysis ---
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

# --- Prescription: Vision OCR ---
# Free-form extraction (no JSON constraint) for best handwriting accuracy
PRESCRIPTION_OCR_SYSTEM = """
You are the world's best specialist at reading Indian doctor handwriting and medical prescriptions.
Your ONLY task is to transcribe every single piece of text you can see in this prescription image.

INDIAN PRESCRIPTION ANATOMY (understand this context):
- Header: Doctor name, qualification, clinic/hospital name, registration number
- Patient info: Name (Pt./Patient), Age, Sex, Date
- Rx section: Numbered list of medicines. Each medicine entry typically has:
    Line 1: Medicine name + strength (e.g. "Tab. Amoxicillin 500mg")
    Line 2: Dose pattern using 1-0-1 grid (morning-afternoon-night) OR BD/TDS/OD/QID
    Line 3: Duration (e.g. × 5d, x 7/7, for 10 days)
- Footer: Doctor signature, seal, instructions like "SOS", "sos only if fever", diet advice

COMMON RAPID-HANDWRITING PATTERNS doctors use:
- Tab = Tablet, Cap = Capsule, Syp/Syr = Syrup, Inj = Injection, Oint = Ointment
- 1-0-1 = morning dose – afternoon dose – night dose (e.g. 1-0-1 = twice; 1-1-1 = three times)
- OD = once daily, BD = twice daily, TDS/TID = thrice daily, QID = four times
- SOS = as needed (when required), Stat = take immediately
- AC = before meals, PC/AF = after meals/food, HS = at bedtime, CC = with meals
- x5d / ×5 days / 5/7 = for 5 days

TRANSCRIPTION RULES:
1. Read EVERY line including headers, patient info, and footer notes.
2. Preserve all numbers and abbreviations exactly as written.
3. For unclear words, give your best guess + original in brackets: "Pantoprazole (Pantop)".
4. If completely unreadable, write [illegible].
5. Output as plain text, line by line, in reading order (top to bottom, left to right).
6. DO NOT interpret, summarize, or skip anything. Full verbatim transcription only.
"""

PRESCRIPTION_OCR_USER = """
Transcribe every piece of text from this prescription image, line by line.
Include doctor header, patient details, ALL medicines with dosage and duration, and any footer notes.
Preserve the Rx numbering, 1-0-1 dose grids, frequency abbreviations, and duration markers exactly.
"""

# --- Prescription: Analysis from transcribed text ---
PRESCRIPTION_ANALYSIS_INSTRUCTION = """
You are a Senior Clinical Pharmacist AI specialising in Indian medical practice.
You receive raw text transcribed from a handwritten Indian doctor's prescription.

Your responsibilities:
1. Identify EVERY medicine — never miss any.
2. Expand ALL abbreviations (see reference below).
3. Match drug names to their correct salts using the reference dictionary.
4. Provide clinical information for each medicine.
5. Build a practical, actionable daily medication schedule.

== FREQUENCY REFERENCE ==
OD = once daily | BD = twice daily | TDS/TID = three times daily | QID = four times daily
SOS = only as needed | Stat = take immediately now
1-0-1 = morning + night (twice) | 1-1-1 = morning + afternoon + night (three times)
0-0-1 = at night only | 1-0-0 = morning only

== TIMING REFERENCE ==
AC = before meals | PC = after meals | HS = at bedtime | CC = with meals | EF = empty stomach

== DRUG NAME REFERENCE (brand → generic salt(s)) ==
Paracetamol/Paracet/PCM/Crocin/Dolo/P-500/Calpol = Paracetamol
Combiflam/Brufen-CT = Ibuprofen + Paracetamol
Ibuprofen/Brufen/Advil/Nurofen = Ibuprofen
Naproxen/Naprosyn = Naproxen
Diclofenac/Voveran/Voltaren = Diclofenac
Meftal/Mefenamic = Mefenamic Acid
Amoxicillin/Amox/Amoxil/Novamox = Amoxicillin
Augmentin/Clavam/Amoxyclav = Amoxicillin + Clavulanic Acid
Azithromycin/Azithro/Zithromax/Azee = Azithromycin
Ciprofloxacin/Cipro/Ciplox = Ciprofloxacin
Cefixime/Cefix/Taxim/Zifi = Cefixime
Cefpodoxime/Cefpod/Cepodem = Cefpodoxime
Cephalexin/Ceporex = Cephalexin
Doxycycline/Doxy = Doxycycline
Metronidazole/Flagyl/Metro = Metronidazole
Clindamycin/Dalacin = Clindamycin
Pantoprazole/Pantop/Pan/Pantocid = Pantoprazole
Omeprazole/Omez/Ocid = Omeprazole
Rabeprazole/Razo/Rablet = Rabeprazole
Esomeprazole/Nexium/Nexpro = Esomeprazole
Domperidone/Domstal/Dom = Domperidone
Ondansetron/Emeset/Ondan/Zofran = Ondansetron
Metoclopramide/Perinorm = Metoclopramide
Ranitidine/Rantac/Zinetac = Ranitidine
Levocetirizine/Levocet/Lecope/Xyzal = Levocetirizine
Cetirizine/Cetzine/Zyrtec/CTZ = Cetirizine
Fexofenadine/Allegra/Fexo = Fexofenadine
Montelukast/Montair/Singulair = Montelukast
Loratadine/Clarityne = Loratadine
Salbutamol/Asthalin/Ventolin = Salbutamol
Budesonide/Budecort = Budesonide
Fluticasone/Flomist/Flixonase = Fluticasone
Metformin/Glycomet/Glucophage = Metformin
Glibenclamide/Daonil = Glibenclamide
Glimepiride/Amaryl/Glimer = Glimepiride
Insulin/Humulin/Novolin = Insulin
Atorvastatin/Atorva/Lipitor/Storvas = Atorvastatin
Rosuvastatin/Rosu/Crestor/Rozucor = Rosuvastatin
Amlodipine/Amlodac/Amlong/Norvasc = Amlodipine
Telmisartan/Telma/Micardis = Telmisartan
Ramipril/Cardace/Altace = Ramipril
Atenolol/Tenormin/Aten = Atenolol
Furosemide/Lasix/Frusemide = Furosemide
Spironolactone/Aldactone/Laractone = Spironolactone
Alprazolam/Alprax/Restyl = Alprazolam
Clonazepam/Clonotril/Klonopin = Clonazepam
Escitalopram/Nexito/Cipralex = Escitalopram
Amitriptyline/Amitril/Elavil = Amitriptyline
Gabapentin/Gabapin/Neurontin = Gabapentin
Pregabalin/Pregalin/Lyrica = Pregabalin
Calcium + Vit D3/Shelcal/Calcirol = Calcium + Cholecalciferol
Vitamin B12/Mecobalamin/Methylcobalamin/Cobadex = Methylcobalamin
Folic Acid/Folvite = Folic Acid
Iron/Ferrous sulphate/Ferium/Orofer = Ferrous Sulphate
Betadine/Povid = Povidone-Iodine
Mupirocin/Mupiderm/Bactroban = Mupirocin
Hydrocortisone/Cortef = Hydrocortisone
Beclomethasone/Beclate = Beclomethasone
Dexamethasone/Dexona/Decadron = Dexamethasone
Prednisolone/Wysolone/Omnacortil = Prednisolone
Tramadol/Tramazac/Ultram = Tramadol
Codeine/Codituss = Codeine
Acetylcysteine/ACC/Mucomyst = Acetylcysteine
Ambroxol/Ambrodil/Mucosolvan = Ambroxol
Salbutamol+Ambroxol/Ascoril = Salbutamol + Ambroxol
Cetrimide/Savlon = Cetrimide
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


def _safe_print(*args, **kwargs):
    """Print that never crashes on Windows due to Unicode characters in model output."""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeError):
        safe_args = [str(a).encode("ascii", errors="replace").decode("ascii") for a in args]
        print(*safe_args, **kwargs)


def _preprocess_image(image_bytes: bytes) -> tuple[bytes, str]:
    """
    Convert any image format to JPEG and resize to max 1600px on the longest side.
    Returns (processed_bytes, mime_type).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Convert palette/transparency modes to RGB for JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # Resize if very large (improves both speed and OCR accuracy)
        max_dim = 1600
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        # Fallback: detect MIME from magic bytes and return raw
        mime = "image/jpeg"
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            mime = "image/webp"
        return image_bytes, mime


def _extract_json_from_text(text: str) -> dict:
    """
    Robustly extract the first valid JSON object from a model response.
    Handles markdown code fences, extra prose, and minor formatting issues.
    """
    # Strip markdown code fences
    stripped = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    stripped = re.sub(r"\s*```$", "", stripped.strip(), flags=re.MULTILINE)
    stripped = stripped.strip()

    # Direct parse
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass

    # Grab first {...} block (handles leading/trailing prose)
    match = re.search(r'\{.*\}', stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(f"Could not parse JSON from model response (first 300 chars): {text[:300]}")


def _call_vision_model_json(image_bytes: bytes, system_prompt: str) -> str:
    """
    Vision OCR with JSON response format — for medicine strips where text is machine-printed.
    Returns the extracted text string.
    """
    processed_bytes, mime_type = _preprocess_image(image_bytes)
    image_base64 = base64.b64encode(processed_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    {"type": "text", "text": "Extract all text from this image. Return as JSON with key 'extracted_text'."}
                ]
            }
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
        for key in ("extracted_text", "text", "content", "result"):
            if key in parsed and isinstance(parsed[key], str):
                return parsed[key].strip()
        text_values = [v for v in parsed.values() if isinstance(v, str)]
        if text_values:
            return " ".join(text_values).strip()
        return raw
    except (json.JSONDecodeError, TypeError):
        return raw.strip()


def _call_vision_model_freetext(image_bytes: bytes, system_prompt: str, user_prompt: str) -> str:
    """
    Vision OCR WITHOUT JSON constraint — critical for handwritten prescriptions.
    Free-form transcription gives much better accuracy for messy handwriting.
    Returns the raw transcribed text.
    """
    processed_bytes, mime_type = _preprocess_image(image_bytes)
    image_base64 = base64.b64encode(processed_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    {"type": "text", "text": user_prompt}
                ]
            }
        ],
        temperature=0.05,  # Very low temperature for maximum faithfulness to image
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def _call_analysis_model(extracted_text: str, system_prompt: str, user_prompt: str) -> dict:
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
    return _extract_json_from_text(raw)


def _cap_text(text: str, max_chars: int = MAX_AUDIO_CHARS) -> str:
    """Trim text to max_chars at the nearest sentence boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = max(truncated.rfind(". "), truncated.rfind("| "), truncated.rfind("। "))
    if last_period > max_chars // 2:
        return truncated[:last_period + 1].strip()
    return truncated.strip()


def _generate_audio(text: str, lang_code: str) -> str | None:
    """Generate a TTS MP3 file. Returns absolute path or None on failure."""
    try:
        capped = _cap_text(text)
        if not capped:
            return None
        tts = gTTS(text=capped, lang=lang_code)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        tmp.close()
        return tmp.name
    except Exception as tts_err:
        _safe_print(f"[WARN] Audio generation failed: {tts_err}")
        return None


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

def analyze_medicine_image(image_bytes: bytes, target_language: str = "English") -> tuple[dict, str | None]:
    """Two-stage pipeline for medicine strip images: Vision OCR → Medical Analysis."""
    try:
        # Stage 1: OCR — free-text mode for better accuracy on all image types
        extracted_text = _call_vision_model_freetext(image_bytes, MEDICINE_OCR_INSTRUCTION, "Extract all visible text from this medicine image, including name, dosage, ingredients, and any other text. Write it line by line.")
        _safe_print(f"[INFO] Medicine OCR extracted {len(extracted_text)} chars")

        if not extracted_text or len(extracted_text.strip()) < 3:
            return {
                "error": "Could not read text from the image. Please ensure the medicine label is clearly visible and well-lit."
            }, None

        # Stage 2: Analysis
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
    "advice": "Comprehensive safety advice including dosage level, conditions, what it does, and age group suitability. Write this advice in {target_language} language."
}}

If the image does not appear to be a medicine, return:
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

        # Defaults for all required fields
        data.setdefault("is_medicine", True)
        data.setdefault("medicine_name", "Unknown")
        data.setdefault("active_salts", [])
        data.setdefault("dosage_strength", "N/A")
        data.setdefault("is_high_dosage", False)
        data.setdefault("dosage_info", "")
        data.setdefault("conditions", [])
        data.setdefault("what_it_does", "")
        data.setdefault("suitable_age_group", "N/A")
        data.setdefault("advice", "")

        # Ensure list fields are actual lists
        if isinstance(data.get("active_salts"), str):
            data["active_salts"] = [s.strip() for s in data["active_salts"].split(",") if s.strip()]
        if isinstance(data.get("conditions"), str):
            data["conditions"] = [s.strip() for s in data["conditions"].split(",") if s.strip()]

        # Build audio
        name = data.get("medicine_name", "Unknown")
        what_it_does = data.get("what_it_does", "")
        dosage_info = data.get("dosage_info", "")
        conditions = ", ".join(data.get("conditions", []))
        age_group = data.get("suitable_age_group", "")
        advice = data.get("advice", "")

        parts = [f"Medicine: {name}."]
        if what_it_does and what_it_does != "N/A":
            parts.append(f"What it does: {what_it_does}.")
        if dosage_info and dosage_info != "N/A":
            parts.append(f"{dosage_info}.")
        if conditions:
            parts.append(f"Used for: {conditions}.")
        if age_group and age_group != "N/A":
            parts.append(f"Suitable for: {age_group}.")
        if advice:
            parts.append(advice)
        audio_text = " ".join(parts)

        audio_path = _generate_audio(audio_text, LANG_MAP.get(target_language, "en"))
        return data, audio_path

    except Exception as e:
        _safe_print(f"[ERROR] Medicine analysis exception: {e}")
        return {"error": f"Scan Failed: {str(e)}"}, None


def analyze_prescription_image(image_bytes: bytes, target_language: str = "English") -> tuple[dict, str | None]:
    """
    Two-stage pipeline for prescription images.
    Stage 1: Free-text OCR (no JSON constraint) for best handwriting transcription.
    Stage 2: Structured medical analysis from transcribed text.
    """
    try:
        # ── Stage 1: Free-text OCR — NO JSON constraint for better handwriting accuracy ──
        extracted_text = _call_vision_model_freetext(
            image_bytes,
            PRESCRIPTION_OCR_SYSTEM,
            PRESCRIPTION_OCR_USER
        )
        _safe_print(f"[INFO] Prescription OCR extracted {len(extracted_text)} chars")
        _safe_print(f"[INFO] OCR preview: {extracted_text[:300].encode('ascii', errors='replace').decode('ascii')}")

        if not extracted_text or len(extracted_text.strip()) < 10:
            return {
                "error": "Could not read text from the prescription image. Please upload a clearer, well-lit photo with good contrast."
            }, None

        # ── Stage 2: Structured Medical Analysis ──
        analysis_prompt = f"""
The following text was transcribed from a handwritten Indian doctor's prescription.
Analyse it carefully and extract every medicine with full clinical details.

Transcribed prescription text:
\"\"\"
{extracted_text}
\"\"\"

Return ONLY a valid JSON object in this EXACT structure (no extra text outside the JSON):
{{
    "patient_info": {{
        "name": "Patient name if visible, else null",
        "age": "Age if visible, else null",
        "date": "Prescription date if visible, else null"
    }},
    "doctor_info": {{
        "name": "Doctor name if visible, else null",
        "qualification": "Qualification if visible, else null"
    }},
    "diagnosis": "Doctor's diagnosis or complaint if written, else null",
    "medicines": [
        {{
            "order": 1,
            "name": "Full generic name + brand name e.g. Paracetamol (Dolo 650)",
            "dosage": "Strength e.g. 500mg, 650mg, 10ml",
            "form": "Tablet / Capsule / Syrup / Injection / Ointment etc.",
            "frequency": "Plain English: e.g. twice a day, three times a day, once at night",
            "timing": "Plain English: e.g. after meals, before meals, at bedtime, empty stomach",
            "duration": "e.g. 5 days, 7 days, 10 days, as needed, ongoing — extract from prescription",
            "meal_relation": "one of: before breakfast, after breakfast, before lunch, after lunch, before dinner, after dinner, before meals, after meals, with food, empty stomach, at bedtime, anytime",
            "active_salts": ["Active ingredient 1", "Active ingredient 2"],
            "alternatives": ["Brand 1 (same salt)", "Brand 2 (same salt)", "Brand 3 (same salt)"],
            "purpose": "Clear explanation: what this medicine does, what condition it treats, why the doctor likely prescribed it for this patient",
            "side_effects": ["Common side effect 1", "Common side effect 2", "Common side effect 3"],
            "food_interaction": "e.g. Avoid alcohol. Take with food to reduce stomach upset. No specific food restrictions.",
            "warnings": "Important warnings e.g. Do not drive. Complete the full antibiotic course. Avoid in pregnancy.",
            "is_antibiotic": true or false,
            "special_instructions": "Any special instruction e.g. Shake well before use. Store in refrigerator. Do not crush."
        }}
    ],
    "overall_advice": "A practical daily medication schedule in {target_language}. Format it clearly by time slot: MORNING: [list medicines + dose + when]. AFTERNOON: [list]. NIGHT: [list]. AS NEEDED: [list]. Then add 2-3 lines of general advice. Be specific and humanised.",
    "diet_advice": "Any dietary advice mentioned by doctor or standard advice for the diagnosed condition",
    "follow_up": "Follow-up instruction if visible, else standard guidance"
}}

CRITICAL RULES:
- Include EVERY medicine from the prescription without exception.
- Use the drug name reference dictionary provided to expand abbreviated names to full generic + brand names.
- If duration is not stated, infer a reasonable duration (e.g. antibiotics: 5-7 days, analgesics: 3-5 days, antacids: 14 days).
- is_antibiotic must be true for any antibiotic (amoxicillin, azithromycin, cefixime, ciprofloxacin, metronidazole, doxycycline, etc.).
- overall_advice MUST be written in {target_language} language.
- All fields are required. Use null only for patient_info/doctor_info fields not visible in the image.
"""
        data = _call_analysis_model(extracted_text, PRESCRIPTION_ANALYSIS_INSTRUCTION, analysis_prompt)
        _safe_print(f"[INFO] Prescription analysis returned keys: {list(data.keys())}")

        # ── Normalise medicines list ──
        medicines = data.get("medicines", []) or []
        if isinstance(medicines, dict):
            medicines = list(medicines.values())

        cleaned = []
        for idx, med in enumerate(medicines, start=1):
            if not isinstance(med, dict):
                continue
            med.setdefault("order", idx)
            med.setdefault("name", "Unknown")
            med.setdefault("dosage", "")
            med.setdefault("form", "Tablet")
            med.setdefault("frequency", "as directed")
            med.setdefault("timing", "as directed")
            med.setdefault("duration", "as prescribed")
            med.setdefault("meal_relation", med.get("timing", "anytime"))
            med.setdefault("purpose", "Not available")
            med.setdefault("food_interaction", "No specific food restrictions.")
            med.setdefault("warnings", "")
            med.setdefault("is_antibiotic", False)
            med.setdefault("special_instructions", "")

            # Ensure list fields are actual lists
            for list_key in ("active_salts", "alternatives", "side_effects"):
                val = med.get(list_key, [])
                if isinstance(val, str):
                    val = [s.strip() for s in val.split(",") if s.strip()]
                med[list_key] = val if isinstance(val, list) else []

            cleaned.append(med)

        medicines_sorted = sorted(cleaned, key=lambda m: m.get("order", 999))
        data["medicines"] = medicines_sorted
        data.setdefault("overall_advice", "")
        data.setdefault("patient_info", {})
        data.setdefault("doctor_info", {})
        data.setdefault("diagnosis", None)
        data.setdefault("diet_advice", "")
        data.setdefault("follow_up", "")

        _safe_print(f"[INFO] Final medicine count: {len(medicines_sorted)}")

        # ── Build audio ──
        audio_parts = []
        for med in medicines_sorted:
            name = med.get("name", "Unknown")
            dosage = med.get("dosage", "")
            freq = med.get("frequency", "")
            meal_rel = med.get("meal_relation", "")
            purpose = med.get("purpose", "")

            part = f"Medicine: {name}."
            if dosage:
                part += f" Dose: {dosage}."
            if freq or meal_rel:
                part += f" Take {freq} {meal_rel}.".replace("  ", " ")
            # Only first sentence of purpose to keep audio concise
            if purpose and purpose != "Not available":
                first = purpose.split(".")[0]
                if first:
                    part += f" {first}."
            audio_parts.append(part)

        full_audio_text = " ".join(audio_parts)
        overall = data.get("overall_advice", "")
        if overall and len(full_audio_text) < MAX_AUDIO_CHARS - 100:
            remaining = MAX_AUDIO_CHARS - len(full_audio_text) - 1
            full_audio_text += " " + overall[:remaining]

        audio_path = _generate_audio(full_audio_text, LANG_MAP.get(target_language, "en"))
        return data, audio_path

    except Exception as e:
        _safe_print(f"[ERROR] Prescription analysis exception: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Prescription Scan Failed: {str(e)}"}, None
