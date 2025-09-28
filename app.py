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

# NEW: for PDF export
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import textwrap

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
# NEW: Language toggle (keeps your layout)
# --------------------------
language = st.radio("🌐 Language / اللغة", ["English", "العربية"], horizontal=True)

def tr(label):
    if language == "العربية":
        mapping = {
            "🧑‍⚕️ Patient Profile": "🧑‍⚕️ الملف الشخصي للمريض",
            "Diabetes type": "نوع السكري",
            "Current therapy": "العلاج الحالي",
            "Typical fasting glucose": "سكر الصائم المعتاد",
            "Injections per day": "عدد الحقن يوميًا",
            "Any low glucose last week?": "هل حدث انخفاض في سكر الدم الأسبوع الماضي؟",
            "Injection burden (0 = none, 10 = severe)": "مدى العبء من الحقن (0 لا يوجد، 10 شديد)",
            "What would you like to learn about?": "ما الذي ترغب في التعرف عليه؟",
            "💊 Medication Details": "💊 تفاصيل الأدوية",
            "Enter the name of your medication:": "أدخل اسم الدواء:",
            "Route of administration": "طريقة الاستخدام",
            "Get Medication Education": "عرض معلومات الدواء",
            "📖 ADA Reference Targets": "📖 أهداف الجمعية الأمريكية للسكري (ADA)",
            "📋 Quick Preference Survey": "📋 استبيان تفضيلات سريع",
            "Would you consider buccal insulin films (research-stage) if your clinician recommends it?":
                "هل تفكر بتجربة شرائط الإنسولين الفموية (مرحلة بحثية) إذا أوصى طبيبك؟",
            "Other delivery methods you'd consider:": "طرق أخرى قد تفكر فيها:",
            "What would make you consider switching delivery method?": "ما الذي قد يجعلك تفكر في تغيير طريقة الإعطاء؟",
            "Save my preference": "حفظ تفضيلي",
            "✨ Generate Education Summary": "✨ إنشاء ملخص تعليمي",
            "📘 Personalized Education Summary": "📘 الملخص التعليمي المخصص",
        }
        return mapping.get(label, label)
    return label

if language == "العربية":
    st.markdown("<style>body {direction: rtl;}</style>", unsafe_allow_html=True)

# --------------------------
# Patient Profile Form
# --------------------------
with st.container():
    st.subheader(tr("🧑‍⚕️ Patient Profile"))
    c1, c2 = st.columns(2)

    with c1:
        # NEW: lifestyle inputs added here (minimal change)
        age = st.number_input("Age (years)" if language == "English" else "العمر (بالسنوات)", 1, 120, 35)
        weight = st.number_input("Weight (kg)" if language == "English" else "الوزن (كجم)", 20, 300, 70)
        activity_level = st.selectbox("Activity level" if language == "English" else "مستوى النشاط",
                                      ["Low", "Moderate", "High"])
        diabetes_type = st.selectbox(tr("Diabetes type"), ["Type 1", "Type 2"])
        therapy_type = st.selectbox(tr("Current therapy"), ["Basal-bolus (MDI)", "Insulin pump", "Oral meds only"])
    with c2:
        fasting_range = st.selectbox(tr("Typical fasting glucose"), ["<70 mg/dL", "70-130 mg/dL", ">130 mg/dL"])
        injections_per_day = st.number_input(tr("Injections per day"), 0, 10, 4)
        hypo_last_week = st.radio(tr("Any low glucose last week?"), ["No", "Yes"])
        burden_score = st.slider(tr("Injection burden (0 = none, 10 = severe)"), 0, 10, 5)

    topics = st.multiselect(
        tr("What would you like to learn about?"),
        ["Low-glucose safety", "New delivery options (research)", "Meal planning",
         "Injection comfort tips", "Monitoring basics", "Exercise basics"]
    )

