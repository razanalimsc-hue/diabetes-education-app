# app.py — Diabetes Education Assistant
# (patient-friendly UI + lifestyle inputs + medication education + ADA targets + PDF + charts + EN/AR + hidden CSV logging)

import os
import io
import uuid
import textwrap
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --------------------------
# Page & session setup
# --------------------------
st.set_page_config(page_title="Diabetes Education Assistant", page_icon="💊", layout="centered")

# Create a per-session anonymous ID for research logging
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --------------------------
# Secrets / .env
# --------------------------
load_dotenv()
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=api_key) if api_key else None
if not api_key:
    st.error("⚠️ No API key found. Add OPENAI_API_KEY in Streamlit secrets or a .env file.")

# --------------------------
# Styles
# --------------------------
st.markdown("""
<style>
.main {font-family: Inter, system-ui, -apple-system, Segoe UI, Arial;}
.small {font-size: 0.9rem; color: #666;}
.card {background: #fff; border: 1px solid #eaeaea; border-radius: 12px; padding: 16px; margin: 8px 0;}
.stButton>button {background:#2563eb;color:#fff;border-radius:10px;padding:10px 18px;font-weight:600;}
hr {border:none;border-top:1px solid #eee;margin: 0.8rem 0;}
</style>
""", unsafe_allow_html=True)

st.title("💊 Diabetes Education Assistant")
st.caption("Friendly explanations. Education only — not medical advice.")

# --------------------------
# Language toggle + helper
# --------------------------
language = st.radio("🌐 Language / اللغة", ["English", "العربية"], horizontal=True)

def t(key: str) -> str:
    if language == "العربية":
        MAP = {
            "Patient Profile": "الملف الشخصي للمريض",
            "Age (years)": "العمر (بالسنوات)",
            "Weight (kg)": "الوزن (كجم)",
            "Diabetes type": "نوع السكري",
            "Activity Level": "مستوى النشاط",
            "Current therapy": "العلاج الحالي",
            "Typical fasting glucose": "سكر الصائم المعتاد",
            "Injections per day": "عدد الحقن يوميًا",
            "Any low glucose last week?": "هل حدث انخفاض في سكر الدم الأسبوع الماضي؟",
            "Injection burden": "مدى العبء من الحقن",
            "Learn topics": "الموضوعات التي ترغب في تعلمها",
            "Medication Details": "تفاصيل الأدوية",
            "Medication name": "اسم الدواء",
            "Route of administration": "طريقة الاستخدام",
            "Get Medication Education": "عرض معلومات الدواء للمريض",
            "Consent": "أفهم أن هذه معلومات تثقيفية فقط وليست نصيحة طبية شخصية.",
            "Generate Summary": "إنشاء ملخص تعليمي",
            "Personalized Education Summary": "الملخص التعليمي المخصص",
            "ADA Reference Targets": "أهداف جمعية السكري الأمريكية (ADA)",
            "Quick Preference Survey": "استبيان تفضيلات سريع",
            "Would you consider films?": "هل تفكر بتجربة شرائط الإنسولين الفموية (مرحلة بحثية) إذا أوصى طبيبك؟",
            "Other methods": "طرق أخرى قد تفكر فيها",
            "Reason to switch": "ما الذي قد يجعلك تفكر في تغيير طريقة الإعطاء؟",
            "Save my preference": "حفظ تفضيلي",
            "Download PDF": "تحميل الملخص PDF",
            "Lifestyle Snapshot": "لمحة عن أسلوب الحياة",
            "Privacy note": "ملاحظة الخصوصية: تُستخدم إجاباتك بشكل مجهول لتحسين الأداة لأغراض البحث فقط.",
        }
        return MAP.get(key, key)
    return key

if language == "العربية":
    st.markdown("<style>body {direction: rtl;}</style>", unsafe_allow_html=True)

