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
from datetime import timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, set_access_cookies, jwt_required, get_jwt_identity, get_jwt, unset_jwt_cookies
from ai_engine import analyze_medicine_image, analyze_prescription_image, get_medicine_dosage_info, _translate_text, request_guide_generation, search_medicine_fallback_ai
from db import register_user, authenticate_user, save_scan, get_user_history, delete_scan, search_medicines, reset_password, get_db_status, save_custom_medicine, get_medicine_alternatives, save_medicine_alternative, create_otp_verification, verify_otp_verification, register_user_with_hash, get_user_email

# ── Video generation module path setup ──────────────────────────────────────
# The video_generation package lives at certificates/video_generation/.
# We add the certificates/ directory to sys.path so Python can resolve the
# top-level "video_generation" package with its absolute internal imports.
_CERTIFICATES_DIR = str(Path(__file__).resolve().parent / "certificates")
if _CERTIFICATES_DIR not in sys.path:
    sys.path.insert(0, _CERTIFICATES_DIR)

try:
    from video_generation.generator import generate_prescription_videos
    from video_generation.services.asset_resolver import (
        AssetResolutionError,
        ResolvedPrescriptionAssets,
        StrictAssetResolver,
    )
    from video_generation.schemas import PrescriptionVideoInput, VideoGenerationResult
    from video_generation.utils import sanitize_filename as _video_sanitize_filename
    _VIDEO_GENERATION_AVAILABLE = True
except Exception as _vg_import_err:
    _VIDEO_GENERATION_AVAILABLE = False
    _vg_import_err_msg = str(_vg_import_err)

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
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = os.getenv("JWT_COOKIE_SECURE", "False").lower() == "true"
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)

# Audio file cache: filename → absolute path on disk
_audio_cache: dict[str, str] = {}

# All 22 scheduled Indian languages
LANG_CODE_MAP = {
    "en":  "English",
    "hi":  "Hindi",
    "ta":  "Tamil",
    "te":  "Telugu",
    "bn":  "Bengali",
    "mr":  "Marathi",
    "kn":  "Kannada",
    "ml":  "Malayalam",
    "gu":  "Gujarati",
    "pa":  "Punjabi",
    "or":  "Odia",
    "as":  "Assamese",
    "ur":  "Urdu",
    "sa":  "Sanskrit",
    "kok": "Konkani",
    "mni": "Manipuri",
    "ne":  "Nepali",
    "sd":  "Sindhi",
    "mai": "Maithili",
    "doi": "Dogri",
    "ks":  "Kashmiri",
    "sat": "Santali",
}


