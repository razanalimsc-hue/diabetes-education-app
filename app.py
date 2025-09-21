# app.py — Diabetes Education Assistant
# Patient-friendly UI • Expandable sections • Inline survey • ADA alerts • Basic analytics
# (Education only — no medical advice)

import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# =========================
# Page setup & styling
# =========================
st.set_page_config(page_title="Diabetes Education Assistant", page_icon="🩺", layout="centered")
st.markdown("""
<style>
.big-title { font-size: 2.0rem; font-weight: 800; margin-bottom: .25rem; }
.subtle { color:#667085; margin-top:0; }
.card { padding: 1rem 1.25rem; border: 1px solid #EAECF0; border-radius: 14px; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.section { margin-top: 1.25rem; }
.stExpander { border: 1px solid #EAECF0 !important; border-radius: 14px !important; background: #fff !important; box-shadow: 0 1px 2px rgba(16,24,40,.04) !important; margin-bottom: 10px !important; }
.stExpander summary { font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

APP_DISCLAIMER = (
    "⚠️ **Educational only — not medical advice.** "
    "Please don’t change insulin or treatment based on this app. Talk to your clinician."
)
RESPONSES_CSV = "patient_preferences.csv"

# Trusted references (for display)
ADA_HYPO = "https://diabetes.org/diabetes/medication-management/blood-glucose-testing-and-control/low-blood-glucose-hypoglycemia"
ADA_STANDARDS = "https://diabetesjournals.org/care/issue"
CDC_CARB = "https://www.cdc.gov/diabetes/healthy-eating/carb-counting-manage-blood-sugar.html"
REFERENCES = [
    ("ADA: Hypoglycemia (Low Blood Glucose)", ADA_HYPO),
    ("ADA Standards of Care — Glycemic Targets", ADA_STANDARDS),
    ("CDC: Carb Counting Basics", CDC_CARB),
]

# =========================
# API key (env or secrets)
# =========================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("❌ OpenAI key missing. Add `OPENAI_API_KEY` in Streamlit **Settings → Secrets** (cloud) "
             "or a local `.env` file for local runs.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# =========================
# Sidebar info
# =========================
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.write("This tool gives **education only** for people living with diabetes.")
    st.caption(APP_DISCLAIMER)

# =========================
# Form choices
# =========================
DIABETES_TYPES = ["Type 1", "Type 2", "Other / Not sure"]
THERAPY_TYPES = ["Basal–bolus (MDI)", "Premix", "Pump / CSII", "Non-insulin", "Not sure"]
FASTING_RANGES = ["<70 mg/dL", "70–99", "100–125", "126–180", ">180", "Not sure"]
TOPIC_CHOICES = [
    "Low-glucose safety",
    "Monitoring basics",
    "Meal planning",
    "Exercise basics",
    "Injection comfort tips",
    "New delivery options (research)",
]

# =========================
# Session state
# =========================
if "summary_ready" not in st.session_state:
    st.session_state.summary_ready = False
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""
if "saved_inputs" not in st.session_state:
    st.session_state.saved_inputs = None

# =========================
# Prompt builder
# =========================
def build_prompt(user_inputs: dict) -> str:
    return f"""
System role: You are a kind, clear diabetes education assistant.
Audience: Adults with diabetes (patients, not clinicians).
Tone: Warm, encouraging, simple language. Avoid medical jargon.

Rules:
- NO dosing suggestions or insulin adjustments.
- Focus on general education and ADA-aligned safety.
- Always include red flags for when to contact a doctor.
- Mark that buccal insulin films are experimental/research stage.
- Keep output short and scannable (bullets, headings).

User profile:
{user_inputs}

Write a patient-friendly education plan with the following sections:

1) **Disclaimer** (short, single paragraph)
    - Remind them this is education only, not medical advice.

2) **Your Current Regimen (Education)**
    - Restate their diabetes type, therapy type, and injection frequency in friendly language.

3) **ADA Glycemic Targets**
    - General target ranges for fasting, post-meal glucose, and A1C.
    - Remind them these are general and should be individualized with their clinician.

