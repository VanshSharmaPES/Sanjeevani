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
from openai import OpenAI
import asyncio
import edge_tts
import json
import base64
import cv2
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener
import pandas as pd
import threading
from rapidfuzz import process, fuzz

# Support HEIC/HEIF (standard iPhone formats)
register_heif_opener()

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

# If NVIDIA Developer Platform key is present, override the defaults
if os.getenv("NVIDIA_API_KEY"):
    VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "meta/llama-3.2-11b-vision-instruct")
    ANALYSIS_MODEL = os.getenv("NVIDIA_ANALYSIS_MODEL", "meta/llama-3.3-70b-instruct")

# Max characters for TTS (gTTS times out on very long inputs)
MAX_AUDIO_CHARS = 1800

# ========== SYSTEM PROMPTS ==========

# --- Medicine Strip: Vision OCR ---
MEDICINE_OCR_INSTRUCTION = """
You are a precision pharmaceutical OCR specialist. Your ONLY task is to extract all visible text from this medicine strip, box, or bottle label.

SPECIAL GUIDELINES FOR MEDICINE PACKAGING:
1. Scan in all directions (horizontal, vertical, rotated, or upside down) as text layout on medicine strips often runs in multiple orientations.
2. Search for active ingredients / composition. This is usually prefixed by phrases like: "Composition", "Each tablet contains", "Each capsule contains", "Active ingredients", or followed by standards like "IP", "BP", "USP" (e.g. "Paracetamol IP 650 mg").
3. Identify the brand name. It is typically printed in the largest, boldest font on the strip or package (e.g. "DOLO-650", "AUGMENTIN 625 Duo", "PANTOCID").
4. Extract strengths and dosage units (e.g. "500 mg", "650mg", "40 mg", "5 ml", "10% w/v").
5. Look out for manufacturer details (e.g. "Mfg. Lic. No.", "Batch No.", "Exp. Date").
6. Correct common visual noise: metallic strips can reflect light; do not let glare cause you to skip characters or misread them (e.g., cross-reference with known pharmaceutical terms to resolve blurry letters).

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
You are the world's leading medical transcriptionist specializing in deciphering handwritten doctor prescriptions, with a focus on Indian healthcare environments.
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

COMMON INDIAN BRANDS & DRUGS VOCABULARY REFERENCE (use this to resolve ambiguous handwritten shapes):
- Painkillers/Fever: Paracetamol, Dolo, Calpol, Crocin, Combiflam, Ibuprofen, Diclofenac, Voveran, Meftal, Meftal-Spas, Ultracet, Tramadol
- Antibiotics: Amoxicillin, Augmentin, Clavam, Azithromycin, Azee, Ciprofloxacin, Ciplox, Cefixime, Zifi, Cefpodoxime, Cepodem, Doxycycline, Doxy, Metronidazole, Flagyl
- Acid Reflux/PPIs: Pantoprazole, Pantocid, Pan-D, Pan-L, Omeprazole, Omez, Rabeprazole, Razo, Rablet, Ranitidine, Rantac, Zinetac, Domperidone, Domstal
- Allergy/Cough: Levocetirizine, Levocet, Lecope, Cetirizine, Cetzine, Budesonide, Budecort, Salbutamol, Asthalin, Montelukast, Montair, Montair-LC, Allegra, Fexofenadine
- Heart/Diabetes: Metformin, Glycomet, Glimepiride, Amaryl, Atorvastatin, Atorva, Rosuvastatin, Rosu, Amlodipine, Amlokind, Amlong, Telmisartan, Telma
- Vitamins/Supplements: Shelcal, Shelcal-500, Calcirol, Mecobalamin, Methylcobalamin, Cobadex, Folic Acid, Folvite, Orofer, Orofer-XT, Becosules, Limcee

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


class RotatingGroqClient:
    def __init__(self):
        self.keys = []
        
        # Support API_KEY_1 to API_KEY_10 or GROQ_API_KEY_1 to GROQ_API_KEY_10
        for i in range(1, 11):
            key = os.getenv(f"API_KEY_{i}") or os.getenv(f"GROQ_API_KEY_{i}")
            if key and key.strip():
                self.keys.append(key.strip())
                
        # Support fallback/main key
        main_key = os.getenv("API_KEY") or os.getenv("GROQ_API_KEY")
        if main_key and main_key.strip() and main_key.strip() not in self.keys:
            self.keys.append(main_key.strip())
            
        # Deduplicate
        seen = set()
        self.keys = [x for x in self.keys if not (x in seen or seen.add(x))]
        
        if not self.keys:
            print("[WARN] RotatingGroqClient: No Groq API keys found in environment variables!")
            self.keys = [""]
            
        self.clients = [Groq(api_key=k) for k in self.keys]
        self.current_index = 0
        print(f"🔑 RotatingGroqClient: Loaded {len(self.keys)} API key(s) for rotation.")

    def rotate(self):
        if len(self.clients) > 1:
            self.current_index = (self.current_index + 1) % len(self.clients)
            print(f"🔄 RotatingGroqClient: Switched to API key index {self.current_index} due to error/limit.")

    class CompletionsWrapper:
        def __init__(self, outer):
            self.outer = outer

        def create(self, *args, **kwargs):
            last_error = None
            for _ in range(len(self.outer.clients)):
                client_instance = self.outer.clients[self.outer.current_index]
                try:
                    return client_instance.chat.completions.create(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    print(f"⚠️ RotatingGroqClient: Request failed using key index {self.outer.current_index}. Error: {e}")
                    self.outer.rotate()
            raise last_error

    class ChatWrapper:
        def __init__(self, outer):
            self.completions = RotatingGroqClient.CompletionsWrapper(outer)

    @property
    def chat(self):
        return RotatingGroqClient.ChatWrapper(self)


class UnifiedAIClient:
    def __init__(self):
        self.groq_client = RotatingGroqClient()
        self.nvidia_key = os.getenv("NVIDIA_API_KEY")
        if self.nvidia_key and self.nvidia_key.strip():
            self.nvidia_client = OpenAI(
                base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                api_key=self.nvidia_key.strip()
            )
            print("🔑 UnifiedAIClient: NVIDIA client initialized.")
        else:
            self.nvidia_client = None
            print("ℹ️ UnifiedAIClient: NVIDIA_API_KEY not found. Operating in Groq-only mode.")

    class CompletionsWrapper:
        def __init__(self, outer):
            self.outer = outer

        def create(self, *args, **kwargs):
            model = kwargs.get("model", "")
            is_nvidia_model = model.startswith("meta/llama") or "nemotron" in model
            
            if is_nvidia_model and self.outer.nvidia_client:
                try:
                    print(f"📡 Routing request to NVIDIA Platform (Model: {model})")
                    return self.outer.nvidia_client.chat.completions.create(*args, **kwargs)
                except Exception as ne:
                    print(f"⚠️ NVIDIA API call failed: {ne}. Falling back to Groq client pool...")
                    # Fallback to Groq equivalent models
                    if "llama-3.3-70b" in model:
                        kwargs["model"] = "llama-3.3-70b-versatile"
                    elif "llama-3.2-11b-vision" in model or "llama-3.2-90b-vision" in model:
                        kwargs["model"] = "meta-llama/llama-4-scout-17b-16e-instruct"
                    return self.outer.groq_client.chat.completions.create(*args, **kwargs)
            else:
                return self.outer.groq_client.chat.completions.create(*args, **kwargs)

    class ChatWrapper:
        def __init__(self, outer):
            self.completions = UnifiedAIClient.CompletionsWrapper(outer)

    @property
    def chat(self):
        return UnifiedAIClient.ChatWrapper(self)


client = UnifiedAIClient()

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


# Voice Mapping for Microsoft Edge TTS (Indian High-Fidelity Neural Voices)
VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",     # Indian English
    "hi": "hi-IN-MadhurNeural",     # Hindi
    "kn": "kn-IN-GaganNeural",      # Kannada
    "ta": "ta-IN-PallaviNeural",    # Tamil
    "te": "te-IN-MohanNeural",      # Telugu
    "bn": "bn-IN-BashkarNeural",    # Bengali
    "mr": "mr-IN-ManoharNeural",    # Marathi
    "ml": "ml-IN-MidhunNeural",     # Malayalam
}


# Mapping of display language name to code
LANG_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Bengali": "bn",
    "Marathi": "mr",
    "Kannada": "kn",
    "Malayalam": "ml",
}


# ========== LAZY LOADING DATASET & FUZZY MATCHING ==========
MEDICINE_DF = None
MEDICINE_LOCK = threading.Lock()

def load_medicine_df():
    global MEDICINE_DF
    if MEDICINE_DF is None:
        with MEDICINE_LOCK:
            if MEDICINE_DF is None:
                csv_path = os.path.join(os.path.dirname(__file__), "A_Z_medicines_dataset_of_India.csv")
                if os.path.exists(csv_path):
                    try:
                        _safe_print("[INFO] Loading A_Z_medicines_dataset_of_India.csv for fuzzy matching...")
                        # Load only required columns to save memory & time: name, Is_discontinued, short_composition1, short_composition2
                        df = pd.read_csv(csv_path, usecols=["name", "Is_discontinued", "short_composition1", "short_composition2"])
                        # Filter to Is_discontinued == False
                        df["Is_discontinued_bool"] = df["Is_discontinued"].astype(str).str.upper() != "TRUE"
                        filtered_df = df[df["Is_discontinued_bool"]].copy()
                        # Clean name column (lowercase, strip)
                        filtered_df["name_clean"] = filtered_df["name"].astype(str).str.strip()
                        MEDICINE_DF = filtered_df
                        _safe_print(f"[INFO] Loaded {len(MEDICINE_DF)} active medicines into database.")
                    except Exception as e:
                        _safe_print(f"[WARN] Failed to load medicine dataset: {e}")
                        MEDICINE_DF = pd.DataFrame(columns=["name", "Is_discontinued", "short_composition1", "short_composition2", "name_clean"])
                else:
                    _safe_print("[WARN] A_Z_medicines_dataset_of_India.csv not found!")
                    MEDICINE_DF = pd.DataFrame(columns=["name", "Is_discontinued", "short_composition1", "short_composition2", "name_clean"])
    return MEDICINE_DF

def _query_openfda(brand_name: str) -> dict | None:
    """
    Query the public OpenFDA drug label API to resolve missing brand names to their generic compositions.
    Returns a dict with 'name', 'active_salts', 'score', and 'low_confidence', or None if not found/error.
    """
    if not brand_name or not brand_name.strip():
        return None
        
    import requests
    brand_clean = brand_name.strip()
    url_brand = f'https://api.fda.gov/drug/label.json?search=openfda.brand_name:"{brand_clean}"&limit=1'
    url_generic = f'https://api.fda.gov/drug/label.json?search=openfda.generic_name:"{brand_clean}"&limit=1'
    
    for url, search_type in [(url_brand, "brand_name"), (url_generic, "generic_name")]:
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    result = results[0]
                    openfda = result.get("openfda", {})
                    generic_names = openfda.get("generic_name", [])
                    salts = []
                    if generic_names:
                        for g in generic_names:
                            salts.append(g.strip().title())
                    else:
                        active_ingredients = result.get("active_ingredient", [])
                        if active_ingredients:
                            for ai in active_ingredients:
                                clean_ai = ai.replace("Active Ingredient (per tablet)", "").replace("Active Ingredient", "").strip()
                                match = re.match(r'^([a-zA-Z\s\-]+)', clean_ai)
                                if match:
                                    salts.append(match.group(1).strip().title())
                    if salts:
                        return {
                            "name": brand_clean,
                            "active_salts": salts,
                            "score": 90,  # Authority match score
                            "low_confidence": False
                        }
        except Exception as e:
            _safe_print(f"[WARN] OpenFDA {search_type} lookup failed for {brand_clean}: {e}")
    return None


def _infer_salts_via_llm(medicine_name: str) -> list[str]:
    """
    LLM fallback to dynamically infer active salts/compositions of a brand medicine
    if it was not found in the local CSV dataset or OpenFDA.
    """
    if not medicine_name or not medicine_name.strip():
        return []
    system_prompt = "You are a clinical pharmacologist. Identify the active pharmaceutical ingredients (generic names) for the given brand medicine."
    user_prompt = (
        f"Brand name: \"{medicine_name}\"\n"
        "Identify its active ingredients / compositions.\n"
        "Return ONLY a JSON object with a list of strings under key 'active_salts'. "
        "Example:\n"
        "{\n"
        "  \"active_salts\": [\"Pantoprazole\", \"Domperidone\"]\n"
        "}\n"
        "If you do not recognize the medicine, return an empty list."
    )
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "active_salts" in parsed:
            return [s.strip().title() for s in parsed["active_salts"] if s.strip()]
        return []
    except Exception as e:
        _safe_print(f"[WARN] LLM salt inference failed for {medicine_name}: {e}")
        return []


def normalize_medicine_name(raw_name: str, medicine_df=None) -> dict:
    """
    Perform fuzzy matching against the brand name column using rapidfuzz.
    If score >= 75, pull short_composition1 and short_composition2 to auto-populate salts.
    If score < 75, keep raw name and set low_confidence: true.
    """
    if not raw_name or not raw_name.strip():
        return {
            "name": raw_name,
            "active_salts": [],
            "score": 0,
            "low_confidence": True
        }
        
    if medicine_df is None:
        medicine_df = load_medicine_df()
        
    if medicine_df.empty:
        return {
            "name": raw_name.strip(),
            "active_salts": [],
            "score": 0,
            "low_confidence": True
        }
        
    raw_name_clean = raw_name.strip()
    
    # We want to match against the name column of the medicine_df
    names_list = medicine_df["name_clean"].tolist()
    matches = process.extract(raw_name_clean, names_list, scorer=fuzz.WRatio, limit=50)
    
    first_word_query = raw_name_clean.split()[0].lower() if raw_name_clean.split() else ""
    best_match = None
    for name, score, idx in matches:
        if first_word_query in name.lower():
            best_match = (name, score, idx)
            break
            
    # Fallback to top match if score is extremely high (just in case of spelling typos in first word)
    if not best_match and matches:
        top_name, top_score, top_idx = matches[0]
        if top_score >= 85:
            best_match = (top_name, top_score, top_idx)
            
    if best_match:
        matched_name, score, idx = best_match
        if score >= 75:
            row = medicine_df.iloc[idx]
            salts = []
            for col in ["short_composition1", "short_composition2"]:
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    salts.append(str(val).strip())
            return {
                "name": matched_name,
                "active_salts": salts,
                "score": score,
                "low_confidence": False
            }
            
    # --- Local Match Failed (score < 75) ---
    # Fallback 1: Query public OpenFDA API
    fda_result = _query_openfda(raw_name_clean)
    if fda_result:
        _safe_print(f"[INFO] Resolved '{raw_name_clean}' via OpenFDA API: {fda_result['active_salts']}")
        return fda_result
        
    # Fallback 2: Dynamically infer composition via LLM
    llm_salts = _infer_salts_via_llm(raw_name_clean)
    if llm_salts:
        _safe_print(f"[INFO] Resolved '{raw_name_clean}' via LLM inference: {llm_salts}")
        return {
            "name": raw_name_clean,
            "active_salts": llm_salts,
            "score": 60,  # Below 75 threshold, maps to low_confidence/reviewRequired
            "low_confidence": True
        }
            
    return {
        "name": raw_name_clean,
        "active_salts": [],
        "score": matches[0][1] if matches else 0,
        "low_confidence": True
    }



def _safe_print(*args, **kwargs):
    """Print that never crashes on Windows due to Unicode characters in model output."""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeError):
        safe_args = [str(a).encode("ascii", errors="replace").decode("ascii") for a in args]
        print(*safe_args, **kwargs)

def _check_image_quality(img_array: np.ndarray) -> tuple[bool, str]:
    """
    Compute the Laplacian variance to evaluate image sharpness.
    Returns (is_acceptable, message).
    """
    try:
        # If it's a color image (has 3 dimensions), convert to gray
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        _safe_print(f"[INFO] Image quality check: sharpness score = {variance:.2f}")
        # Threshold: if variance < 45, it is considered too blurry to process
        if variance < 45:
            return False, f"Image is too blurry or low contrast (sharpness score: {variance:.1f}). Please upload a clearer photo."
        return True, "Success"
    except Exception as e:
        _safe_print(f"[WARN] Error in _check_image_quality: {e}")
        return True, "Success"


def _heuristic_split_prescription(text: str) -> list[str]:
    """
    Fallback heuristic splitter that splits text by line/numbered patterns
    if the LLM fails to segment it.
    """
    lines = text.splitlines()
    segments = []
    current_segment = []
    
    # Patterns that indicate a new medicine entry starts
    new_entry_patterns = [
        r'^\s*\d+[\s\.\)-]',  # e.g., 1. or 1) or 1-
        r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)[\s\.\)-]',  # Roman numerals
        r'^\s*(Tab|Cap|Syr|Syp|Inj|Oint|Rx|Rx:|Tablet|Capsule|Syrup|Injection|Ointment)\b'  # Brand/form prefix
    ]
    
    def starts_new_entry(line):
        line_stripped = line.strip()
        if not line_stripped:
            return False
        for pattern in new_entry_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                return True
        return False

    for line in lines:
        if not line.strip():
            continue
        if starts_new_entry(line) and current_segment:
            segments.append("\n".join(current_segment))
            current_segment = [line]
        else:
            current_segment.append(line)
            
    if current_segment:
        segments.append("\n".join(current_segment))
        
    return segments


def _compute_confidence(data: dict, fuzzy_scores: list[int], ocr_len: int) -> str:
    """
    Computes overall confidence of the parsing: returns "high", "medium", or "low".
    Confidence is set to "low" when:
      - Any fuzzy match score is < 75
      - Any dosage information is missing or empty (or "N/A")
      - OCR text length is < 20 characters
    Otherwise, returns "high" if all fuzzy scores are >= 85, else "medium".
    """
    if ocr_len < 20:
        return "low"
    
    # Check fuzzy match scores
    if not fuzzy_scores or any(score < 75 for score in fuzzy_scores):
        return "low"
        
    # Check dosage information
    if "medicines" in data:
        for med in data["medicines"]:
            dosage = med.get("dosage", "")
            if not dosage or not str(dosage).strip() or str(dosage).strip().upper() == "N/A":
                return "low"
    else:
        dosage = data.get("dosage_strength", "")
        if not dosage or not str(dosage).strip() or str(dosage).strip().upper() == "N/A":
            return "low"

    if all(score >= 85 for score in fuzzy_scores):
        return "high"
    return "medium"


def _preprocess_image(image_bytes: bytes) -> tuple[bytes, str]:
    """
    Convert any image format to JPEG, auto-correct orientation, enhance contrast,
    sharpen text, and resize to max 1600px on the longest side.
    Returns (processed_bytes, mime_type).
    """
    try:
        from PIL import ImageOps, ImageEnhance
        img = Image.open(io.BytesIO(image_bytes))
        
        # Check image quality (sharpness check via Laplacian variance)
        img_np = np.array(img)
        is_acceptable, msg = _check_image_quality(img_np)
        if not is_acceptable:
            raise ValueError(msg)
            
        # Log suspected format for debugging
        original_format = getattr(img, "format", "Unknown")
        _safe_print(f"[INFO] Preprocessing image: format={original_format}, size={img.size}, mode={img.mode}")

        # Correct portrait/landscape camera orientation based on EXIF tag
        img = ImageOps.exif_transpose(img)

        # Convert palette/transparency modes (like PNG) or HEIF modes to RGB for JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
            
        # Subtle contrast and sharpness enhancements to make handwriting and print text pop
        img = ImageEnhance.Contrast(img).enhance(1.18)
        img = ImageEnhance.Sharpness(img).enhance(1.12)

        # Resize if very large (improves both speed and OCR accuracy)
        max_dim = 1600
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue(), "image/jpeg"
    except ValueError as ve:
        raise ve
    except Exception as e:
        _safe_print(f"[WARN] Image preprocessing failed: {e}. Attempting raw fallback.")
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


def _call_prescription_analysis(extracted_text: str, target_language: str, lang_code: str) -> dict:
    """
    Dedicated prescription analysis call.
    Keeps the OCR text and JSON schema in a single message to avoid double-embedding.
    Drug dictionary is in the system prompt; everything else is in one user message.
    """
    schema = f"""
