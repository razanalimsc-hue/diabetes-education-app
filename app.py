# app.py – Diabetes Education Assistant (extended with lifestyle inputs, PDF export, charts, and language toggle)

# --------------------------
# Imports
# --------------------------
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("⚠️ No API key found. Please add your OpenAI API key in Streamlit secrets or .env file.")
else:
    client = OpenAI(api_key=api_key)

# --------------------------
# Page config & style
# --------------------------
st.set_page_config(page_title="Diabetes Education Assistant", page_icon="💊", layout="centered")

st.markdown("""
    <style>
    .main {font-family: 'Arial', sans-serif;}
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        font-size: 16px;
        padding: 10px 20px;
    }
    .stAlert {
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💊 Diabetes Education Assistant")
st.caption("Friendly explanations. No medical advice.")

# --------------------------
# Language toggle
# --------------------------
language = st.radio("🌐 Select Language / اختر اللغة", ["English", "العربية"], horizontal=True)

def translate(text, lang):
    if lang == "العربية":
        translations = {
            "Patient Profile": "الملف الشخصي للمريض",
            "Age (years)": "العمر (بالسنوات)",
            "Weight (kg)": "الوزن (كجم)",
            "Diabetes type": "نوع السكري",
            "Activity Level": "مستوى النشاط",
            "Current therapy": "العلاج الحالي",
            "Typical fasting glucose": "مستوى سكر الصائم",
            "Injections per day": "عدد الحقن يومياً",
            "Any low glucose last week?": "هل حدث انخفاض في سكر الدم الأسبوع الماضي؟",
            "Injection burden": "مدى العبء من الحقن",
            "What would you like to learn about?": "ما الذي ترغب في التعرف عليه؟",
        }
        return translations.get(text, text)
    return text

# --------------------------
# Patient Profile Form
# --------------------------
with st.container():
    st.subheader(translate("Patient Profile", language))

    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input(translate("Age (years)", language), min_value=1, max_value=120, value=35)
        weight = st.number_input(translate("Weight (kg)", language), min_value=20, max_value=200, value=70)
        diabetes_type = st.selectbox(translate("Diabetes type", language), ["Type 1", "Type 2", "Gestational"])
    with c2:
        activity_level = st.selectbox(translate("Activity Level", language), ["Low", "Moderate", "High"])
        therapy_type = st.selectbox(translate("Current therapy", language), ["Basal-bolus (MDI)", "Insulin pump", "Oral meds only"])
        fasting_range = st.selectbox(translate("Typical fasting glucose", language), ["<70 mg/dL", "70-130 mg/dL", ">130 mg/dL"])

    injections_per_day = st.number_input(translate("Injections per day", language), 0, 10, 4)
    hypo_last_week = st.radio(translate("Any low glucose last week?", language), ["No", "Yes"])
    burden_score = st.slider(translate("Injection burden", language) + " (0 = none, 10 = severe)", 0, 10, 5)

    topics = st.multiselect(
        translate("What would you like to learn about?", language),
        ["Low-glucose safety", "New delivery options (research)", "Meal planning",
         "Injection comfort tips", "Monitoring basics", "Exercise basics"]
    )

# --------------------------
# Medication Input Section
# --------------------------
with st.container():
    st.subheader("💊 Medication Details")
    medication_name = st.text_input("Enter the name of your medication:")
    route = st.selectbox("Route of administration", ["Oral", "Injection (IV/IM/SC)", "Other"])

    if st.button("Get Medication Education"):
        if medication_name:
            with st.spinner("Fetching medication guidance..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a diabetes educator. Provide ADA/FDA-aligned patient education."},
                            {"role": "user", "content": f"Give patient-friendly education about {medication_name}, taken via {route}. \
                                Include how it works, when to take it, precautions, and FDA/ADA notes if available."}
                        ],
                        max_tokens=500
                    )
                    st.success("📘 Medication Education")
                    st.write(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"⚠️ Could not fetch education: {e}")
        else:
            st.warning("Please enter a medication name first.")

# --------------------------
# Safety Alerts
# --------------------------
if fasting_range == "<70 mg/dL":
    st.error("🔴 Your fasting glucose includes **low values (<70 mg/dL)**. Follow your clinician’s plan and seek care if needed.")
if fasting_range == ">130 mg/dL":
    st.warning("🟠 Your fasting glucose is above target (>130 mg/dL). ADA recommends 80–130 mg/dL fasting. Discuss with your clinician.")

# --------------------------
# ADA Reference Ranges
# --------------------------
with st.expander("📖 ADA Reference Targets"):
    st.markdown("""
    **ADA Standards of Care**:
    - Fasting: 80–130 mg/dL  
    - Post-meal: <180 mg/dL  
    - A1C: <7% (individualized)  
    """)

# --------------------------
# Education Summary + PDF
# --------------------------
def save_summary_to_pdf(text, filename="summary.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    text_obj = c.beginText(40, 750)
    text_obj.setFont("Helvetica", 11)
    for line in text.splitlines():
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.save()
    return filename

if st.button("✨ Generate Education Summary"):
    if not api_key:
        st.error("⚠️ No API key configured.")
    else:
        with st.spinner("Generating personalized summary..."):
            try:
                prompt = f"""
                Patient profile:
                - Age: {age}
                - Weight: {weight}
                - Activity level: {activity_level}
                - Type: {diabetes_type}
                - Therapy: {therapy_type}
                - Injections/day: {injections_per_day}
                - Fasting glucose: {fasting_range}
                - Hypo last week: {hypo_last_week}
                - Burden score: {burden_score}
                - Topics: {topics}
                """

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a diabetes educator. Provide clear, supportive explanations only."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600
                )

                summary_text = response.choices[0].message.content
                st.subheader("📘 Personalized Education Summary")
                st.write(summary_text)

                # PDF download
                pdf_file = save_summary_to_pdf(summary_text, "summary.pdf")
                with open(pdf_file, "rb") as f:
                    st.download_button("⬇️ Download PDF Summary", f, file_name="diabetes_summary.pdf")

                # Lifestyle chart
                st.subheader("📊 Lifestyle Snapshot")
                lifestyle_scores = {
                    "Diet awareness": 6,
                    "Exercise": 5 if activity_level == "Low" else (7 if activity_level == "Moderate" else 9),
                    "Monitoring": 7,
                    "Stress/Sleep": 5
                }
                df = pd.DataFrame.from_dict(lifestyle_scores, orient="index", columns=["Score"])
                st.bar_chart(df)

            except Exception as e:
                st.error(f"⚠️ Could not generate summary: {e}")