# --------------------------
# Helpers: file logging
# --------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def append_csv(path: str, row: dict):
    """Append a single row to CSV, writing header if file doesn't exist."""
    df = pd.DataFrame([row])
    header = not os.path.exists(path)
    df.to_csv(path, mode="a", index=False, header=header, encoding="utf-8")

# --------------------------
# Patient Profile
# --------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(t("Patient Profile"))

    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input(t("Age (years)"), min_value=1, max_value=120, value=35)
        weight = st.number_input(t("Weight (kg)"), min_value=20, max_value=300, value=70)
        diabetes_type = st.selectbox(t("Diabetes type"), ["Type 1", "Type 2", "Gestational"])
    with c2:
        activity_level = st.selectbox(t("Activity Level"), ["Low", "Moderate", "High"])
        therapy_type = st.selectbox(t("Current therapy"), ["Basal-bolus (MDI)", "Insulin pump", "Oral meds only"])
        fasting_range = st.selectbox(t("Typical fasting glucose"), ["<70 mg/dL", "70-130 mg/dL", ">130 mg/dL"])

    c3, c4 = st.columns(2)
    with c3:
        injections_per_day = st.number_input(t("Injections per day"), min_value=0, max_value=10, value=4)
        hypo_last_week = st.radio(t("Any low glucose last week?"), ["No", "Yes"], horizontal=True)
    with c4:
        burden_score = st.slider(f"{t('Injection burden')} (0 = none, 10 = severe)", 0, 10, 5)

    topics = st.multiselect(
        t("Learn topics"),
        ["Low-glucose safety", "New delivery options (research)", "Meal planning",
         "Injection comfort tips", "Monitoring basics", "Exercise basics"],
        default=["Low-glucose safety", "New delivery options (research)"]
    )
    st.markdown(f'<div class="small">🔒 {t("Privacy note")}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# Medication Input
# --------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(f"💊 {t('Medication Details')}")
    med_cols = st.columns([2, 2, 1])
    with med_cols[0]:
        med_name = st.text_input(t("Medication name"), placeholder="e.g., Metformin, Lantus, Empagliflozin")
    with med_cols[1]:
        route = st.selectbox(t("Route of administration"), ["Oral", "Injection (SC/IM/IV)", "Inhaled", "Other"])
    with med_cols[2]:
        med_btn = st.button(t("Get Medication Education"))

    med_education_text = ""
    if med_btn and client and med_name.strip():
        with st.spinner("Fetching medication guidance…"):
            try:
                lang_note = "Write in Arabic." if language == "العربية" else "Write in English."
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system",
                         "content": "You are a diabetes educator. Provide ADA- and FDA-aligned patient education. No dosing."},
                        {"role": "user",
                         "content": f"{lang_note} Provide a short patient handout about '{med_name}' via {route}: "
                                    f"What it is (class), typical use, when/how to take, common side effects, safety red flags, and a reminder to follow clinician instructions."}
                    ],
                    max_tokens=600,
                    temperature=0.2
                )
                med_education_text = resp.choices[0].message.content.strip()
                st.success("📘")
                st.write(med_education_text)
            except Exception as e:
                st.error(f"Could not fetch medication education: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# Safety Alerts
# --------------------------
if fasting_range == "<70 mg/dL":
    st.error("🔴 Fasting glucose includes low values (<70 mg/dL). Follow your clinician’s plan and seek care if needed.")
elif fasting_range == ">130 mg/dL":
    st.warning("🟠 Fasting glucose above target (>130 mg/dL). ADA fasting target is 80–130 mg/dL. Discuss with your clinician.")

# --------------------------
# ADA References
# --------------------------
with st.expander(f"📖 {t('ADA Reference Targets')}"):
    st.markdown(
        "- **Fasting:** 80–130 mg/dL  \n"
        "- **Post-meal (1–2h):** <180 mg/dL  \n"
        "- **A1C:** <7% *(individualized)*  \n\n"
        "Resources:  \n"
        "- ADA Hypoglycemia education: https://diabetes.org/health-wellness/medication/oral-medications-and-insulin/hypoglycemia-low-blood-glucose  \n"
        "- ADA Standards of Care (glycemic targets): https://diabetesjournals.org/care/issue  \n"
        "- CDC Carb Counting Basics: https://www.cdc.gov/diabetes/managing/eat-well.html"
    )

# --------------------------
# Consent + Summary button
# --------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
consent = st.checkbox(t("Consent"), value=True)
gen_btn = st.button(f"✨ {t('Generate Summary')}")
st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# LLM helpers
# --------------------------
def build_prompt():
    lang_note = "Write in Arabic." if language == "العربية" else "Write in English."
    return f"""
System role: You are a kind, clear diabetes education assistant.
Audience: Adults with diabetes (patients).
Tone: Warm, plain language. NO dosing advice. Education only. ADA/FDA-aligned.

{lang_note}

User profile:
- Age: {age}
- Weight: {weight} kg
- Activity level: {activity_level}
- Diabetes type: {diabetes_type}
- Therapy: {therapy_type}
- Injections/day: {injections_per_day}
- Fasting glucose (typical): {fasting_range}
- Any low glucose last week: {hypo_last_week}
- Injection burden (0–10): {burden_score}
- Topics of interest: {topics}
- Medications (free text): {med_name} via {route if med_name else ''}

Write a structured, patient-friendly plan:

1) Disclaimer (education only).
2) Your current regimen (restate in simple words; mention listed medications WITHOUT dosing).
3) ADA glycemic targets (fasting, post-meal, A1C) with note they’re individualized.
4) Lifestyle self-care (Diet, Exercise, Monitoring, Stress/Sleep) — short bullets and practical cues.
5) Injection comfort & adherence — short tips if on insulin.
6) Red flags & safety — when to contact a clinician and why.
7) Medication education summary — one paragraph (if a medication was given); remind to follow clinician instructions.
8) New delivery option: Buccal insulin films (research stage) — one short paragraph.
9) Ask: “Would you consider this option if your clinician recommends it?”
10) References — ADA/CDC titles (no URLs needed; URLs will be shown elsewhere in the app).

Keep it concise, scannable (bullets, short sentences).
"""

def call_llm(prompt: str) -> str:
    if not client:
        return ""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a diabetes educator. Be clear, kind, and safe. No dosing."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.2
    )
    return resp.choices[0].message.content.strip()