You are given the transcribed text of a handwritten Indian prescription. Extract ALL medicines and return ONLY valid JSON.
Return ALL fields in English.

Prescription text:
\"\"\"
{extracted_text}
\"\"\"

Return ONLY this JSON structure — no markdown, no prose outside the JSON:
{{
    "patient_info": {{"name": null, "age": null, "date": null}},
    "doctor_info": {{"name": null, "qualification": null}},
    "diagnosis": null,
    "medicines": [
        {{
            "order": 1,
            "name": "Full generic + brand name e.g. Paracetamol (Dolo 650)",
            "dosage": "e.g. 500mg",
            "form": "Tablet",
            "frequency": "e.g. twice a day",
            "timing": "e.g. after meals",
            "duration": "e.g. 5 days",
            "meal_relation": "after meals",
            "active_salts": ["salt1"],
            "alternatives": ["Brand A", "Brand B"],
            "purpose": "What this medicine treats and why prescribed",
            "side_effects": ["side effect 1", "side effect 2"],
            "food_interaction": "e.g. Take with food.",
            "warnings": "e.g. Complete the full course.",
            "is_antibiotic": false,
            "special_instructions": ""
        }}
    ],
    "interactions": ["list of severe known drug-drug interactions between prescribed medicines, if any. Return empty array if none"],
    "overall_advice": "Daily medication schedule in English. Format: MORNING: ... AFTERNOON: ... NIGHT: ... AS NEEDED: ... then general advice.",
    "diet_advice": "Dietary advice for the condition in English",
    "follow_up": "Follow-up recommendation in English"
}}

