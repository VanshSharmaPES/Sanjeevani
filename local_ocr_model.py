#!/usr/bin/env python3
# local_ocr_model.py — bridges the fine-tuned Qwen2.5-VL-32B model into the
# existing ai_engine.py pipeline. Loads the model ONCE at import time.
#
# Exposes: local_vision_ocr(image_bytes: bytes) -> str

import io
import os
import json
import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from peft import PeftModel
from qwen_vl_utils import process_vision_info
from dotenv import load_dotenv

load_dotenv()

os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["PYTORCH_JIT"] = "0"

MODEL_CACHE_PATH = os.getenv("BASE_VLM_MODEL", "Qwen/Qwen2.5-VL-32B-Instruct")
ADAPTER_PATH = os.getenv("OCR_ADAPTER", "vanshshsharma/sanjeevani-rx-ocr-qwen25vl32b-lora")

SYSTEM_INSTRUCTION = (
    "You are a medical prescription and medicine strip OCR and extraction system. "
    "Read the handwritten Indian prescription or medicine image and output ONLY a JSON array "
    "of objects, each with this exact structure: "
    "{\"medicine\": <string>, \"route\": <string>, \"dosage_and_duration\": <string>}. "
    "Do not include any text outside the JSON array. Do not include patient or doctor identifying information."
)

print("[local_ocr_model] Loading fine-tuned Stage 1 model — this takes a few minutes...")

_bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

_base_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_CACHE_PATH,
    quantization_config=_bnb_config,
    device_map={"": 0},
    torch_dtype=torch.bfloat16,
    attn_implementation="sdpa",
)

_model = PeftModel.from_pretrained(_base_model, ADAPTER_PATH)
_model.eval()

_processor = AutoProcessor.from_pretrained(
    MODEL_CACHE_PATH,
    min_pixels=256 * 28 * 28,
    max_pixels=1280 * 1280,
)

print("[local_ocr_model] Model loaded and ready.")


def _flatten_json_to_text(medicines_json):
    lines = []
    for med in medicines_json:
        name = med.get("medicine", "")
        route = med.get("route", "")
        dosage = med.get("dosage_and_duration", "")
        lines.append(f"{name} — {route} — {dosage}")
    return "\n".join(lines)


def local_vision_ocr(image_bytes: bytes) -> str:
    """
    Drop-in replacement for ai_engine.py's _call_vision_model_freetext.
    Takes raw image bytes, returns free-text line-by-line transcription.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": SYSTEM_INSTRUCTION},
            ],
        }
    ]

    text_prompt = _processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, _ = process_vision_info(messages)

    model_inputs = _processor(
        text=[text_prompt],
        images=image_inputs,
        padding=True,
        return_tensors="pt",
    ).to(_model.device)

    with torch.no_grad():
        generated_ids = _model.generate(
            **model_inputs,
            max_new_tokens=1024,
            do_sample=False,
        )

    generated_ids_trimmed = generated_ids[:, model_inputs["input_ids"].shape[1]:]
    output_text = _processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    try:
        parsed = json.loads(output_text.strip())
        return _flatten_json_to_text(parsed)
    except json.JSONDecodeError:
        print(f"[local_ocr_model] WARNING: model output was not valid JSON, passing raw text through: {output_text[:200]}")
        return output_text.strip()
