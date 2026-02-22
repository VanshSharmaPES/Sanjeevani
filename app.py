#!/usr/bin/env python3
# app.py
import streamlit as st
import os
import pandas as pd
from ai_engine import analyze_medicine_image, analyze_prescription_image
import time

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Sanjeevani AI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
    
)

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
    :root {
        --primary-color: #004a99;
        --secondary-color: #00A8FF;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f9fa;
    }
    
    .stTabs [data-baseweb="tab-list"] button {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        background-color: #f0f2f6;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #004a99;
        color: white;
        border-color: #004a99;
    }
    
    .stCameraInput {
        border: 3px solid #004a99 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .stFileUploadDropzone {
        border: 2px dashed #004a99 !important;
        border-radius: 12px !important;
        padding: 30px !important;
    }
    
    .header-title {
        background: linear-gradient(135deg, #004a99 0%, #00a8ff 100%);
        color: white;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,74,153,0.2);
    }
</style>
""", unsafe_allow_html=True)

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

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### ⚙️ Settings & Preferences")
    
    # Initialize session state
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "Scan Medicine Strip"
    if "language" not in st.session_state:
        st.session_state.language = "English"
    
    st.session_state.app_mode = st.radio(
        "Select Mode",
        ["Scan Medicine Strip", "Read Prescription"],
        index=0 if st.session_state.app_mode == "Scan Medicine Strip" else 1
    )
    
    st.session_state.language = st.selectbox(
        "Preferred Language",
        ["English", "Hindi", "Kannada", "Tamil", "Telugu"]
    )
    
    st.divider()
    st.markdown("### 📋 About This Tool")
    if st.session_state.app_mode == "Scan Medicine Strip":
        st.info("""
        **Scan Medicine Strip**: Upload or capture a medicine strip/box to:
        - Identify the medicine and active ingredients
        - Check dosage levels and suitability
        - Learn about medical conditions it treats
        - Get age group recommendations
        """)
    else:
        st.info("""
        **Read Prescription**: Upload or scan a doctor's prescription to:
        - Extract all medicines in reading order
        - Show dosage and timing information
        - Suggest alternative medicines
        - Play audio instructions
        """)
    
    st.divider()
    st.caption("🏥 Sanjeevani v4.0 | Made with ❤️ for India")

# ========== MAIN CONTENT ==========
st.markdown("""
<div class="header-title">
    <h1>💊 Sanjeevani AI</h1>
    <p>Your Smart Medical Assistant</p>
</div>
""", unsafe_allow_html=True)

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
    if st.session_state.app_mode == "Scan Medicine Strip":
        with st.spinner("🔍 AI is analyzing the medicine..."):
            data, audio_path = analyze_medicine_image(image_to_process, target_language=st.session_state.language)

        if "error" in data:
            st.error(f"❌ **Error:** {data['error']}")
        else:
            st.success(f"✅ Medicine: {data.get('medicine_name')}")

            col1, col2 = st.columns([1.5, 1])
            with col1:
                st.markdown("#### 💊 Medicine Details")
                
                active_salts = data.get('active_salts', [])
                if active_salts:
                    salts_html = " · ".join([f"<code>{salt}</code>" for salt in active_salts])
                    st.markdown(f"**Active Salts:**  {salts_html}", unsafe_allow_html=True)
                else:
                    st.write("**Active Salts:** N/A")
                
                dosage = data.get('dosage_strength', 'N/A')
                st.write(f"**Dosage Strength:** `{dosage}`")

                is_high = data.get("is_high_dosage", False)
                if is_high:
                    st.warning(f"⚠️ **HIGH DOSAGE** — {data.get('dosage_info', '')}")
                else:
                    st.success(f"✔️ **Normal Dosage** — {data.get('dosage_info', '')}")

                conditions = data.get("conditions", [])
                if conditions:
                    cond_text = ", ".join(conditions)
                    st.info(f"**Used for:** {cond_text}")
                else:
                    st.write("**Used for:** Not specified")

                what_it_does = data.get('what_it_does', '')
                if what_it_does and what_it_does != 'N/A':
                    st.markdown(f"**How it works:** {what_it_does}")

                age_group = data.get('suitable_age_group', 'N/A')
                st.write(f"**Suitable Age Group:** `{age_group}`")

            with col2:
                st.markdown("#### 💡 Safety Advice")
                advice_text = data.get('advice')
                if advice_text:
                    st.info(advice_text)
                else:
                    st.warning("No advice available")
                
                if audio_path:
                    st.markdown("---")
                    st.markdown("🔊 **Audio Guide**")
                    st.audio(audio_path, format="audio/mp3")
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except:
                        pass

    elif st.session_state.app_mode == "Read Prescription":
        with st.spinner("🔍 AI is reading the prescription..."):
            data, audio_path = analyze_prescription_image(image_to_process, target_language=st.session_state.language)

        if "error" in data:
            st.error(f"❌ **Error:** {data['error']}")
        else:
            st.success("✅ Prescription Analyzed Successfully")

            st.markdown("---")
            st.markdown("### 📝 Medication Schedule (In Order)")
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
                
                st.dataframe(
                    df.style.format(precision=0),
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("---")
                st.markdown("### 📋 Medicine Purpose & Alternatives")

                # Create expandable sections for each medicine
                for m in medicines_sorted:
                    name = m.get("name", "Unknown")
                    salts = m.get("active_salts", [])
                    alts = m.get("alternatives", [])
                    purpose = m.get("purpose", "")
                    
                    with st.expander(f"💊 {name} (Order {m.get('order')})"):
                        if purpose:
                            st.markdown(f"**What it does:** {purpose}")
                        
                        if salts:
                            st.write(f"**Active Ingredients:** {', '.join(salts)}")
                        
                        if alts:
                            st.markdown("**🔄 Alternative Medicines (same salts):**")
                            for alt in alts:
                                st.write(f"  • {alt}")
                        else:
                            st.caption("No alternatives found")

            else:
                st.warning("⚠️ No medicines could be clearly extracted from the image. Please try again with a clearer image.")

            st.markdown("---")
            st.markdown("### 🎯 Overall Instructions")
            overall_advice = data.get("overall_advice")
            if overall_advice:
                st.info(overall_advice)
            if audio_path:
                st.markdown("---")
                st.markdown("🔊 **Audio Instructions**")
                st.audio(audio_path, format="audio/mp3")
                try:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except:
                    pass

st.divider()
st.markdown("""
<div style="text-align: center; padding: 20px; color: #666;">
    <p>💊 <strong>Sanjeevani AI v4.0</strong> | Your Digital Healthcare Assistant</p>
    <p style="font-size: 0.9em;">Made with ❤️ | Secure • Fast • Accessible</p>
</div>
""", unsafe_allow_html=True)