RULES:
1. Include EVERY medicine — no exceptions.
2. Use the drug dictionary in your system prompt to resolve abbreviated Indian brand/generic names.
3. Expand ALL shorthand: OD=once daily, BD=twice daily, TDS=thrice daily, 1-0-1=morning+night, AC=before meals, PC=after meals.
4. If duration is missing, infer: antibiotics=5-7 days, analgesics=3-5 days, antacids=14 days.
5. Set is_antibiotic=true for any antibiotic class drug.
6. Explicitly check for severe known drug interactions among the extracted medicines and add them to the 'interactions' array. If none exist, return an empty array.
7. ALL text fields must be in English.
"""
    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": PRESCRIPTION_ANALYSIS_INSTRUCTION},
            {"role": "user", "content": schema}
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


async def _generate_audio_bytes_async(text: str, lang_code: str) -> str | None:
    """
    Generate a TTS MP3 file in memory asynchronously.
    Returns base64 encoded string or None on failure.
    """
    try:
        capped = _cap_text(text)
        if not capped:
            return None

        voice = VOICE_MAP.get(lang_code, "hi-IN-MadhurNeural")
        communicate = edge_tts.Communicate(capped, voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as tts_err:
        _safe_print(f"[WARN] Async Edge TTS generation failed: {tts_err}")
        return None


def _generate_audio(text: str, lang_code: str) -> str | None:
    """
    Generate a TTS MP3 file using Microsoft Edge TTS (Azure Neural voices) in memory.
    Returns base64 encoded string or None on failure.
    """
    return asyncio.run(_generate_audio_bytes_async(text, lang_code))


def _translate_text(text: str, target_language: str) -> str:
    """
    Translate an English medical summary to target_language.
    Returns original text unchanged if target is English or translation fails.
    """
    if target_language == "English" or not text.strip():
        return text
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a certified medical translator. "
                        f"Translate the following medical text to {target_language}. "
                        f"Keep all medicine names, dosages, and medical terms accurate. "
                        f"Return ONLY the translated text — no explanations, no English labels."
                    )
                },
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        translated = response.choices[0].message.content.strip()
        return translated if translated else text
    except Exception as te:
        _safe_print(f"[WARN] Translation failed: {te}")
        return text


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

        # Check local SQLite cache first to save API costs & latency
        from db import find_cached_drug_by_ocr, cache_drug
        cached_data = find_cached_drug_by_ocr(extracted_text)
        if cached_data:
            _safe_print(f"[INFO] Cache HIT for medicine from OCR text!")
            data = cached_data.copy()
            name = data.get("medicine_name", "Unknown")
            conditions_str = ", ".join(data.get("conditions", []))
            what_it_does = data.get("what_it_does", "")
            dosage_info = data.get("dosage_info", "")
            age_group = data.get("suitable_age_group", "")
            
            advice_en = data.get("advice_en", "")
            if not advice_en:
                parts_en = [f"{name}."]  
                if conditions_str:
                    parts_en.append(f"Used for: {conditions_str}.")  
                if dosage_info and dosage_info != "N/A":
                    parts_en.append(f"{dosage_info}.")
                if what_it_does and what_it_does != "N/A":
                    parts_en.append(f"{what_it_does}.")
                if age_group and age_group != "N/A":
                    parts_en.append(f"Suitable for: {age_group}.")
                advice_en = _cap_text(" ".join(parts_en))
            
            translated_summary = _translate_text(advice_en, target_language)
            lang_code = LANG_MAP.get(target_language, "en")
            
            data["advice"] = translated_summary
            data["advice_en"] = advice_en
            
            # Ensure confidence & reviewRequired fields are populated for cache hits
            if "confidence" not in data:
                score = 80 if not data.get("low_confidence", False) else 70
                confidence = _compute_confidence(data, [score], len(extracted_text))
                data["confidence"] = confidence
                data["reviewRequired"] = (confidence == "low")
            
            audio_path = _generate_audio(translated_summary, lang_code)
            return data, audio_path

        # Stage 2: Analysis — generate ALL fields in English for accuracy
        analysis_prompt = """