# ─── Auth ────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    action = data.get("action", "verify")  # Default to verify for backward compatibility
    username = data.get("username", "").strip()
    
    if action == "request":
        password = data.get("password", "")
        role = data.get("role", "patient")
        email = data.get("email", "").strip()
        
        if not username or not password or not email:
            return jsonify({"success": False, "message": "Username, password, and email address are required."}), 400
        if len(password) < 4:
            return jsonify({"success": False, "message": "Password must be at least 4 characters."}), 400
        if len(password) > 128:
            return jsonify({"success": False, "message": "Password cannot be more than 128 characters."}), 400
            
        # Check if user already exists
        import sqlite3
        from db import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username.lower(),)).fetchone()
        conn.close()
        if row:
            return jsonify({"success": False, "message": "Username already exists. Please choose a different one."}), 400
            
        # Hash password and create temporary registration record
        from db import _hash_password
        pwd_hash = _hash_password(password)
        success, otp = create_otp_verification(username, "register", password_hash=pwd_hash, role=role, email=email)
        if success:
            return jsonify({"success": True, "message": "OTP verification code sent via Email."})
        return jsonify({"success": False, "message": "Failed to generate verification code."}), 500
        
    elif action == "verify":
        otp = data.get("otp", "").strip()
        if not username or not otp:
            return jsonify({"success": False, "message": "Username and OTP code are required."}), 400
            
        success, otp_data = verify_otp_verification(username, "register", otp)
        if success and otp_data:
            # Register user
            reg_ok, reg_msg = register_user_with_hash(
                username=username,
                password_hash=otp_data["password_hash"],
                role=otp_data["role"],
                email=otp_data["email"]
            )
            if reg_ok:
                return jsonify({"success": True, "message": reg_msg})
            return jsonify({"success": False, "message": reg_msg}), 400
        return jsonify({"success": False, "message": "Invalid or expired verification code."}), 400
        
    return jsonify({"success": False, "message": "Invalid action."}), 400


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    success, user_id, role = authenticate_user(username, password)
    if success:
        token = create_access_token(identity=str(user_id), additional_claims={"role": role})
        resp = jsonify({"success": True, "username": username, "role": role, "token": token})
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
    action = data.get("action", "verify")  # Default to verify for backward compatibility
    username = data.get("username", "").strip()
    
    if action == "request":
        if not username:
            return jsonify({"success": False, "message": "Username is required."}), 400
            
        # Get email associated with user
        email = get_user_email(username)
        if not email:
            return jsonify({"success": False, "message": "Username not found or no email is registered for this account."}), 400
            
        success, otp = create_otp_verification(username, "reset", email=email)
        if success:
            return jsonify({"success": True, "message": "OTP verification code sent via Email."})
        return jsonify({"success": False, "message": "Failed to generate verification code."}), 500
        
    elif action == "verify":
        otp = data.get("otp", "").strip()
        new_password = data.get("new_password", "")
        if not username or not otp or not new_password:
            return jsonify({"success": False, "message": "Username, OTP code, and new password are required."}), 400
            
        success, otp_data = verify_otp_verification(username, "reset", otp)
        if success:
            reset_ok, reset_msg = reset_password(username, new_password)
            if reset_ok:
                return jsonify({"success": True, "message": reset_msg})
            return jsonify({"success": False, "message": reset_msg}), 400
        return jsonify({"success": False, "message": "Invalid or expired verification code."}), 400
        
    return jsonify({"success": False, "message": "Invalid action."}), 400


# ─── Medicines search ────────────────────────────────────────
@app.route("/api/medicines/search", methods=["GET"])
def api_search_medicines():
    query = request.args.get("q", "").strip()
    results = search_medicines(query)
    
    # Check if there is any high-quality match (exact or prefix/word-boundary match)
    has_high_quality = any(
        r["medicineName"].lower().startswith(query.lower()) or 
        f" {query.lower()}" in r["medicineName"].lower()
        for r in results
    )
    
    # Fallback to AI search if no high-quality matches found in local DB and query length >= 3
    if not has_high_quality and len(query) >= 3:
        _safe_log(f"[INFO] Search miss (or no high-quality match) for '{query}'. Invoking AI fallback search...")
        ai_result = search_medicine_fallback_ai(query)
        if ai_result:
            _safe_log(f"[INFO] AI search found details for '{query}'. Caching to SQLite...")
            save_custom_medicine(ai_result, query=query)
            
            # Re-fetch from DB to merge and sort all results properly
            results = search_medicines(query)
            if not results:
                results = [ai_result]
                
                # If the AI corrected/normalized the name, also offer the user's exact typed query as an option
                if query.lower() != ai_result["medicineName"].lower():
                    query_variation = ai_result.copy()
                    query_variation["medicineName"] = query.title()
                    results.insert(0, query_variation)
            
    return jsonify(results)


@app.route("/api/medicines/dosage-info", methods=["GET"])
def api_medicine_dosage_info():
    name = request.args.get("name", "").strip()
    composition = request.args.get("composition", "").strip()
    if not name:
        return jsonify({"error": "Missing medicine name"}), 400
    results = get_medicine_dosage_info(name, composition)
    return jsonify(results)


@app.route("/api/medicines/alternatives", methods=["GET"])
def api_get_medicine_alternatives():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing medicine name"}), 400
    return jsonify(get_medicine_alternatives(name))