4) **Lifestyle & Self-Care Recommendations**
    - **Diet:** General healthy eating guidance, carb awareness, portion control tips.
    - **Exercise:** Safe activity suggestions (walking, light activity, frequency).
    - **Monitoring:** Reminders for blood glucose checks, foot checks, logging results.
    - **Stress/Sleep:** Simple tips for stress management and good sleep hygiene.

5) **Injection Comfort & Adherence**
    - Simple comfort techniques (site rotation, needle length tips, warming insulin).

6) **Red Flags & Safety**
    - What symptoms or numbers should prompt contacting a doctor (e.g., very high glucose >250 mg/dL, recurrent lows <70 mg/dL, severe symptoms).

7) **New Delivery Option: Buccal Insulin Films (Research Stage)**
    - Briefly explain what it is, why it might help, and note it is experimental.

8) **Question: Would You Consider This Option?**
    - End with a gentle question to engage them.

9) **References**
    - ADA Standards of Care (glycemic targets)
    - ADA Hypoglycemia guidance
    - CDC Carb Counting basics

Output should be formatted with numbered headings like '1) ... 2) ...', with short paragraphs and bullets.
"""

# =========================
# LLM call with friendly errors
# =========================
def call_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Follow safety rules. Education only. No dosing advice."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        msg = str(e)
        if "invalid_api_key" in msg or "401" in msg:
            st.error("🔑 Your OpenAI API key appears **invalid**. Update it in Streamlit **Settings → Secrets** "
                     "as `OPENAI_API_KEY` (no extra spaces).")
        elif "insufficient_quota" in msg or "429" in msg:
            st.error("🔒 Your OpenAI project has **no remaining credits**. Add billing/credits and try again.")
        else:
            st.error(f"LLM error: {msg}")
        return ""

# =========================
# UI header
# =========================
st.markdown('<div class="big-title">🩺 Diabetes Education Assistant</div>', unsafe_allow_html=True)
st.markdown('<p class="subtle">Friendly explanations. No medical advice.</p>', unsafe_allow_html=True)

# =========================
# Patient form
# =========================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Patient Profile")
    c1, c2 = st.columns(2)
    with c1:
        diabetes_type = st.selectbox("Diabetes type", DIABETES_TYPES)
        therapy_type = st.selectbox("Current therapy", THERAPY_TYPES)
        fasting_range = st.selectbox("Typical fasting glucose", FASTING_RANGES)
    with c2:
        injections_per_day = st.number_input("Injections per day", min_value=0, max_value=10, value=4)
        hypo_last_week = st.radio("Any low glucose last week?", ["No", "Yes"], horizontal=True)
        burden_score = st.slider("Injection burden (0 = none, 10 = severe)", 0, 10, 5)

    topics = st.multiselect("What would you like to learn about?", TOPIC_CHOICES,
                            default=["Low-glucose safety", "New delivery options (research)"])

    if topics:
        st.write("**Focus areas:** ", "  ".join([f"`{t}`" for t in topics]))

    consent = st.checkbox("I understand this is education only (not medical advice).", value=True)
    submitted = st.button("✨ Generate Education Summary")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Alerts & targets helper
# =========================
def show_clinical_banners(ui: dict):
    if ui["fasting_range"] in ["126–180", ">180"]:
        st.error("🔴 Your fasting glucose is often **above** the usual target range. Please contact your clinician.")
    if ui["fasting_range"] == "<70 mg/dL":
        st.error("🔴 Your fasting glucose includes **low values** (<70 mg/dL). Follow your clinician’s plan and seek care if needed.")
        st.markdown(f"• ADA Hypoglycemia education: [{ADA_HYPO}]({ADA_HYPO})")

    st.info(f"**ADA general targets:** Fasting **80–130 mg/dL** • Post-meal **<180 mg/dL** • A1C **<7%** (individualized) — "
            f"[ADA Standards]({ADA_STANDARDS})")

# =========================
# Generate summary
# =========================
if submitted:
    if not consent:
        st.warning("Please tick the consent box to continue.")
    else:
        user_inputs = {
            "diabetes_type": diabetes_type,
            "therapy_type": therapy_type,
            "injections_per_day": injections_per_day,
            "fasting_range": fasting_range,
            "hypo_last_week": hypo_last_week,
            "burden_score": burden_score,
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat()
        }
        with st.spinner("Generating your summary…"):
            summary = call_llm(build_prompt(user_inputs))
        st.session_state.summary_text = summary
        st.session_state.saved_inputs = user_inputs
        st.session_state.summary_ready = bool(summary)

# =========================
# Section parsing & rendering
# =========================
HEADING_RE = re.compile(r"^\s*(\d+)\)\s*(.+?)\s*$")
def split_into_sections(markdown_text: str):
    lines = markdown_text.splitlines()
    sections, current = [], {"num": None, "title": None, "body": []}

    def flush():
        if current["num"] is not None:
            sections.append((current["num"], current["title"], "\n".join(current["body"]).strip()))

    for ln in lines:
        m = HEADING_RE.match(ln)
        if m:
            flush()
            current = {"num": int(m.group(1)), "title": m.group(2), "body": []}
        else:
            current["body"].append(ln)
    flush()
    return sections

def render_summary_expandable(text: str, ui: dict):
    sections = split_into_sections(text)
    for num, title, body in sections:
        with st.expander(f"{num}) {title}", expanded=(num <= 2)):
            st.markdown(body)

            # Inject the survey right after section 8
            if num == 8:
                st.markdown("---")
                st.subheader("🗳️ Quick Preference Survey")
                q_buccal = st.radio(
                    "Would you consider buccal insulin films (research-stage) if your clinician recommends it?",
                    ["Yes", "Maybe", "No"], index=1, key="q_buccal_key"
                )
                q_alternatives = st.multiselect(
                    "Other delivery options you’d like to learn about:",
                    ["Insulin pump (CSII)", "Patch / patch pump", "Inhaled insulin (where available)",
                     "Oral/tablet formulations (research)", "Needle-free injectors", "None / not sure"],
                    key="q_alt_key"
                )
                q_free = st.text_input("What would make you consider switching? (optional)", key="q_free_key")
                if st.button("💾 Save my preference", key="save_pref_btn"):
                    row = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "diabetes_type": ui["diabetes_type"],
                        "therapy_type": ui["therapy_type"],
                        "injections_per_day": ui["injections_per_day"],
                        "consider_buccal": st.session_state.q_buccal_key,
                        "other_options": ";".join(st.session_state.q_alt_key) if st.session_state.q_alt_key else "",
                        "free_text": st.session_state.q_free_key.strip(),
                    }
                    try:
                        if os.path.exists(RESPONSES_CSV):
                            df_prev = pd.read_csv(RESPONSES_CSV)
                            df_out = pd.concat([df_prev, pd.DataFrame([row])], ignore_index=True)
                        else:
                            df_out = pd.DataFrame([row])
                        df_out.to_csv(RESPONSES_CSV, index=False)
                        st.success(f"Saved ✔️ (added to `{RESPONSES_CSV}`)")
                        st.dataframe(df_out.tail(5), use_container_width=True)
                    except Exception as e:
                        st.error(f"Could not save response: {e}")

# =========================
# Display summary + refs + analytics
# =========================
if st.session_state.summary_ready:
    ui = st.session_state.saved_inputs
    show_clinical_banners(ui)

    st.subheader("📘 Education Summary")
    render_summary_expandable(st.session_state.summary_text, ui)

    st.markdown("### 🔗 References")
    for title, url in REFERENCES:
        st.markdown(f"- [{title}]({url})")

    if os.path.exists(RESPONSES_CSV):
        st.markdown("---")
        st.subheader("📊 Survey Responses Summary")
        try:
            df = pd.read_csv(RESPONSES_CSV)
            if not df.empty:
                counts = df["consider_buccal"].value_counts().reindex(["Yes", "Maybe", "No"]).fillna(0).astype(int)
                st.bar_chart(counts, height=220)
            else:
                st.info("No responses yet. Submit the survey to populate analytics.")
        except Exception as e:
            st.error(f"Could not load analytics: {e}")

st.caption(APP_DISCLAIMER)