Based on the extracted medicine text below, provide a detailed medical analysis.
Return ALL fields in English.

Return JSON structure:
{
    "is_medicine": true,
    "medicine_name": "Name of the medicine",
    "active_salts": ["salt1", "salt2"],
    "dosage_strength": "e.g. 500mg, 10mg etc.",
    "is_high_dosage": true or false,
    "dosage_info": "Explain whether this is a high or normal dosage and why",
    "conditions": ["list of medical conditions this medicine is used for"],
    "what_it_does": "A clear explanation of what this medicine does in the body and how it works",
    "suitable_age_group": "e.g. Adults (18+), Children (6-12), All ages, etc.",
    "advice": "Comprehensive safety advice including dosage level, conditions, what it does, and age group suitability. Write in English."
}

If the image does not appear to be a medicine, return:
{
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
}
"""
        try:
            data = _call_analysis_model(extracted_text, MEDICINE_ANALYSIS_INSTRUCTION, analysis_prompt)
        except Exception as analysis_err:
            _safe_print(f"[WARN] Analysis LLM failed: {analysis_err}. Attempting database lookup fallback...")
            from db import find_db_drug_by_ocr
            fallback_data = find_db_drug_by_ocr(extracted_text)
            if fallback_data:
                _safe_print("[INFO] Fallback database lookup succeeded!")
                data = fallback_data
            else:
                _safe_print("[WARN] Fallback database lookup failed to find a match.")
                raise analysis_err

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

        # Apply fuzzy match post-processing
        normalized = normalize_medicine_name(data.get("medicine_name", ""))
        if not normalized["low_confidence"]:
            data["medicine_name"] = normalized["name"]
            data["active_salts"] = normalized["active_salts"]
            data["low_confidence"] = False
        else:
            data["low_confidence"] = True

        # Compute confidence and reviewRequired (Task 4)
        if not data.get("is_medicine"):
            data["confidence"] = "low"
            data["reviewRequired"] = True
        else:
            score = normalized.get("score", 0)
            confidence = _compute_confidence(data, [score], len(extracted_text))
            data["confidence"] = confidence
            data["reviewRequired"] = (confidence == "low")

        # Ensure list fields are actual lists
        if isinstance(data.get("active_salts"), str):
            data["active_salts"] = [s.strip() for s in data["active_salts"].split(",") if s.strip()]
        if isinstance(data.get("conditions"), str):
            data["conditions"] = [s.strip() for s in data["conditions"].split(",") if s.strip()]

        # ── Build English summary from the validated structured fields ──
        # This is the single source of truth — both displayed text and audio come from this.
        name = data.get("medicine_name", "Unknown")
        conditions_str = ", ".join(data.get("conditions", []))
        what_it_does = data.get("what_it_does", "")
        dosage_info = data.get("dosage_info", "")
        age_group = data.get("suitable_age_group", "")
        advice_en = data.get("advice", "")

        parts_en = [f"{name}."]  
        if conditions_str:
            parts_en.append(f"Used for: {conditions_str}.")  
        if dosage_info and dosage_info != "N/A":
            parts_en.append(f"{dosage_info}.")
        if what_it_does and what_it_does != "N/A":
            parts_en.append(f"{what_it_does}.")
        if age_group and age_group != "N/A":
            parts_en.append(f"Suitable for: {age_group}.")
        if advice_en:
            parts_en.append(advice_en)
        english_summary = _cap_text(" ".join(parts_en))

        # ── Translate once → used for BOTH displayed advice text and TTS audio ──
        translated_summary = _translate_text(english_summary, target_language)
        lang_code = LANG_MAP.get(target_language, "en")

        # Store both versions so the frontend can display them
        data["advice"] = translated_summary        # shown in selected language
        data["advice_en"] = english_summary        # shown in English for reference

        # Store results in the SQLite lookup cache
        if data.get("is_medicine") and data.get("medicine_name") != "Unknown":
            try:
                cache_drug(data["medicine_name"], data)
            except Exception as cache_err:
                _safe_print(f"[WARN] Failed to write cache: {cache_err}")

        audio_path = _generate_audio(translated_summary, lang_code)
        return data, audio_path

    except Exception as e:
        _safe_print(f"[ERROR] Medicine analysis exception: {e}")
        err_msg = str(e)
        if "Image is too blurry" in err_msg:
            return {"error": err_msg}, None
        return {"error": f"Scan Failed: {err_msg}"}, None


def _extract_prescription_metadata(extracted_text: str) -> dict:
    """
    Extract patient, doctor, diagnosis info, and a list of raw medicine names from the prescription OCR text.
    """
    system_prompt = (
        "You are a clinical transcription assistant. Your task is to extract prescription metadata "
        "and list the raw names of all medicines mentioned. Return ONLY valid JSON."
    )
    user_prompt = f"""
