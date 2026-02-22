# ai_engine.py
import os
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
import json
import base64
from datetime import datetime

load_dotenv()

SYSTEM_INSTRUCTION = """
You are a Medical OCR specialist. Your goal is absolute precision.
Step 1: Extract ALL dates visible on the medicine.
Step 2: Label them clearly as 'MFG', 'EXP', or 'Unknown'.
Step 3: Identify the primary medicine name.
Language Rule: Do not let translation affect your logic. Only translate the 'advice' field.
"""

PRESCRIPTION_INSTRUCTION = """
You are a Medical AI Assistant specializing in reading handwritten and printed prescriptions.
Your goal is to extract the exact medicines, their dosages, and the doctor's instructions.
Language Rule: Translate the 'overall_advice' field into the requested target language.
"""

client = Groq(api_key=os.getenv("API_KEY"))

def analyze_medicine_image(image_bytes, target_language="Hindi"):
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    prompt_text = f"""
    Analyze this image. Today is {today_str}.
    Extract text exactly as seen. Do not guess.
    
    Return JSON structure:
    {{
        "is_medicine": bool,
        "extracted_expiry_text": "The raw date text found after 'EXP' or 'Expiry'",
        "medicine_name": "string",
        "advice": "Safety advice translated into {target_language}"
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
        
        expiry_text = data.get("extracted_expiry_text", "").upper()
        is_expired = False
        if any(yr in expiry_text for yr in ["2022", "2023", "2024", "2025"]):
            is_expired = True
            data["advice"] = f"WARNING: This medicine expired in {expiry_text}. DO NOT USE."
        
        data["is_expired"] = is_expired
        data["expiry_date"] = expiry_text if expiry_text else "Not Found"
        
        audio_file = "medicine_advice.mp3"
        lang_map = {'Hindi': 'hi', 'Kannada': 'kn', 'Tamil': 'ta', 'Telugu': 'te', 'English': 'en'}
        tts = gTTS(text=data["advice"], lang=lang_map.get(target_language, 'hi'))
        tts.save(audio_file)
        
        return data, audio_file

    except Exception as e:
        return {"error": f"Scan Failed: {str(e)}"}, None


def analyze_prescription_image(image_bytes, target_language="Hindi"):
    prompt_text = f"""
    Analyze this medical prescription image.
    Extract the list of prescribed medicines, their dosages (e.g., 500mg, 10ml), 
    frequency (e.g., 2 times a day), and timing (e.g., after meals, before sleep).
    
    Additionally, determine the sequence/order the patient should take the medicines (if the prescription lists them in order, preserve that). For each medicine include a clear "meal_relation" value such as "before breakfast", "after breakfast", "before meals", "after meals", "with food", "empty stomach", "at bedtime", or "anytime".

    Return JSON structure exactly like this:
    {
        "medicines": [
            {
                "name": "string",
                "dosage": "string",
                "frequency": "string",
                "timing": "string",
                "order": 1,
                "meal_relation": "after breakfast"
            }
        ],
        "overall_advice": "A conversational summary of how to take these medicines, translated into {target_language}"
    }
    """

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
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

        # Clean up potential markdown formatting from the LLM response
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:-3].strip()

        data = json.loads(raw_content)

        # Normalize medicines entries: ensure order and meal_relation exist
        medicines = data.get("medicines", []) or []
        for idx, med in enumerate(medicines, start=1):
            if "order" not in med:
                med["order"] = med.get("order", idx)
            if "meal_relation" not in med:
                med["meal_relation"] = med.get("timing", "anytime")

        # Sort medicines by provided order for predictable presentation
        medicines_sorted = sorted(medicines, key=lambda m: m.get("order", 999))
        data["medicines"] = medicines_sorted
        
        # Generate Audio for the overall advice
        audio_file = "prescription_advice.mp3"
        lang_map = {'Hindi': 'hi', 'Kannada': 'kn', 'Tamil': 'ta', 'Telugu': 'te', 'English': 'en'}
        tts = gTTS(text=data.get("overall_advice", ""), lang=lang_map.get(target_language, 'hi'))
        tts.save(audio_file)
        
        return data, audio_file

    except Exception as e:
        return {"error": f"Prescription Scan Failed: {str(e)}"}, None