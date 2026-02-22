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

SYSTEM_INSTRUCTION = """
You are a Medical AI specialist. Your goal is absolute precision.
Step 1: Identify the primary medicine name from the image.
Step 2: Identify the active salts/ingredients in the medicine.
Step 3: Determine whether it is a high dosage or normal dosage medicine.
Step 4: Identify what medical conditions this medicine is used for.
Step 5: Identify the suitable age group for this medicine.
Language Rule: Do not let translation affect your logic. Only translate the 'advice' field.
"""

PRESCRIPTION_INSTRUCTION = """
You are a Medical AI Assistant who is an expert at reading real handwritten doctor prescriptions.
Doctors write in rushed, abbreviated, and often illegible handwriting. You must:
- Use medical context and common drug names to interpret unclear handwriting.
- Recognize common doctor abbreviations: "BD" = twice daily, "TDS/TID" = three times daily, "OD" = once daily, "QID" = four times daily, "SOS" = as needed, "HS" = at bedtime, "AC" = before meals, "PC" = after meals, "Stat" = immediately, "Tab" = Tablet, "Cap" = Capsule, "Syp" = Syrup, "Inj" = Injection.
- If a word is partially legible, match it against known drug names (e.g. "Amox" = Amoxicillin, "Azithro" = Azithromycin, "Paracet" = Paracetamol, "Cefix" = Cefixime).
- Extract EVERY medicine line — do not skip any entry, even if partially readable.
- For each medicine, identify its active salts and suggest 2-3 alternatives with the same salts.
Language Rule: Translate the 'overall_advice' field into the requested target language.
"""

client = Groq(api_key=os.getenv("API_KEY"))

LANG_MAP = {'English': 'en', 'Hindi': 'hi', 'Kannada': 'kn', 'Tamil': 'ta', 'Telugu': 'te'}


def analyze_medicine_image(image_bytes, target_language="English"):
    prompt_text = f"""
    Analyze this medicine image carefully.
    Identify the medicine name, its active salts/ingredients, dosage strength, and usage information.

    Return JSON structure:
    {{
        "is_medicine": true,
        "medicine_name": "Name of the medicine",
        "active_salts": ["salt1", "salt2"],
        "dosage_strength": "e.g. 500mg, 10mg etc.",
        "is_high_dosage": true or false,
        "dosage_info": "Explain whether this is a high or normal dosage and why",
        "conditions": ["list of medical conditions this medicine is used for"],
        "suitable_age_group": "e.g. Adults (18+), Children (6-12), All ages, etc.",
        "advice": "Comprehensive safety advice including dosage level, conditions, and age group suitability — translated into {target_language}"
    }}

    If the image is not a medicine, return:
    {{
        "is_medicine": false,
        "medicine_name": "Unknown",
        "active_salts": [],
        "dosage_strength": "N/A",
        "is_high_dosage": false,
        "dosage_info": "N/A",
        "conditions": [],
        "suitable_age_group": "N/A",
        "advice": "This does not appear to be a medicine."
    }}
    """

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                        {"type": "text", "text": prompt_text}
                    ]
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content.strip())

        # Build descriptive audio text
        name = data.get("medicine_name", "Unknown")
        dosage_info = data.get("dosage_info", "")
        conditions = ", ".join(data.get("conditions", []))
        age_group = data.get("suitable_age_group", "")
        advice = data.get("advice", "")

        audio_text = f"Medicine: {name}. {dosage_info}. "
        if conditions:
            audio_text += f"This medicine is used for: {conditions}. "
        if age_group:
            audio_text += f"Suitable age group: {age_group}. "
        audio_text += advice

        tts = gTTS(text=audio_text, lang=LANG_MAP.get(target_language, 'en'))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        tmp.close()

        return data, tmp.name

    except Exception as e:
        return {"error": f"Scan Failed: {str(e)}"}, None


def analyze_prescription_image(image_bytes, target_language="English"):
    prompt_text = f"""
    You are reading a real doctor's handwritten prescription. Doctors write quickly so the handwriting may be messy.
    Use your medical knowledge to interpret abbreviated or unclear text:
    - Common abbreviations: BD=twice daily, TDS/TID=thrice daily, OD=once daily, QID=four times, SOS=as needed, HS=bedtime, AC=before meals, PC=after meals, Tab=Tablet, Cap=Capsule, Syp=Syrup, Inj=Injection.
    - Match partial words to known drugs (e.g. "Amox"=Amoxicillin, "Cefix"=Cefixime, "Azithro"=Azithromycin).

    Extract EVERY medicine from this prescription. Do not skip any line.
    
    For each medicine extract:
    - name: full medicine name (interpret abbreviations)
    - dosage: strength (e.g. 500mg, 250mg)
    - frequency: how often (convert abbreviations to plain language, e.g. BD -> "twice a day")
    - timing: when to take (convert AC/PC to plain language)
    - meal_relation: one of "before breakfast", "after breakfast", "before lunch", "after lunch", "before dinner", "after dinner", "before meals", "after meals", "with food", "empty stomach", "at bedtime", or "anytime"
    - active_salts: the active pharmaceutical ingredients
    - alternatives: 2-3 alternative brand-name medicines containing the same active salts

    Return JSON structure exactly like this:
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
                "alternatives": ["Crocin", "Calpol", "Dolo"]
            }}
        ],
        "overall_advice": "A detailed, conversational summary specifying exactly which medicine to take and when (e.g. 'Take Medicine-A 500mg after breakfast, then Medicine-B 250mg after lunch...'). Translated into {target_language}."
    }}
    """

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": PRESCRIPTION_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                        {"type": "text", "text": prompt_text}
                    ]
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:-3].strip()

        data = json.loads(raw_content)

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

        medicines_sorted = sorted(medicines, key=lambda m: m.get("order", 999))
        data["medicines"] = medicines_sorted

        # Build detailed audio: specify each medicine and when to take it
        audio_parts = []
        for med in medicines_sorted:
            part = f"Medicine {med.get('order', '')}: {med.get('name', 'Unknown')}, {med.get('dosage', '')}, "
            part += f"take {med.get('frequency', '')} {med.get('meal_relation', '')}."
            alts = med.get("alternatives", [])
            if alts:
                part += f" If unavailable, you can use: {', '.join(alts)}."
            audio_parts.append(part)

        overall = data.get("overall_advice", "")
        full_audio_text = " ".join(audio_parts) + " " + overall

        tts = gTTS(text=full_audio_text, lang=LANG_MAP.get(target_language, 'en'))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        tmp.close()

        return data, tmp.name

    except Exception as e:
        return {"error": f"Prescription Scan Failed: {str(e)}"}, None
