#!/usr/bin/env python3
# app.py
import streamlit as st
import os
import pandas as pd
from ai_engine import analyze_medicine_image, analyze_prescription_image

st.set_page_config(page_title="Sanjeevani AI", page_icon="💊", layout="centered")

# --- Camera Permission JS for network URLs ---
st.markdown("""
<script>
async function requestCameraPermission() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach(track => track.stop());
    } catch (err) {
        console.log("Camera permission denied or unavailable:", err);
    }
}
if (location.protocol === "https:" || location.hostname !== "localhost") {
    requestCameraPermission();
}
</script>
""", unsafe_allow_html=True)

# Custom UI
st.markdown("<style>.stCameraInput { border: 2px solid #004a99; border-radius: 10px; }</style>", unsafe_allow_html=True)

st.title("💊 Sanjeevani")

# SIDEBAR CONTROLS
st.sidebar.header("Settings")
app_mode = st.sidebar.radio("Select Mode", ["Scan Medicine Strip", "Read Prescription"])
language = st.sidebar.selectbox("Preferred Language", ["English", "Hindi", "Kannada", "Tamil", "Telugu"])

if app_mode == "Scan Medicine Strip":
    st.write("Scan your medicine to learn about its usage, dosage, and suitability.")
else:
    st.write("Upload or scan a doctor's prescription to understand your dosage schedule and find alternatives.")

# TABBED INTERFACE
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
        with st.spinner("🔍 AI is analyzing the medicine..."):
            data, audio_path = analyze_medicine_image(image_to_process, target_language=language)

        if "error" in data:
            st.error(data['error'])
        else:
            st.success(f"✅ Medicine: {data.get('medicine_name')}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 💊 Medicine Details")
                st.write(f"**Active Salts:** {', '.join(data.get('active_salts', [])) or 'N/A'}")
                st.write(f"**Dosage Strength:** {data.get('dosage_strength', 'N/A')}")

                is_high = data.get("is_high_dosage", False)
                if is_high:
                    st.warning(f"⚠️ HIGH DOSAGE — {data.get('dosage_info', '')}")
                else:
                    st.info(f"✔️ Normal Dosage — {data.get('dosage_info', '')}")

                conditions = data.get("conditions", [])
                if conditions:
                    st.write(f"**Used for:** {', '.join(conditions)}")

                st.write(f"**Suitable Age Group:** {data.get('suitable_age_group', 'N/A')}")

            with col2:
                st.markdown("#### 💡 Advice")
                st.write(data.get('advice'))
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")
                    os.remove(audio_path)

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
                medicines_sorted = sorted(medicines, key=lambda m: m.get("order", 999))

                # Display table
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

                # Medicine alternatives only (no duplicate prescription details)
                st.markdown("#### 🔄 Medicine Alternatives")
                has_any_alt = False
                for m in medicines_sorted:
                    name = m.get("name", "Unknown")
                    salts = m.get("active_salts", [])
                    alts = m.get("alternatives", [])
                    if alts:
                        has_any_alt = True
                        salts_str = f" ({', '.join(salts)})" if salts else ""
                        st.markdown(f"**{name}**{salts_str}")
                        st.info(f"🔄 Alternatives: {', '.join(alts)}")
                if not has_any_alt:
                    st.caption("No alternatives found for any medicine.")
            else:
                st.warning("No medicines could be clearly extracted from the image.")

            st.markdown("#### 💡 Summary Advice")
            st.info(data.get("overall_advice"))
            if audio_path:
                st.audio(audio_path, format="audio/mp3")
                os.remove(audio_path)

st.divider()
st.caption("Sanjeevani AI v4.0 | 2026 Edition")
