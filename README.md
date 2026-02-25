# Sanjeevani

Sanjeevani is an AI-powered healthcare assistant designed to read medicine strips and prescriptions. It utilizes an AI model to extract critical details from images—such as medication names, usage instructions, and expiry dates—and provides an accessible audio output of this information in the user's selected language.

## Detailed Functionalities

* **Medicine Strip Analysis:** - **Information Extraction:** Upload a photo of any medicine strip or bottle. The AI engine extracts the primary drug name, active ingredients, manufacturer details, and expiry date.
* **Usage & Warnings:** It outlines the standard dosage and highlights important medical warnings or side effects associated with the drug.


* **Prescription Decoding:** - **Handwriting Recognition:** Upload images of handwritten doctor prescriptions. The AI deciphers the handwriting to list the prescribed medications.
* **Dosage Instructions:** It breaks down the frequency of the dosage (e.g., morning/evening, before/after meals) into easy-to-understand instructions.


* **Multilingual Audio Output (TTS):** - Designed for accessibility, particularly for elderly users or the visually impaired.
* Converts the extracted text into spoken audio using `edge-tts`.
* **Supported Languages:** English, Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, and Malayalam.


* **User Dashboard & Scan History:** - **Secure Authentication:** Users can create an account and log in securely.
* **History Tracking:** All past medicine and prescription scans are saved to the user's profile, allowing them to revisit old prescriptions or check drug details without rescanning. Users also have full control to delete past records.


* **Modern, Accessible UI:** - Built with Next.js, Tailwind CSS, and Radix UI components, ensuring a highly responsive, animated, and accessible user experience across all devices.

## Tech Stack

* **Frontend:** Next.js (App Router), React, Tailwind CSS, Framer Motion, Radix UI Primitives.
* **Backend:** Python, Flask, Flask-CORS.
* **AI & Processing:** Groq API for fast model inference, Pillow for image processing, Edge-TTS for text-to-speech generation.
* **Data & State Management:** React Query (`@tanstack/react-query`), React Hook Form, Zod for validation.

## Project Structure

```text
sanjeevani/
├── app/                    # Next.js App Router frontend
│   ├── api/                # Next.js API Routes (if any)
│   ├── globals.css         # Global Tailwind styles
│   ├── layout.tsx          # Root layout
│   └── page.tsx            # Main landing page
├── components/             # Reusable UI components
│   └── ui/                 # Radix UI / shadcn components (accordion, dialog, etc.)
├── public/                 # Static assets and icons
├── backend/                # Core Python backend files
│   ├── ai_engine.py        # Core AI logic (Groq API, image analysis, TTS generation)
│   ├── db.py               # Database connection, auth, and user history logic
│   └── server.py           # Flask API server routing and endpoints
├── package.json            # Node.js dependencies and frontend scripts
├── requirements.txt        # Python backend dependencies
├── tailwind.config.ts      # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration

```

## Installation & Setup

### Prerequisites

* Node.js (v18+)
* Python (v3.8+)
* Groq API Key (for the AI engine)

### Backend Setup

1. Navigate to the project directory.
2. Install the required Python dependencies:
```bash
pip install -r requirements.txt

```


3. Create a `.env` file and add your environment variables (e.g., `GROQ_API_KEY`).
4. Start the Flask server:
```bash
python server.py

```


*The server runs on `0.0.0.0:5000`, making it accessible across your local network.*

### Frontend Setup

1. Install Node modules:
```bash
npm install

```


2. Start the Next.js development server:
```bash
npm run dev

```


*The app will be available at `http://localhost:3000`.*

---

## 📱 How to Use on Mobile Devices

Sanjeevani is built with a mobile-first responsive design using Tailwind CSS, meaning the UI automatically adapts to fit smartphone and tablet screens seamlessly. You do not need to install a separate mobile app to use it.

To access Sanjeevani on your mobile phone while developing or hosting locally:

1. **Connect to the same network:** Ensure your mobile device and the computer running the Sanjeevani servers are connected to the same Wi-Fi network.
2. **Find your computer's local IP Address:**
* *Windows:* Open Command Prompt and type `ipconfig` (look for "IPv4 Address", e.g., `192.168.1.5`).
* *Mac/Linux:* Open Terminal and type `ifconfig` or `ip a`.


3. **Run the Backend:** The Flask server is already configured to host on `0.0.0.0` (all interfaces). Start it normally with `python server.py`.
4. **Run the Frontend (Network Access):** Start your Next.js frontend binding it to your local IP address:
```bash
npm run dev -- -H 0.0.0.0

```


5. **Update API URLs (if necessary):** If your frontend relies on an environment variable for the backend API URL (e.g., `NEXT_PUBLIC_API_URL`), ensure it is pointed to your computer's local IP address instead of `localhost` (e.g., `http://192.168.1.5:5000`).
6. **Access via Mobile Browser:** Open Safari or Chrome on your phone and navigate to `http://<YOUR_COMPUTER_IP>:3000`. You can now use the phone's camera directly to snap pictures of medicine strips and prescriptions and upload them to the web app.

---

## API Endpoints

**Auth**

* `POST /api/auth/register` - Register a new user
* `POST /api/auth/login` - Authenticate an existing user
* `POST /api/auth/logout` - Logout the current user using JWT cookie

**Analysis**

* `POST /api/analyze/medicine` - Upload a medicine for Groq analysis and edge-TTS audio bytes
* `POST /api/analyze/prescription` - Upload a prescription for analysis and TTS audio bytes

**Media & History**

* `GET /api/history` - Fetch the authenticated user's scan history
* `DELETE /api/history/<scan_id>` - Remove a specific history entry
* `GET /api/health` - Check backend server health status