@app.route("/api/medicines/alternatives", methods=["POST"])
@jwt_required()
def api_save_medicine_alternative():
    claims = get_jwt()
    if claims.get("role") != "doctor":
        return jsonify({"success": False, "message": "Doctor/pharmacist authorization required."}), 403
    data = request.get_json(silent=True) or {}
    data["createdBy"] = str(get_jwt_identity())
    success, message = save_medicine_alternative(data)
    return jsonify({"success": success, "message": message}), 200 if success else 400


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


# ─── Guide Generation (implement_D glue) ─────────────────────
@app.route("/api/guides/generate", methods=["POST"])
@jwt_required(optional=True)
def api_generate_guides():
    """
    Accept a prescription analysis result dict (from /api/analyze/prescription)
    and call the implement_D Next.js guide service to generate a medication guide
    for every medicine found in the prescription.
    
    Request body (JSON):
      { "analysis": { ...prescription analysis result... }, "language_code": "en" }
    
    Response body:
      { "success": true, "guides": [ ...GuideApiResponse objects... ] }
    """
    data = request.get_json(force=True, silent=True) or {}
    analysis = data.get("analysis")
    language_code = data.get("language_code", "en")
    language = LANG_CODE_MAP.get(language_code, "English")

    if not analysis or not isinstance(analysis, dict):
        return jsonify({"error": "Missing or invalid 'analysis' field."}), 400

    if "medicines" not in analysis:
        return jsonify({"error": "'analysis' must contain a 'medicines' list."}), 400

    try:
        guides = request_guide_generation(analysis, preferred_language=language)
        return jsonify({"success": True, "guides": guides})
    except Exception as e:
        _safe_log(f"[ERROR] Guide generation failed: {e}")
        return jsonify({"error": f"Guide generation error: {e}"}), 500

# ─── Video Guide Generation ───────────────────────────────────

@app.route("/api/video-guides/generate", methods=["POST"])
@jwt_required(optional=True)
def api_video_guides_generate():
    """
    Generate prescription instruction videos for every medicine in the prescription.

    Request body (JSON): PrescriptionVideoInput-compatible dict, e.g.
      {
        "patientName": "Patient",
        "language": "en",
        "medicines": [ { "medicineName": "Paracetamol 500mg", "dosage": "1 tablet", ... } ]
      }

    Response:
      { "success": true, "videos": [ ...VideoGenerationResult.to_api_dict()... ] }
    """
    if not _VIDEO_GENERATION_AVAILABLE:
        return jsonify({
            "success": False,
            "videos": [],
            "error": f"Video generation module is not available: {_vg_import_err_msg}",
        }), 503

    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        data = {}
    if not data.get("medicines"):
        return jsonify({"success": False, "videos": [], "error": "'medicines' list is required"}), 400

    try:
        results = generate_prescription_videos(data)
        return jsonify({
            "success": True,
            "videos": [r.to_api_dict() for r in results],
        })
    except Exception as exc:
        _safe_log(f"[ERROR] Video generation failed: {exc}")
        return jsonify({"success": False, "videos": [], "error": str(exc)}), 500


@app.route("/api/video-guides/file/<path:filename>", methods=["GET"])
def api_video_guides_file(filename):
    """
    Serve a generated video (.mp4) or subtitle (.srt) file by name.
    The filename corresponds to a sanitized medicine name produced by
    video_generation.utils.sanitize_filename.
    """
    if not _VIDEO_GENERATION_AVAILABLE:
        return jsonify({"error": "Video generation module is not available"}), 503

    # Only allow safe file access within the configured output directory.
    try:
        from video_generation.config import get_settings as _vg_get_settings
        output_dir = _vg_get_settings().output_dir
    except Exception:
        return jsonify({"error": "Video output directory not configured"}), 503

    # Prevent path traversal + restrict to expected generated filenames/types.
    safe_name = Path(filename).name
    requested = Path(safe_name)
    if not safe_name or ".." in Path(filename).parts:
        return jsonify({"error": "Invalid filename"}), 400

    if requested.suffix.lower() not in {".mp4", ".srt"}:
        return jsonify({"error": "Unsupported file type"}), 400

    if requested.stem != _video_sanitize_filename(requested.stem):
        return jsonify({"error": "Invalid filename"}), 400

    output_root = output_dir.resolve()
    video_path = (output_dir / safe_name).resolve()
    if output_root not in video_path.parents:
        return jsonify({"error": "Invalid filename"}), 400

    if not video_path.exists():
        return jsonify({"error": "Video not found"}), 404

    mimetype = "video/mp4" if requested.suffix.lower() == ".mp4" else "text/plain; charset=utf-8"
    return send_file(str(video_path), mimetype=mimetype)