# --------------------------
# NEW: Optional Lifestyle Inputs (for evidence-based chart)
# --------------------------
with st.expander("🧩 Optional lifestyle details (improves your snapshot)" if language == "English"
                 else "🧩 تفاصيل نمط الحياة (اختياري)"):
    cL1, cL2 = st.columns(2)
    with cL1:
        activity_minutes = st.number_input(
            "Weekly activity (minutes)" if language == "English" else "النشاط الأسبوعي (دقائق)",
            min_value=0, max_value=10000, value=0,
            help="ADA recommends ≥150 min/week." if language == "English" else "توصي ADA بـ 150 دقيقة/أسبوع أو أكثر."
        )
        sleep_hours = st.number_input(
            "Average sleep (hours/night)" if language == "English" else "متوسط النوم (ساعات/ليلة)",
            min_value=0.0, max_value=24.0, value=0.0, step=0.5,
            help="7–9 hours/night is generally associated with better outcomes." if language == "English"
                 else "٧–٩ ساعات/ليلة ترتبط بنتائج أفضل."
        )
    with cL2:
        diet_adherence = st.selectbox(
            "Following a meal plan most days?" if language == "English" else "اتباع خطة غذائية معظم الأيام؟",
            ["Prefer not to say", "Rarely", "Sometimes", "Often"] if language == "English"
            else ["أفضل عدم الإفصاح", "نادراً", "أحياناً", "غالباً"]
        )
        monitoring_freq = st.selectbox(
            "Glucose monitoring frequency" if language == "English" else "تواتر مراقبة سكر الدم",
            ["Prefer not to say", "Less than daily", "Daily", "Multiple times/day"] if language == "English"
            else ["أفضل عدم الإفصاح", "أقل من يومي", "يومي", "عدة مرات/اليوم"]
        )

# --------------------------
# Medication Input Section
# --------------------------
with st.container():
    st.subheader(tr("💊 Medication Details"))
    medication_name = st.text_input(tr("Enter the name of your medication:"))
    route = st.selectbox(tr("Route of administration"), ["Oral", "Injection (IV/IM/SC)", "Other"])

    if st.button(tr("Get Medication Education")):
        if medication_name:
            with st.spinner("Fetching medication guidance..." if language == "English" else "جاري جلب معلومات الدواء..."):
                try:
                    # Ask LLM to provide ADA/FDA-based patient education
                    lang_note = "Write in Arabic." if language == "العربية" else "Write in English."
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a diabetes educator. Provide ADA/FDA-aligned patient education."},
                            {"role": "user", "content": f"Give patient-friendly education about {medication_name}, taken via {route}. \
                                Include how it works, when to take it, precautions, and FDA/ADA notes if available. {lang_note}"}
                        ],
                        max_tokens=600,
                        temperature=0.2
                    )
                    st.success("📘 Medication Education" if language == "English" else "📘 معلومات الدواء")
                    st.write(response.choices[0].message.content)

                except Exception as e:
                    st.error(f"⚠️ Could not fetch education: {e}")
        else:
            st.warning("Please enter a medication name first." if language == "English" else "يرجى إدخال اسم الدواء أولاً.")

# --------------------------
# Safety Alerts
# --------------------------
if fasting_range == "<70 mg/dL":
    st.error("🔴 Your fasting glucose includes **low values (<70 mg/dL)**. Follow your clinician’s plan and seek care if needed."
             if language == "English" else
             "🔴 سكر الصائم لديك يتضمن قيماً منخفضة (<70 mg/dL). اتبع خطة طبيبك واطلب المساعدة إذا لزم الأمر.")
if fasting_range == ">130 mg/dL":
    st.warning("🟠 Your fasting glucose is above target (>130 mg/dL). ADA recommends 80–130 mg/dL fasting. Discuss with your clinician."
               if language == "English" else
               "🟠 سكر الصائم أعلى من الهدف (>130 mg/dL). توصي ADA بأن يكون الصائم 80–130 mg/dL. ناقش ذلك مع طبيبك.")