Prescription text:
\"\"\"
{extracted_text}
\"\"\"

Extract the metadata and list the raw medicine names. Return ONLY a JSON object:
{{
    "patient_info": {{"name": "name or null", "age": "age or null", "date": "date or null"}},
    "doctor_info": {{"name": "name or null", "qualification": "qualification or null"}},
    "diagnosis": "diagnosis or null",
    "diet_advice": "diet advice or null",
    "follow_up": "follow-up advice or null"
}}
"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        _safe_print(f"[WARN] Error in _extract_prescription_metadata: {e}")
        return {
            "patient_info": {"name": None, "age": None, "date": None},
            "doctor_info": {"name": None, "qualification": None},
            "diagnosis": None,
            "diet_advice": "",
            "follow_up": ""
        }


def _split_prescription_ocr(extracted_text: str) -> list[str]:
    """
    Use the LLM to split the raw prescription OCR text into individual medicine lines/blocks.
    Returns a list of raw medicine text segments.
    """
    system_prompt = (
        "You are a clinical transcription assistant. Your task is to extract all individual "
        "medicine entries from the raw prescription text. Do not summarize or alter the text; "
        "just split it into distinct text blocks, one for each medicine prescribed. "
        "Return the result as a JSON object with key 'medicines'."
    )
    user_prompt = f"""
Prescription text:
\"\"\"
{extracted_text}
\"\"\"

Extract each medicine entry (including its name, dosage, timing, duration if available) as a separate string.
Return ONLY a JSON object with key 'medicines', containing a list of strings:
{{
  "medicines": [
    "1. Tab. Dolo 650mg 1-0-1 x 5 days",
    "2. Cap. Amoxicillin 500mg 1-1-1 x 7 days after food"
  ]
}}
If no medicines are found, return an empty list:
{{
  "medicines": []
}}
"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "medicines" in parsed:
            return parsed["medicines"]
        return []
    except Exception as e:
        _safe_print(f"[WARN] Error in _split_prescription_ocr: {e}")
        return [extracted_text]


def _extract_medicine_name_from_segment(segment_text: str) -> str:
    """
    Fast LLM call to extract just the raw medicine name from a segment.
    """
    system_prompt = "You are a pharmaceutical assistant. Extract only the brand name or generic name of the medicine from this line."
    user_prompt = f"Line: \"{segment_text}\"\nReturn ONLY the clean medicine name (e.g. Dolo 650, Augmentin 625 Duo, Calpol). No dosage, frequency, or packaging words. Return JSON: {{\"name\": \"...\"}}"
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content).get("name", segment_text)
    except Exception:
        return segment_text


def _extract_dosage_structured(medicine_name: str, segment_text: str) -> dict:
    """
    Extract precise dosage details and pharmaceutical/clinical information for a specific
    medicine based on its text segment from the prescription.
    """
    system_prompt = (
        "You are an expert clinical pharmacist AI. Your task is to extract dosage details "
        "and provide patient advice for a specific medicine from a prescription line."
    )
    user_prompt = f"""