# ─── Video Asset Resolution ───────────────────────────────────

def _resolver_response(resolved: "ResolvedPrescriptionAssets") -> dict:
    """Serialize a ResolvedPrescriptionAssets to a JSON-safe dict."""
    medicines_out = {}
    for slug, assets in resolved.medicines.items():
        medicines_out[slug] = {
            "medicineName": assets.medicine_name,
            "medicineSlug": assets.medicine_slug,
            "routeTemplate": assets.route_template,
            "packageImage": str(assets.package_image),
            "productImage": str(assets.product_image),
            "humanDemoVideo": str(assets.human_demo_video),
            "packageConfidenceLabel": assets.package_confidence_label,
            "productConfidenceLabel": assets.product_confidence_label,
            "warnings": list(assets.warnings or []),
        }
    return {
        "success": True,
        "assets": {"medicines": medicines_out},
        "failures": list(resolved.failures or []),
    }


@app.route("/api/video-assets/resolve", methods=["POST"])
@jwt_required(optional=True)
def api_video_assets_resolve():
    """
    Resolve (fetch/cache) all required media assets for a prescription without
    generating the videos.  Useful to pre-check which assets are available.

    Request body (JSON): same PrescriptionVideoInput-compatible dict as
    /api/video-guides/generate.

    Response:
      { "success": true, "assets": { "medicines": { ... } }, "failures": [ ... ] }
    """
    if not _VIDEO_GENERATION_AVAILABLE:
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": [],
            "error": f"Video generation module is not available: {_vg_import_err_msg}",
        }), 503

    data = request.get_json(force=True, silent=True) or {}
    if not data.get("medicines"):
        return jsonify({"success": False, "assets": {"medicines": {}}, "failures": [],
                        "error": "'medicines' list is required"}), 400

    try:
        resolver = StrictAssetResolver()
        resolved = resolver.resolve_prescription(data, force_refresh=False)
        return jsonify(_resolver_response(resolved))
    except AssetResolutionError as exc:
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": exc.failures,
            "error": str(exc),
        }), 422
    except Exception as exc:
        _safe_log(f"[ERROR] Video asset resolution failed: {exc}")
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": [],
            "error": str(exc),
        }), 500


@app.route("/api/video-assets/refresh", methods=["POST"])
@jwt_required(optional=True)
def api_video_assets_refresh():
    """
    Force-refresh (bypass cache) all media assets for a prescription.
    Accepts the same request body as /api/video-assets/resolve.
    """
    if not _VIDEO_GENERATION_AVAILABLE:
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": [],
            "error": f"Video generation module is not available: {_vg_import_err_msg}",
        }), 503

    data = request.get_json(force=True, silent=True) or {}
    if not data.get("medicines"):
        return jsonify({"success": False, "assets": {"medicines": {}}, "failures": [],
                        "error": "'medicines' list is required"}), 400

    try:
        resolver = StrictAssetResolver()
        resolved = resolver.resolve_prescription(data, force_refresh=True)
        return jsonify(_resolver_response(resolved))
    except AssetResolutionError as exc:
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": exc.failures,
            "error": str(exc),
        }), 422
    except Exception as exc:
        _safe_log(f"[ERROR] Video asset refresh failed: {exc}")
        return jsonify({
            "success": False,
            "assets": {"medicines": {}},
            "failures": [],
            "error": str(exc),
        }), 500



if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    print(f"🌿 Sanjeevani API server starting on http://localhost:{port} (Debug: {debug_mode})")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
