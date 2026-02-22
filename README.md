# 💊 Sanjeevani AI v4.0

Your Smart Medical Assistant for Medicine & Prescription Analysis

---

## 📋 Features

### 🔍 **Scan Medicine Strip**
- Identify medicines from images of medicine strips/boxes
- Extract active salts/ingredients
- Check dosage levels (normal or high)
- Learn medical conditions the medicine treats
- Get age group recommendations
- Listen to safety advice in your preferred language

### 📝 **Read Prescription**
- Analyze doctor's handwritten or printed prescriptions
- Extract all medicines with dosage and timing
- Show medicines in the order they should be taken
- Suggest alternative medicines with the same active ingredients
- Get detailed meal-relation instructions (before/after meals, etc.)
- Listen to step-by-step audio instructions

### 🌍 **Multi-Language Support**
- English (Default)
- Hindi
- Kannada
- Tamil
- Telugu

---

## 🚀 Quick Start

### 1️⃣ **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 2️⃣ **Set Environment Variables**

Create a `.env` file in the project root with:

```env
API_KEY=your_groq_api_key_here
```

Get your API key from [Groq Console](https://console.groq.com)

### 3️⃣ **Run the App**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📦 Project Structure

```
sanjeevani/
├── app.py                 # Main Streamlit UI
├── ai_engine.py          # LLM-powered OCR and prescription parsing
├── requirements.txt      # Python dependencies
├── ARCHITECTURE.md       # System architecture
├── REQUIREMENTS.md       # Feature requirements
└── README.md            # This file
```

---

## 🛠️ Technologies Used

- **Frontend:** Streamlit (Python)
- **AI/ML:** Groq LLM (Llama models)
- **OCR:** Vision-enabled LLM (no local OCR needed)
- **Text-to-Speech:** gTTS (Google Text-to-Speech)
- **Image Processing:** Pillow
- **Data Handling:** Pandas

---

## 📖 How It Works

### Medicine Analysis Pipeline
1. User captures/uploads medicine image
2. Image is converted to base64 and sent to Groq LLM
3. LLM extracts: name, active salts, dosage, conditions, age group
4. Results are displayed with audio summary
5. Optional temp files are cleaned up

### Prescription Analysis Pipeline
1. User captures/uploads prescription image
2. Image is sent to Groq LLM with medical context
3. LLM interprets handwriting & abbreviations (BD, TDS, AC, PC, etc.)
4. Medicines are extracted in order with:
   - Dosage & frequency
   - Meal relation (before/after meals, etc.)
   - Active ingredients
   - Alternative medicines
5. Audio guide is generated for all medicines
6. Results shown in table + expandable sections

---

## 🎨 Frontend Highlights

- **Responsive Design:** Works on desktop, tablet, and mobile
- **Dark/Light Mode:** Adapts to your system theme
- **Professional UI:**
  - Gradient headers
  - Expandable medicine details
  - Color-coded dosage warnings
  - Clean data tables
- **Accessibility:**
  - Audio output in multiple languages
  - High contrast elements
  - Clear error messages
- **Session State:** Remembers your preferences

---

## ⚙️ Configuration

### Default Settings
- **Default Language:** English
- **Default Mode:** Scan Medicine Strip
- **Audio Format:** MP3
- **Image Formats:** JPG, JPEG, PNG

### Camera Permissions
- HTTPS or network URLs automatically request camera permission
- Localhost doesn't require explicit permission

---

## 🔐 Privacy & Security

- ✅ Images are sent to Groq API (encrypted HTTPS)
- ✅ Audio files are generated locally using gTTS
- ✅ Temp files are automatically cleaned up
- ✅ No data is stored on servers
- ✅ API key kept in `.env` (not hardcoded)

---

## 📞 Troubleshooting

### App won't start
```bash
# Check Python version
python --version  # Should be 3.7+

# Verify dependencies
pip list

# Reinstall requirements
pip install -r requirements.txt --no-cache-dir
```

### Camera not working
- Check browser permission settings
- Use HTTPS for remote access
- Try uploading an image instead

### API errors
- Verify `API_KEY` is set in `.env`
- Check Groq API status: https://status.groq.com
- Ensure API key has not expired

### Audio not playing
- Check browser audio settings
- Verify speakers are not muted
- Try a different browser

---

## 🚦 Current Limitations

- **Handwriting Quality:** Works best with legible handwriting
- **Image Quality:** Clear, well-lit images produce better results
- **Language:** Medical terms in English work best even in translated UI
- **Rate Limiting:** Free Groq tier has usage limits

---

## 🔄 Future Enhancements

- [ ] Local OCR fallback (pytesseract)
- [ ] Drug interaction warnings
- [ ] Symptom-based first aid (Drishti-Vani module)
- [ ] Prescription history tracking
- [ ] Integration with pharmacies for availability
- [ ] Offline mode with cached medicines DB

---

## 📄 License

This project is created for healthcare accessibility in India.

---

## 👥 Contributing

Found a bug or have a feature request? Please open an issue!

---

## 🏥 Support

For issues or questions, contact the Sanjeevani Team.

---

**Made with ❤️ for India | Sanjeevani v4.0 | 2026**
