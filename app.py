# app.py
import streamlit as st
import os
import pandas as pd
from ai_engine import analyze_medicine_image, analyze_prescription_image

st.set_page_config(page_title="Sanjeevani AI", page_icon="💊", layout="centered")

# Custom UI for a cleaner feel
st.markdown("<style>.stCameraInput { border: 2px solid #004a99; border-radius: 10px; }</style>", unsafe_allow_html=True)

st.title("💊 Sanjeevani")

# SIDEBAR CONTROLS
st.sidebar.header("Settings")
app_mode = st.sidebar.radio("Select Mode", ["Scan Medicine Strip", "Read Prescription"])
language = st.sidebar.selectbox("Preferred Language", ["Hindi", "English", "Kannada", "Tamil", "Telugu"])

if app_mode == "Scan Medicine Strip":
    st.write("Scan your medicine strip for instant safety verification.")
else:
    st.write("Upload or scan a doctor's prescription to understand your dosage schedule.")

# TABBED INTERFACE: Choose between Webcam and Upload
tab1, tab2 = st.tabs(["📸 Live Webcam", "📂 Upload Image"])

image_to_process = None

with tab1:
    cam_image = st.camera_input("Hold the document/strip clearly in front of the camera")
    if cam_image:
        image_to_process = cam_image.getvalue()

with tab2:
    uploaded_file = st.file_uploader("Or upload a saved photo", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image_to_process = uploaded_file.getvalue()

# AUTO-PROCESSING LOGIC
if image_to_process:
    if app_mode == "Scan Medicine Strip":
        with st.spinner("🔍 AI is reading the strip..."):
            data, audio_path = analyze_medicine_image(image_to_process, target_language=language)

        if "error" in data:
            st.error(data['error'])
        else:
            st.success(f"✅ Medicine: {data.get('medicine_name')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 📅 Expiry Status")
                status = data.get('is_expired')
                exp_date = data.get('expiry_date')

                if status is None or exp_date == "Not Found":
                    st.warning("⚖️ UNKNOWN")
                    st.info("Expiry date not found. **Warning: Medicine might be expired.**")
                elif status is True:
                    st.error(f"⛔ EXPIRED ({exp_date})")
                else:
                    st.success(f"✔️ VALID ({exp_date})")

            with col2:
                st.markdown("#### 💡 Advice")
                st.write(data.get('advice'))
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")

    elif app_mode == "Read Prescription":
        with st.spinner("🔍 AI is reading the prescription..."):
            data, audio_path = analyze_prescription_image(image_to_process, target_language=language)

        if "error" in data:
            st.error(data['error'])
        else:
            st.success("✅ Prescription Analyzed Successfully")
            
            st.markdown("#### 📝 Medication Schedule")
            medicines = data.get("medicines", [])
            if medicines:
                # Ensure predictable ordering
                medicines_sorted = sorted(medicines, key=lambda m: m.get("order", 999))

                # Create display DataFrame with explicit columns
                display_rows = []
                for m in medicines_sorted:
                    display_rows.append({
                        "Order": m.get("order"),
                        "Name": m.get("name"),
                        "Dosage": m.get("dosage"),
                        "Frequency": m.get("frequency"),
                        "Timing": m.get("timing"),
                        "Meal Relation": m.get("meal_relation", "anytime")
                    })

                df = pd.DataFrame(display_rows)
                st.table(df)

                st.markdown("#### 🔢 Sequence & Friendly Schedule")
                for m in medicines_sorted:
                    order = m.get("order")
                    name = m.get("name")
                    dosage = m.get("dosage") or ""
                    meal = m.get("meal_relation", "anytime")
                    frequency = m.get("frequency") or ""
                    st.write(f"{order}. {name} {dosage} — {frequency} — {meal}")

            else:
                st.warning("No medicines could be clearly extracted from the image.")

            st.markdown("#### 💡 Summary Advice")
            st.info(data.get("overall_advice"))
            if audio_path:
                st.audio(audio_path, format="audio/mp3")

st.divider()
st.caption("Sanjeevani AI v3.0 | 2026 Edition")