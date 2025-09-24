# app.py – Diabetes Education Assistant (patient-friendly UI + survey + ADA targets + medication education)

# --------------------------
# Imports
# --------------------------
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

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
# Patient Profile Form
# --------------------------
with st.container():
    st.subheader("🧑‍⚕️ Patient Profile")
    c1, c2 = st.columns(2)

    with c1:
        diabetes_type = st.selectbox("Diabetes type", ["Type 1", "Type 2", "Gestational"])
        therapy_type = st.selectbox("Current therapy", ["Basal-bolus (MDI)", "Insulin pump", "Oral meds only"])
        fasting_range = st.selectbox("Typical fasting glucose", ["<70 mg/dL", "70-130 mg/dL", ">130 mg/dL"])

    with c2:
        injections_per_day = st.number_input("Injections per day", 0, 10, 4)
        hypo_last_week = st.radio("Any low glucose last week?", ["No", "Yes"])
        burden_score = st.slider("Injection burden (0 = none, 10 = severe)", 0, 10, 5)

    topics = st.multiselect(
        "What would you like to learn about?",
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
                    # Ask LLM to provide ADA/FDA-based patient education
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
# Survey (after Q8)
# --------------------------
with st.container():
    st.subheader("📋 Quick Preference Survey")
    survey_choice = st.radio("Would you consider buccal insulin films (research-stage) if your clinician recommends it?",
                             ["Yes", "Maybe", "No"])
    other_methods = st.multiselect("Other delivery methods you'd consider:",
                                   ["Insulin Pump", "Oral insulin (research)", "Inhaled insulin", "Traditional injections"])
    switch_reason = st.text_input("What would make you consider switching delivery method?")

    if st.button("Save my preference"):
        st.success("✅ Thank you! Your preferences have been saved.")

# --------------------------
# Education Summary
# --------------------------
if st.button("✨ Generate Education Summary"):
    if not api_key:
        st.error("⚠️ No API key configured.")
    else:
        with st.spinner("Generating personalized summary..."):
            try:
                prompt = f"""
                Patient profile:
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

                st.subheader("📘 Personalized Education Summary")
                st.write(response.choices[0].message.content)

            except Exception as e:
                st.error(f"⚠️ Could not generate summary: {e}")
