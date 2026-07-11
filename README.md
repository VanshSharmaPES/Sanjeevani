# Sanjeevani

Sanjeevani is an AI-powered, mobile-first healthcare accessibility platform designed to read medicine packaging and decipher handwritten prescriptions. By combining advanced vision models with deterministic pharmaceutical matching and high-fidelity text-to-speech, Sanjeevani translates medical jargon and handwritten notes into easy-to-understand daily schedules and audio summaries in any of the **22 scheduled languages of India**.

## Med Guide: Production Deployment Vision

Med Guide extends the earlier GenAI-powered personalised medication-guide work into a deployable, API-first healthcare service. Rather than operating as a standalone application, it is designed as an AI layer that can be embedded in the pharmacy and telemedicine workflows people already use.

### The Need

Patients often leave a consultation or pharmacy with prescriptions and medicine packs they cannot confidently interpret. Med Guide converts prescription and medicine data into personalised, multilingual, patient-friendly guidance, while fitting into existing digital-pharmacy workflows. The integration layer is intended to work with platforms such as **PharmEasy, Tata 1mg, Apollo Pharmacy, and Netmeds**, using their prescription, medicine-catalogue, and dispensing data where authorised.

The service must also be safe and practical in real-world conditions: it should protect health data, meet applicable healthcare and **Digital Personal Data Protection (DPDP) Act** obligations, support pharmacist and doctor review, remain useful with low or intermittent connectivity, and use patient feedback to improve guide quality over time.

### Why It Matters

Moving from proof of concept to a reliable product is what enables national-scale impact. An official Med Guide deployment can support Ministry of Health initiatives, integrate with telemedicine services such as **eSanjeevani**, and be used by hospital and retail pharmacies at consultation or dispensing. Clear medication instructions in a patient's preferred Indian language can improve adherence, reduce avoidable medication errors and adverse drug events, and help patients and caregivers participate more confidently in treatment.

### Target Deliverables

1. **Production-ready patient application (Android and iOS):** a user-tested mobile experience for patients and caregivers, distributed through official app stores, that presents accessible medication schedules, warnings, multilingual explanations, and audio guidance.
2. **Secure, scalable backend API and data pipeline:** highly available services that securely process authorised prescription requests, connect to trusted medicine data, apply clinical safety guardrails, and serve AI-generated guides at scale.
3. **Pharmacist and doctor admin dashboard:** a web workspace for healthcare professionals to generate, review, print, and share medication guides during consultations or dispensing, with clear clinical accountability.
4. **Telemedicine integration module:** a standard API and SDK that lets platforms such as eSanjeevani embed medication-guide generation and delivery directly in their existing patient journey.

### Integration, Safety, and Continuous Improvement Principles

* **API-first interoperability:** versioned, documented endpoints and SDKs for pharmacy, hospital, and telemedicine partners; no dependency on a single consumer application.
* **Privacy by design:** consent-aware data handling, data minimisation, encryption in transit and at rest, role-based access, audit trails, and retention controls aligned with applicable law and partner agreements.
* **Clinical safety:** evidence-backed drug data, structured guardrails for contraindications and interactions, clear escalation paths for uncertain results, and pharmacist/doctor review where a workflow requires it. Generated content supports—not replaces—professional medical advice.
* **Inclusive, resilient access:** plain-language guides, support for Indian languages and audio, caregiver sharing, printable outputs, and offline-friendly caching or deferred sync for low-connectivity environments.
* **Feedback-led quality:** allow patients and healthcare professionals to rate, correct, or flag guides; use de-identified, governed feedback to measure safety and usefulness and continuously improve the system.

---