# --------------------------
# PDF helper (reportlab)
# --------------------------
def pdf_from_text(summary_text: str, meta: dict) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def draw_wrapped(text, x=40, y_start=height-90, line_height=14, wrap=92):
        y = y_start
        for paragraph in text.split("\n"):
            wrapped = textwrap.wrap(paragraph, wrap) if paragraph else [""]
            for line in wrapped:
                c.drawString(x, y, line)
                y -= line_height
                if y < 60:  # new page
                    c.showPage()
                    y = height - 60
        return y

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-40, "Diabetes Education Summary")
    c.setFont("Helvetica", 10)
    c.drawString(40, height-56, f"Generated: {datetime.utcnow().isoformat(timespec='seconds')} UTC")

    # Meta block
    c.setFont("Helvetica", 11)
    meta_lines = (
        f"Age: {meta['age']}   Weight: {meta['weight']} kg   Activity: {meta['activity']}",
        f"Type: {meta['dtype']}   Therapy: {meta['therapy']}   Injections/day: {meta['injections']}",
        f"Fasting glucose (typical): {meta['fasting']}   Hypo last week: {meta['hypo']}",
        f"Medication: {meta['med']}"
    )
    y = height - 80
    for line in meta_lines:
        c.drawString(40, y, line)
        y -= 14

    y -= 6
    c.line(40, y, width-40, y)
    y -= 18

    c.setFont("Helvetica", 11)
    draw_wrapped(summary_text, x=40, y_start=y, line_height=14, wrap=95)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