# --------------------------
# ADA Reference Ranges
# --------------------------
with st.expander(tr("📖 ADA Reference Targets")):
    if language == "English":
        st.markdown("""
        **ADA Standards of Care**:
        - Fasting: 80–130 mg/dL  
        - Post-meal: <180 mg/dL  
        - A1C: <7% (individualized)  
        """)
    else:
        st.markdown("""
        **إرشادات ADA**:
        - الصائم: 130–80 mg/dL  
        - بعد الوجبة: أقل من 180 mg/dL  
        - A1C: أقل من 7% (وفق الحالة)  
        """)

# --------------------------
# Survey (after Q8)
# --------------------------
with st.container():
    st.subheader(tr("📋 Quick Preference Survey"))
    survey_choice = st.radio(tr("Would you consider buccal insulin films (research-stage) if your clinician recommends it?"),
                             ["Yes", "Maybe", "No"] if language == "English" else ["نعم", "ربما", "لا"])
    other_methods = st.multiselect(tr("Other delivery methods you'd consider:"),
                                   ["Insulin Pump", "Oral insulin (research)", "Inhaled insulin", "Traditional injections"]
                                   if language == "English" else
                                   ["مضخة إنسولين", "إنسولين فموي (بحثي)", "إنسولين مستنشق", "حقن تقليدية"])
    switch_reason = st.text_input(tr("What would make you consider switching delivery method?"))

    if st.button(tr("Save my preference")):
        st.success("✅ Thank you! Your preferences have been saved."
                   if language == "English" else "✅ شكراً لك! تم حفظ تفضيلاتك.")
# --- Silent CSV logging (optional, invisible to patient) ---
try:
    import os

    row = {
        "timestamp_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "language": language,
        "diabetes_type": diabetes_type,
        "therapy_type": therapy_type,
        "injections_per_day": injections_per_day,
        "fasting_range": fasting_range,
        "hypo_last_week": hypo_last_week,
        "burden_score": burden_score,
        "topics": ";".join(topics),
        "survey_choice": survey_choice,
        "other_methods": ";".join(other_methods),
        "switch_reason": switch_reason,
        "age": age,
        "weight": weight,
        "activity_level": activity_level,
        "medication_name": medication_name,
        "route": route,
    }

    csv_path = "survey_logs.csv"
    df_new = pd.DataFrame([row])

    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        df_out = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_out = df_new

    df_out.to_csv(csv_path, index=False)
except Exception:
    # fail silently; no UI shown to the patient
    pass

# --------------------------
# NEW: helper to create a simple PDF from text (keeps your structure)
# --------------------------
def make_pdf(summary_text: str, filename: str = "diabetes_summary.pdf") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 40, "Diabetes Education Summary")

    # Timestamp
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 56, f"Generated: {datetime.utcnow().isoformat(timespec='seconds')} UTC")

    c.setFont("Helvetica", 11)
    y = height - 80
    wrap_width = 95
    line_h = 14

    # Wrap text neatly
    for para in summary_text.split("\n"):
        lines = textwrap.wrap(para, wrap_width) if para else [""]
        for ln in lines:
            c.drawString(40, y, ln)
            y -= line_h
            if y < 60:
                c.showPage()
                y = height - 60

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