## 🌟 Core Features & Detailed Functionalities
### 1. Handwritten Prescription Decoding
* **Handwriting Transcription:** Deciphers scribbled doctor notes using specialized, low-temperature Vision LLMs.
* **Intelligent Parsing & Segmentation:** Split prescription text into discrete entries (patient info, doctor info, diagnosis, diet advice, follow-up date, and individual medication blocks).
* **Shorthand & Abbreviations Expansion:** Translates medical shorthand like `OD` (once daily), `BD` (twice daily), `TDS` (thrice daily), `1-0-1` (morning & night), `AC` (before meals), `PC` (after meals), `HS` (bedtime), and `SOS` (as needed).
* **Missing Duration Inference:** Automatically estimates duration if omitted (e.g., Antibiotics: 5-7 days, Analgesics: 3-5 days, Antacids: 14 days).
* **Antibiotic Classification & Drug-Drug Interactions:** Flags antibiotic medications and computes severe interaction warnings if multiple conflicting drugs are prescribed together.
* **Dynamic Few-Shot Learning (RAG):** Integrates doctor-corrected history to feed high-fidelity examples back to the parser, improving handwriting transcription over time.

### 2. Alternate Medicine Recommendation Engine
* **Deterministic Matching:** Normalizes and matches active composition keys, dosage form, route of administration, and release type (e.g., extended-release `ER`, dispersible `DT`).
* **Price-Sorted Substitution:** Finds cheaper, active alternatives from the local database sorted by price.
* **Formulation Warnings:** Flags potential differences in special formulations (e.g., fast-absorption optizorb).
* **Doctor-Curated Alternates:** Allows authenticated doctors or pharmacists to manually curate and verify custom alternatives with detailed reasons.

### 3. Medication Guide Generation (implement_D Glue)
* **API Integration:** Connects with the `implement_D` Next.js guide service to generate detailed, printable, and audio-guided patient medication pamphlets for every drug in a prescription.

### 4. Multilingual Audio & Accessibility
* **Translational Pipeline:** Translates summaries and daily schedule tables to a user's selected language using fast Groq LPUs.
* **High-Fidelity Text-To-Speech (TTS):** Generates spoken audio files using `edge-tts` (Azure Neural Voices) matched to local Indian dialects.
* **Full Multilingual Support:** English, Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia, Assamese, Urdu, Nepali, Sanskrit, Konkani, Manipuri, Sindhi, Maithili, Dogri, Kashmiri, and Santali.

### 6. Automated OTP Authentication Engine (Email & Console Fallback)
* **Email Integration:** Registration and password reset actions require a 6-digit OTP sent via secure **SMTP Email dispatches** to the user's registered email address.
* **Mock Fallback Console:** In development environments where SMTP variables are not configured in the `.env` file, OTPs are outputted to the server logs automatically so registrations/resets can proceed.
* **Security Stashing:** Registration requests hash the password first and stashes verification states (`username`, `password_hash`, `role`, `email`, `otp`) in SQLite, verifying them within a 5-minute expiry window to mitigate raw password handling over transient requests.

### 7. Remember Me / "Save login info" Session Guard
* **Granular Login Control:** On the login screen, a "Save login info" toggle controls where JWT tokens, usernames, and roles are kept in the client browser.
* **Persistent Session:** Selecting the option writes credentials to `localStorage`, allowing the user to stay logged in across browser closes.
* **Temporary Session:** Disabling the option routes storing credentials to `sessionStorage`. Closing the browser tab/window immediately destroys all local keys, protecting against session replay or shoulder-surfing compromises.
* **Universal Safeguards:** Scanning interfaces, dashboards, admin views, and logout handlers have been fully upgraded to query, update, and clear state keys from both storage mechanisms.

---

## 🔒 Security & Reliability Guardrails

### 1. Image Quality Verification Gate
* Uses **Laplacian variance computation** to verify image sharpness. It warns users for low-quality uploads and completely blocks blank, out-of-focus, or blurry photos (sharpness score < 2.0) to prevent vision model API wastage.

### 2. Multi-Key API Rotation & Failover
* **Rotating Client Pool:** Rotates between up to 10 Groq API keys (`GROQ_API_KEY_1` to `10`) dynamically to prevent rate limits or credential exhaustion.
* **NVIDIA NIM Fallover:** Automatically reroutes calls to the **NVIDIA Developer Platform** if the primary Groq endpoints fail or exceed limits.