Medicine: "{medicine_name}"
Prescription segment: "{segment_text}"

Extract the dosage details and provide detailed medical/clinical information for this medicine.
Return ALL text fields in English.
Return ONLY a JSON object matching this structure:
{{
    "dosage": "e.g., 500mg, 1 tablet, 10ml",
    "form": "e.g., Tablet, Capsule, Syrup, Inhaler, Injection",
    "frequency": "e.g., twice a day, once daily, three times a day",
    "timing": "e.g., after meals, before meals, at bedtime",
    "duration": "e.g., 5 days, 1 week, 14 days",
    "meal_relation": "e.g., after meals, before meals, empty stomach, with meals, anytime",
    "purpose": "What this medicine treats and why it is prescribed",
    "side_effects": ["side effect 1", "side effect 2"],
    "food_interaction": "e.g., Avoid taking with dairy products.",
    "warnings": "e.g., May cause drowsiness. Do not consume alcohol.",
    "is_antibiotic": true or false,
    "special_instructions": "e.g., Take with a full glass of water."
}}
"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        _safe_print(f"[WARN] Error in _extract_dosage_structured for {medicine_name}: {e}")
        return {
            "dosage": "",
            "form": "Tablet",
            "frequency": "as directed",
            "timing": "as directed",
            "duration": "as prescribed",
            "meal_relation": "anytime",
            "purpose": "Not available",
            "side_effects": [],
            "food_interaction": "No specific food restrictions.",
            "warnings": "",
            "is_antibiotic": False,
            "special_instructions": ""
        }