# --------------------------
# Generate summary (with hidden CSV logging)
# --------------------------
summary_text = ""
if gen_btn:
    if not consent:
        st.warning("Please confirm the consent checkbox first.")
    elif not client:
        st.error("API not configured.")
    else:
        with st.spinner("Generating your education summary…"):
            try:
                prompt = build_prompt()
                summary_text = call_llm(prompt)
                if not summary_text:
                    st.error("Model returned empty response.")
                else:
                    st.subheader(f"📘 {t('Personalized Education Summary')}")
                    st.write(summary_text)

                    # Lifestyle chart
                    st.subheader(f"📊 {t('Lifestyle Snapshot')}")
                    exercise_score = 5 if activity_level == "Low" else 7 if activity_level == "Moderate" else 9
                    lifestyle_scores = {
                        "Diet awareness": 6,
                        "Exercise": exercise_score,
                        "Monitoring": 7,
                        "Stress/Sleep": 5
                    }
                    df = pd.DataFrame.from_dict(lifestyle_scores, orient="index", columns=["Score"])
                    st.bar_chart(df)

                    # PDF download
                    meta = {
                        "age": age, "weight": weight, "activity": activity_level,
                        "dtype": diabetes_type, "therapy": therapy_type,
                        "injections": injections_per_day, "fasting": fasting_range,
                        "hypo": hypo_last_week, "med": (med_name or "—")
                    }
                    pdf_bytes = pdf_from_text(summary_text, meta)
                    st.download_button(
                        label=f"⬇️ {t('Download PDF')}",
                        data=pdf_bytes,
                        file_name="diabetes_education_summary.pdf",
                        mime="application/pdf"
                    )

                    # 🔒 Hidden research log: summaries.csv
                    try:
                        append_csv(
                            os.path.join(DATA_DIR, "summaries.csv"),
                            {
                                "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
                                "session_id": st.session_state.session_id,
                                "language": language,
                                "age": age,
                                "weight": weight,
                                "activity_level": activity_level,
                                "diabetes_type": diabetes_type,
                                "therapy_type": therapy_type,
                                "injections_per_day": injections_per_day,
                                "fasting_range": fasting_range,
                                "hypo_last_week": hypo_last_week,
                                "burden_score": burden_score,
                                "topics": ";".join(topics),
                                "medication_name": med_name,
                                "route": route,
                                "summary_text": summary_text
                            }
                        )
                    except Exception as log_err:
                        st.info(f"(Research log skipped: {log_err})")

            except Exception as e:
                st.error(f"Could not generate summary: {e}")

# --------------------------
# Survey (with hidden CSV logging)
# --------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader(f"📋 {t('Quick Preference Survey')}")
survey_choice = st.radio(t("Would you consider films?"), ["Yes", "Maybe", "No"], horizontal=True)
other_methods = st.multiselect(t("Other methods"),
                               ["Insulin Pump", "Inhaled insulin", "Oral insulin (research)", "Traditional injections"])
switch_reason = st.text_input(t("Reason to switch"))
if st.button(t("Save my preference")):
    st.success("✅ Saved. Thank you!")
    # 🔒 Hidden research log: surveys.csv
    try:
        append_csv(
            os.path.join(DATA_DIR, "surveys.csv"),
            {
                "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
                "session_id": st.session_state.session_id,
                "language": language,
                "diabetes_type": diabetes_type,
                "therapy_type": therapy_type,
                "fasting_range": fasting_range,
                "injections_per_day": injections_per_day,
                "survey_choice": survey_choice,
                "other_methods": ";".join(other_methods) if other_methods else "",
                "switch_reason": switch_reason
            }
        )
    except Exception as log_err:
        st.info(f"(Survey log skipped: {log_err})")
st.markdown('</div>', unsafe_allow_html=True)