### 3. Defense-in-Depth Security
* **SQL Injection Protection:** Input validation filters out malicious query parameters, and common non-medical search keywords are excluded from database lookups to prevent blind SQLi.
* **XSS & Template Injection Guards:** Scans OCR/User text for code execution hooks, prototype pollution patterns, and nested repetitions designed to cause Regular Expression Denial of Service (ReDoS).
* **Password DoS Protection:** Implements length caps (4 to 128 characters) and hashes user passwords using SHA-256 with a static salt.
* **Scans Rate Limiter:** Protects vision model endpoints from spam using an in-memory rate limiter capped at 15 requests per minute per IP.
* **OTP Replay Guard:** Deletes OTP verification tokens immediately upon first successful use or expiration in SQLite, preventing reuse and brute-force attempts on reset or registration.

---

## 🛠️ Tech Stack

* **Frontend:** Next.js (App Router), React, Tailwind CSS, Framer Motion, Radix UI Primitives, Lucide React, HTML5 Audio API.
* **Backend:** Python (Flask), Flask-CORS, Flask-JWT-Extended (secure cookie tokens).
* **Database:** SQLite (local persistent relational database).
* **AI & Processing:** Groq API, NVIDIA NIMs, RapidFuzz (fuzzy matching), edge-tts (Azure Neural TTS), OpenCV & Pillow (image processing), pillow-heif (HEIC support).
* **OTP Integration:** SMTP Email Dispatcher (secure smtplib TLS connection).

---

## 📂 Project Structure

```text
sanjeevani/
├── app/                        # Next.js App Router Frontend
│   ├── admin/                  # Admin dashboard for doctor/pharmacist curation
│   ├── api/                    # Frontend proxy API routes (auth, analyze, medicines, alternatives, translation)
│   ├── dashboard/              # Patient / Doctor control center
│   ├── history/                # Scanned history records
│   ├── result/                 # Detailed scan results (Medicine and Prescription tabs)
│   ├── scan/                   # Camera scanning interface
│   ├── globals.css             # Main styling system
│   └── page.tsx                # Dynamic landing page
├── components/                 # Reusable UI components (DNASpinner, MandalaBackground, NavLink, etc.)
│   └── ui/                     # Radix UI and shadcn primitives
├── backend/                    # Python API and core services (located in root directory)
│   ├── ai_engine.py            # AI Pipeline (Vision OCR, Translation, Edge-TTS, Image Preprocessing)
│   ├── db.py                   # SQLite Schema, User auth, history storage, custom caches, few-shot retrieval, SMTP/OTP helpers
│   ├── server.py               # Flask Routing, rate-limiting, failover wrappers, guide generation glue, OTP request handler
│   └── medicine_matcher.py     # Deterministic active ingredient and dosage profile matcher
├── A_Z_medicines_dataset_of_India.csv  # Raw Indian medicines catalog for fuzzy lookup
├── dataset_map.json            # Map of known prescription image hashes to prevent cross-uploading
├── sanjeevani.db               # SQLite database file
├── requirements.txt            # Python backend package requirements
├── package.json                # Frontend Node dependencies & build script
├── setup.py                    # Repository setup scripts
├── tailwind.config.ts          # Tailwind styling tokens
└── tsconfig.json               # TypeScript config
```

---

## 🗄️ Database Schema & Caches

Sanjeevani utilizes SQLite (`sanjeevani.db`) with optimized indexes for sub-second retrieval times:
* `users`: Stores user credentials (`username`, `password_hash`, `role` [patient, doctor], `email` [registered email used for OTP], and registration timestamps).
* `scan_history`: Stores past scans for logged-in users, mapping type, language, and structured output.
* `drug_cache`: Key-value cache matching normalized medicine names to analysis results to save on LLM inference costs.
* `prescription_cache`: Matches prescription MD5 OCR hashes to structured results, tracking `corrected` states for dynamic few-shot prompt injection.
* `medicines`: Local medicines database with indexed columns for composition, dosage form, route of administration, release type, formulation variant, and pricing.
* `medicine_alternatives`: Stores manually curated alternatives verified by doctors or pharmacists.
* `otp_verifications`: Stashes OTP records (`username`, `action` [register, reset], `password_hash`, `role`, `email`, `otp` code, `expires_at`, and `created_at`) used in two-step verification.