def _check_drug_interactions(medicine_names: list[str]) -> list[str]:
    """
    Check for severe drug-drug interactions between these medicines.
    """
    if len(medicine_names) < 2:
        return []
    system_prompt = "You are a clinical pharmacologist. Check for severe drug-drug interactions between these medicines."
    user_prompt = f"""
Medicines: {medicine_names}

Check if there are any severe drug-drug interactions between these medicines.
Return ONLY a JSON object with key 'interactions' containing a list of strings describing any interactions:
{{
    "interactions": [
        "Severe interaction: Medicine A + Medicine B can cause risk of..."
    ]
}}
If no severe interactions exist, return an empty list:
{{
    "interactions": []
}}
"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed.get("interactions", [])
    except Exception as e:
        _safe_print(f"[WARN] Error checking drug interactions: {e}")
        return []


def _generate_overall_advice(medicines: list[dict], diagnosis: str) -> str:
    """
    Generate a clear daily medication schedule based on all prescribed medicines.
    """
    if not medicines:
        return "Follow the individual instructions for each medicine."
    system_prompt = "You are a clinical pharmacist. Generate a clear daily medication schedule."
    meds_summary = "\n".join([
        f"- {m['name']} ({m['dosage']}): Form={m['form']}, Freq={m['frequency']}, Timing={m['timing']}, Duration={m['duration']}, Special Instructions={m['special_instructions']}"
        for m in medicines
    ])
    user_prompt = f"""
Diagnosis: {diagnosis}
Medicines:
{meds_summary}