# --------------------------
# Education Summary
# --------------------------
if st.button(tr("✨ Generate Education Summary")):
    if not api_key:
        st.error("⚠️ No API key configured." if language == "English" else "⚠️ لم يتم إعداد مفتاح API.")
    else:
        with st.spinner("Generating personalized summary..." if language == "English" else "جاري إنشاء الملخص..."):
            try:
                # ORIGINAL PROMPT + NEW FIELDS (age, weight, activity + meds info for clarity)
                prompt = f"""
                Patient profile:
                - Age: {age}
                - Weight: {weight} kg
                - Activity level: {activity_level}
                - Type: {diabetes_type}
                - Therapy: {therapy_type}
                - Injections/day: {injections_per_day}
                - Fasting glucose: {fasting_range}
                - Hypo last week: {hypo_last_week}
                - Burden score: {burden_score}
                - Topics: {topics}
                - Medication (if provided): {medication_name} via {route if medication_name else ""}
                
                Please provide a patient-friendly education summary covering:
                - Diet, Exercise, Monitoring, Stress/Sleep
                - ADA glycemic targets (general, individualized)
                - Injection comfort tips
                - Red flags & safety
                - New delivery option: Buccal insulin films (research-stage)
                - Use short headings and bullet points. No dosing advice.
                {"Write the whole summary in Arabic." if language == "العربية" else "Write the whole summary in English."}
                """

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a diabetes educator. Provide clear, supportive explanations only. No dosing."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=900,
                    temperature=0.3
                )

                st.subheader(tr("📘 Personalized Education Summary"))
                summary_text = response.choices[0].message.content
                st.write(summary_text)

                # --- Evidence-based Lifestyle Snapshot (scores 0–10) ---
                if activity_minutes >= 150:
                    exercise_score = 10
                elif activity_minutes >= 90:
                    exercise_score = 7
                elif activity_minutes > 0:
                    exercise_score = 4
                else:
                    exercise_score = 0

                if 7.0 <= sleep_hours <= 9.0:
                    sleep_score = 10
                elif sleep_hours in (6.0, 10.0):
                    sleep_score = 6
                else:
                    sleep_score = 3 if sleep_hours > 0 else 0

                # Diet/monitor maps — keep exactly as proxies
                diet_map_en = {"Prefer not to say": 0, "Rarely": 3, "Sometimes": 6, "Often": 9}
                diet_map_ar = {"أفضل عدم الإفصاح": 0, "نادراً": 3, "أحياناً": 6, "غالباً": 9}
                diet_score = (diet_map_en if language == "English" else diet_map_ar).get(diet_adherence, 0)

                monitor_map_en = {"Prefer not to say": 0, "Less than daily": 4, "Daily": 7, "Multiple times/day": 9}
                monitor_map_ar = {"أفضل عدم الإفصاح": 0, "أقل من يومي": 4, "يومي": 7, "عدة مرات/اليوم": 9}
                monitor_score = (monitor_map_en if language == "English" else monitor_map_ar).get(monitoring_freq, 0)

                st.subheader("📊 Lifestyle Snapshot (educational)" if language == "English" else "📊 لمحة عن نمط الحياة (تعليمي)")
                df = pd.DataFrame(
                    {"Score": [diet_score, exercise_score, monitor_score, sleep_score]},
                    index=(["Diet awareness", "Exercise", "Monitoring", "Sleep"]
                           if language == "English" else ["الوعي الغذائي", "التمارين", "المراقبة", "النوم"])
                )
                st.bar_chart(df)

                with st.expander("What do these scores mean? (sources)" if language == "English" else "ماذا تعني هذه الدرجات؟ (مصادر)"):
                    st.markdown(
                        "- **Exercise:** ≥150 min/week of moderate activity is recommended for most adults with diabetes. [ADA / AHA]\n"
                        "- **Sleep:** ~7–9 h/night is associated with better glycemic outcomes; short or long sleep links with higher A1c/risk. [Diabetes Care, meta-analyses]\n"
                        "- **Diet awareness & Monitoring:** education proxies aligned with ADA lifestyle & nutrition guidance."
                    )

                # NEW: PDF download button
                pdf_bytes = make_pdf(summary_text)
                st.download_button(
                    "⬇️ Download PDF Summary" if language == "English" else "⬇️ تحميل الملخص PDF",
                    data=pdf_bytes,
                    file_name="diabetes_summary.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"⚠️ Could not generate summary: {e}")
