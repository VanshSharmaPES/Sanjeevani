#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# server.py — Flask API server wrapping ai_engine.py and db.py
"""
Start with: python server.py
Runs on http://localhost:5000
"""
import io
import os
import sys
import json
import base64
import time
from functools import wraps
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, set_access_cookies, jwt_required, get_jwt_identity, unset_jwt_cookies
from ai_engine import analyze_medicine_image, analyze_prescription_image, get_medicine_dosage_info, _translate_text
from db import register_user, authenticate_user, save_scan, get_user_history, delete_scan, search_medicines, reset_password, get_db_status

# Fix Windows charmap codec crashes when printing Unicode model output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _safe_log(msg: str):
    """Print log message safely, replacing any unencodable characters."""
    try:
        print(msg)
    except (UnicodeEncodeError, UnicodeError):
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# Simple in-memory rate limiter: IP -> list of timestamps
_rate_limits: dict[str, list[float]] = {}
LIMIT_WINDOW = 60         # 1 minute window
LIMIT_MAX_REQUESTS = 15   # Max 15 scans per minute per IP to protect Vision LLM endpoints

def rate_limited(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        now = time.time()
        
        # Clean up expired timestamps for this IP
        timestamps = _rate_limits.setdefault(ip, [])
        _rate_limits[ip] = [t for t in timestamps if now - t < LIMIT_WINDOW]
        
        if len(_rate_limits[ip]) >= LIMIT_MAX_REQUESTS:
            _safe_log(f"[WARN] Rate limit exceeded for IP: {ip}")
            return jsonify({"error": "Too many requests. Please wait a minute before scanning again."}), 429
            
        _rate_limits[ip].append(now)
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-sanjeevani-key")
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = os.getenv("JWT_COOKIE_SECURE", "False").lower() == "true"
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
jwt = JWTManager(app)

# Audio file cache: filename → absolute path on disk
_audio_cache: dict[str, str] = {}

LANG_CODE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "kn": "Kannada",
    "ml": "Malayalam",
}


# ─── Auth ────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    role = data.get("role", "patient")
    success, msg = register_user(username, password, role)
    if success:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    success, user_id, role = authenticate_user(username, password)
    if success:
        token = create_access_token(identity=str(user_id), additional_claims={"role": role})
        resp = jsonify({"success": True, "username": username, "role": role})
        set_access_cookies(resp, token)
        return resp
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    resp = jsonify({"success": True, "message": "Logged out"})
    unset_jwt_cookies(resp)
    return resp


@app.route("/api/auth/reset-password", methods=["POST"])
def api_reset_password():
    data = request.get_json() or {}
    username = data.get("username", "")
    new_password = data.get("new_password", "")
    success, msg = reset_password(username, new_password)
    if success:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


# ─── Medicines search ────────────────────────────────────────
@app.route("/api/medicines/search", methods=["GET"])
def api_search_medicines():
    query = request.args.get("q", "").strip()
    results = search_medicines(query)
    return jsonify(results)


@app.route("/api/medicines/dosage-info", methods=["GET"])
def api_medicine_dosage_info():
    name = request.args.get("name", "").strip()
    composition = request.args.get("composition", "").strip()
    if not name:
        return jsonify({"error": "Missing medicine name"}), 400
    results = get_medicine_dosage_info(name, composition)
    return jsonify(results)


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    target_lang_code = data.get("language_code", "en").strip()
    target_language = LANG_CODE_MAP.get(target_lang_code, "English")
    
    if not text:
        return jsonify({"error": "Missing text to translate"}), 400
        
    translated = _translate_text(text, target_language)
    return jsonify({"translated": translated})


# ─── Analysis ────────────────────────────────────────────────
@app.route("/api/analyze/medicine", methods=["POST"])
@jwt_required(optional=True)
@rate_limited
def api_analyze_medicine():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files["image"]
    language_code = request.form.get("language", "en")
    user_id = get_jwt_identity()
    language = LANG_CODE_MAP.get(language_code, "English")

    image_bytes = image_file.read()
    data, audio_b64 = analyze_medicine_image(image_bytes, target_language=language)

    if "error" in data:
        _safe_log(f"[ERROR] Medicine analysis failed: {data['error']}")
        return jsonify(data), 500

    # Save to history if user is logged in
    if user_id:
        try:
            save_scan(int(user_id), "medicine", language_code, data)
        except Exception as e:
            _safe_log(f"[WARN] Could not save medicine scan to history: {e}")

    response = {"success": True, "data": data}
    if audio_b64:
        response["audio_b64"] = audio_b64

    return jsonify(response)


@app.route("/api/analyze/prescription", methods=["POST"])
@jwt_required(optional=True)
@rate_limited
def api_analyze_prescription():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files["image"]
    language_code = request.form.get("language", "en")
    user_id = get_jwt_identity()
    language = LANG_CODE_MAP.get(language_code, "English")

    image_bytes = image_file.read()
    data, audio_b64 = analyze_prescription_image(image_bytes, target_language=language)

    if "error" in data:
        _safe_log(f"[ERROR] Prescription analysis failed: {data['error']}")
        return jsonify(data), 500

    # Save to history if user is logged in
    if user_id:
        try:
            save_scan(int(user_id), "prescription", language_code, data)
        except Exception as e:
            _safe_log(f"[WARN] Could not save prescription scan to history: {e}")

    response = {"success": True, "data": data}
    if audio_b64:
        response["audio_b64"] = audio_b64

    return jsonify(response)


# ─── Audio serving ───────────────────────────────────────────


@app.route("/api/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    path = _audio_cache.get(filename)
    if path and os.path.exists(path):
        return send_file(path, mimetype="audio/mpeg")
    return jsonify({"error": "Audio not found"}), 404


# ─── History ─────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
@jwt_required()
def api_history():
    jwt_user = get_jwt_identity()
    history = get_user_history(int(jwt_user))
    return jsonify({"success": True, "history": history})


@app.route("/api/history/<int:scan_id>", methods=["DELETE"])
@jwt_required()
def api_delete_scan(scan_id):
    jwt_user = get_jwt_identity()
    deleted = delete_scan(int(jwt_user), scan_id)
    return jsonify({"success": deleted})


# ─── Health check ────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    db_status = get_db_status()
    return jsonify({
        "status": "ok",
        "database": db_status
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    print(f"🌿 Sanjeevani API server starting on http://localhost:{port} (Debug: {debug_mode})")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