Create a daily medication schedule. Format exactly like:
MORNING: (list medicines to take and timing, or None)
AFTERNOON: (list medicines to take and timing, or None)
NIGHT: (list medicines to take and timing, or None)
AS NEEDED: (list medicines to take as needed, or None)
General Advice: (1-2 sentences of general clinical advice)
"""
    try:
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        _safe_print(f"[WARN] Error generating overall advice: {e}")
        return "Follow the individual instructions for each medicine."


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

        # ── Stage 2: Two-Stage Prescription Processing ──
        lang_code = LANG_MAP.get(target_language, "en")
        
        # 1. Extract metadata (patient, doctor, diagnosis, diet, follow_up)
        metadata = _extract_prescription_metadata(extracted_text)
        
        # 2. Split prescription text into segments (one segment per medicine)
        segments = _split_prescription_ocr(extracted_text)
        
        # Fallback / heuristic splitter check (Task 3)
        # If LLM returned 0 or 1 segments, check if we have a multi-medicine layout heuristically
        if len(segments) <= 1:
            heuristic_segments = _heuristic_split_prescription(extracted_text)
            if len(heuristic_segments) > len(segments):
                _safe_print(f"[INFO] Fallback: LLM returned {len(segments)} segments, but heuristic splitter detected {len(heuristic_segments)} segments. Using heuristic splitting.")
                segments = heuristic_segments
        
        _safe_print(f"[INFO] Two-stage pipeline: split prescription into {len(segments)} segments.")
        
        # 3. Process each segment concurrently to extract precise medicine and dosage details
        import concurrent.futures
        
        def process_segment(idx, segment):
            raw_name = _extract_medicine_name_from_segment(segment)
            normalized = normalize_medicine_name(raw_name)
            
            confirmed_name = normalized["name"]
            matched_salts = normalized["active_salts"]
            low_confidence = normalized["low_confidence"]
            fuzzy_score = normalized["score"]
            
            dosage_data = _extract_dosage_structured(confirmed_name, segment)
            dosage = dosage_data.get("dosage", "")
            
            # Map reviewRequired for this medicine segment
            med_review_req = (
                low_confidence or 
                not dosage or 
                not str(dosage).strip() or 
                str(dosage).strip().upper() == "N/A"
            )
            
            return {
                "order": idx,
                "name": confirmed_name,
                "active_salts": matched_salts,
                "low_confidence": low_confidence,
                "reviewRequired": med_review_req,
                "fuzzy_score": fuzzy_score,
                "dosage": dosage,
                "form": dosage_data.get("form", "Tablet"),
                "frequency": dosage_data.get("frequency", "as directed"),
                "timing": dosage_data.get("timing", "as directed"),
                "duration": dosage_data.get("duration", "as prescribed"),
                "meal_relation": dosage_data.get("meal_relation", "anytime"),
                "purpose": dosage_data.get("purpose", "Not available"),
                "side_effects": dosage_data.get("side_effects", []),
                "food_interaction": dosage_data.get("food_interaction", "No specific food restrictions."),
                "warnings": dosage_data.get("warnings", ""),
                "is_antibiotic": dosage_data.get("is_antibiotic", False),
                "special_instructions": dosage_data.get("special_instructions", "")
            }
            
        medicines_sorted = []
        fuzzy_scores = []
        
        if segments:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(process_segment, idx, segment) for idx, segment in enumerate(segments, start=1)]
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        med_result = fut.result()
                        medicines_sorted.append(med_result)
                        fuzzy_scores.append(med_result.pop("fuzzy_score", 0))
                    except Exception as ex:
                        _safe_print(f"[WARN] Error processing segment: {ex}")
            medicines_sorted.sort(key=lambda x: x["order"])
            
        # 4. Construct overall return dictionary
        data = {
            "patient_info": metadata.get("patient_info") or {"name": None, "age": None, "date": None},
            "doctor_info": metadata.get("doctor_info") or {"name": None, "qualification": None},
            "diagnosis": metadata.get("diagnosis"),
            "medicines": medicines_sorted,
            "diet_advice": metadata.get("diet_advice", ""),
            "follow_up": metadata.get("follow_up", ""),
            "interactions": []
        }
        
        # Compute overall confidence and reviewRequired (Task 4)
        confidence = _compute_confidence(data, fuzzy_scores, len(extracted_text))
        data["confidence"] = confidence
        data["reviewRequired"] = (confidence == "low")
        
        # 5. Check drug-drug interactions for all matched names
        med_names = [m["name"] for m in medicines_sorted if m["name"] != "Unknown"]
        if med_names:
            data["interactions"] = _check_drug_interactions(med_names)
            
        # 6. Generate overall daily schedule advice
        data["overall_advice"] = _generate_overall_advice(medicines_sorted, data["diagnosis"] or "")
        
        _safe_print(f"[INFO] Two-stage execution complete: Final medicine count: {len(medicines_sorted)}, Interactions: {len(data['interactions'])}")
        
        # ── Build English summary from validated structured fields ──
        # Single source of truth — both overall_advice display text and TTS audio come from this.
        med_parts_en = []
        for med in medicines_sorted:
            m_name = med.get("name", "Unknown")
            m_dosage = med.get("dosage", "")
            m_freq = med.get("frequency", "")
            m_meal = med.get("meal_relation", "")
            m_duration = med.get("duration", "")
            m_purpose = med.get("purpose", "")

            sentence = m_name
            if m_dosage:
                sentence += f", {m_dosage}"
            if m_freq:
                sentence += f". Take {m_freq}"
            if m_meal:
                sentence += f" {m_meal}"
            if m_duration:
                sentence += f" for {m_duration}"
            sentence += "."
            # First sentence of purpose only
            if m_purpose and m_purpose != "Not available":
                first = m_purpose.split(".")[0].strip()
                if first:
                    sentence += f" {first}."
            med_parts_en.append(sentence)

        english_med_summary = _cap_text(" ".join(med_parts_en))

        # ── Translate once → used for BOTH overall_advice display and TTS audio ──
        lang_code = LANG_MAP.get(target_language, "en")
        translated_summary = _translate_text(english_med_summary, target_language)

        # Store English summary so the frontend can render bilingual output
        data["overall_advice_en"] = english_med_summary

        # Translate overall_advice (daily schedule), diet_advice, follow_up for display
        if target_language != "English":
            for field in ("overall_advice", "diet_advice", "follow_up"):
                val = data.get(field, "")
                if val:
                    data[field] = _translate_text(val, target_language)

        # Generate individual medicine audios in parallel
        async def _generate_all_meds_audio(meds):
            async def process_med(med, sentence):
                translated = _translate_text(sentence, target_language)
                med["advice_en"] = sentence
                med["advice_translated"] = translated
                med["audio_b64"] = await _generate_audio_bytes_async(translated, lang_code)

            tasks = [process_med(m, s) for m, s in zip(meds, med_parts_en)]
            await asyncio.gather(*tasks)

        try:
            asyncio.run(_generate_all_meds_audio(medicines_sorted))
        except Exception as parallel_tts_err:
            _safe_print(f"[WARN] Parallel TTS generation failed: {parallel_tts_err}")

        audio_text = _cap_text(translated_summary)
        audio_path = _generate_audio(audio_text, lang_code)
        return data, audio_path

    except Exception as e:
        _safe_print(f"[ERROR] Prescription analysis exception: {e}")
        import traceback
        traceback.print_exc()
        err_msg = str(e)
        if "Image is too blurry" in err_msg:
            return {"error": err_msg}, None
        return {"error": f"Prescription Scan Failed: {err_msg}"}, None


def get_medicine_dosage_info(medicine_name: str, composition: str = "") -> dict:
    """
    Query the AI model to get recommended default baseline dosage, frequency, timing,
    and safety advice notes for the specified medicine.
    """
    try:
        system_prompt = (
            "You are an expert clinical pharmacist. Recommend a standard, safe, adult baseline "
            "dosage profile for the specified medicine. Always prioritize safety. Return JSON format."
        )
        
        user_prompt = f"""
        Medicine: "{medicine_name}"
        Composition: "{composition}"
        
        Return standard initial adult dosage details in JSON format with exactly these keys:
        {{
            "dosage": "e.g., 500mg, 1 tablet, 10ml (specify common baseline strength)",
            "frequency": "e.g., Once a day (1-0-0), Twice a day (1-0-1), Three times a day (1-1-1)",
            "timing": "e.g., After meals (PC), Before meals (AC), With meals (CC)",
            "doctorNotes": "1-2 brief safety warnings (e.g. 'Complete the course. Avoid alcohol.')."
        }}
        """
        
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        _safe_print(f"[WARN] Error fetching AI dosage for {medicine_name}: {e}")
        return {
            "dosage": "1 Tablet",
            "frequency": "Twice a day (1-0-1)",
            "timing": "After meals (PC)",
            "doctorNotes": "Consult prescription details for specific instructions."
        }