---

## 🚀 Installation & Setup

### Prerequisites
* **Node.js** (v18+)
* **Python** (v3.10+)
* A **Groq API Key** (or NVIDIA NIM key)
* *Optional:* **SMTP Configuration** (for automated Email OTP notifications)

### 1. Backend Setup
1. Open a terminal in the project root folder.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On MacOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   # Optional key rotation:
   GROQ_API_KEY_1=key_1
   GROQ_API_KEY_2=key_2
   # Optional NVIDIA NIM configuration:
   NVIDIA_API_KEY=your_nvidia_api_key_here
   # JWT Configuration:
   JWT_SECRET_KEY=secure_sanjeevani_jwt_secret
   
   # Optional SMTP credentials for Email OTP:
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_gmail_app_password
   SMTP_SENDER=your_email@gmail.com
   
   # Optional Resend API credentials (alternative to SMTP):
   RESEND_API_KEY=re_your_api_key_here
   ```
5. Run the Flask server:
   ```bash
   python server.py
   ```
   *The server runs locally on `http://127.0.0.1:5000`.*

### 2. Frontend Setup
1. Open a new terminal session in the root folder.
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The app is served locally at `https://localhost:3000` (HTTPS enabled).*

### 📱 Accessing via Mobile Devices (Local Network)
1. Connect both your computer and mobile device to the same Wi-Fi network.
2. Find your computer's local IP address (e.g., `192.168.1.5`).
3. Run the frontend bound to all interfaces:
   ```bash
   npm run dev -- -H 0.0.0.0
   ```
4. Navigate to `http://192.168.1.5:3000` on your mobile browser. You can now use your smartphone camera to scan strips and prescriptions.

---

## 🔌 API Endpoints Reference

### 🔐 Authentication
* `POST /api/auth/register` - Registers users via a two-step verification flow:
  - Request OTP Phase: Payload `{ "action": "request", "username": "user", "password": "pwd", "role": "patient", "email": "user@example.com" }`
  - Verify OTP Phase: Payload `{ "action": "verify", "username": "user", "otp": "123456" }`
* `POST /api/auth/login` - Authenticates user, sets JWT cookies, and returns user configuration details.
* `POST /api/auth/logout` - Clears active JWT cookie tokens and terminates active session scope.
* `POST /api/auth/reset-password` - Resets passwords via a two-step verification flow:
  - Request OTP Phase: Payload `{ "action": "request", "username": "user" }`
  - Verify OTP Phase: Payload `{ "action": "verify", "username": "user", "otp": "123456", "new_password": "pwd" }`

### 🩺 Scanning & OCR Analysis
* `POST /api/analyze/prescription` - Verbatim OCR transcribe of prescription handwriting, segments patient/doctor/drugs, scans drug interactions, translates, and generates edge-TTS audio.

### 💊 Medicines & Alternatives
* `GET /api/medicines/search?q=<query>` - Searches local database for active products. Automatically falls back to AI search to correct typos if database misses.
* `GET /api/medicines/dosage-info?name=<name>&composition=<composition>` - Fetches clinical dosage and usage guidance.
* `GET /api/medicines/alternatives?name=<name>` - Deterministically matches active substitutes by composition, form, route, and release.
* `POST /api/medicines/alternatives` - Submits a doctor-verified substitute recommendation.

### 📚 Extras & Utilities
* `POST /api/translate` - Translates medical texts into target Indian language formats.
* `POST /api/guides/generate` - Generates printable, patient-centric drug guides for prescription medicines.
* `GET /api/history` - Fetches JWT-authenticated user scan history.
* `DELETE /api/history/<scan_id>` - Removes a scan record from history.
* `GET /api/health` - Inspects backend server status and SQLite connection health.
