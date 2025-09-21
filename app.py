# app.py — Diabetes Education Assistant (patient-friendly UI + inline survey + ADA targets + analytics)

import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# Page & style
# -----------------------------
st.set_page_config(page_title="Diabetes Education Assistant", page_icon="🩺", layout="centered")
st.markdown("""
<style>
.big-title { font-size: 2.0rem; font-weight: 800; margin-bottom: 0.25rem; }
.subtle { color:#667085; margin-top:0; }
.card { padding: 1rem 1.25rem; border: 1px solid #EAECF0; border-radius: 14px; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.section { margin-top: 1.25rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# API key (from .env only)
# -----------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("❌ No API key found. Create a **.env** file with:\n\n`OPENAI_API_KEY=sk-proj-...`\n\nThen restart.")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------
# Constants & references
# -----------------------------
APP_DISCLAIMER = (
    "⚠️ **Educational only — not medical advice.** "
    "Please don’t change insulin or treatment based on this app. Talk to your clinician."
)
RESPONSES_CSV = "patient_preferences.csv"

ADA_HYPO = "https://diabetes.org/diabetes/medication-management/blood-glucose-testing-and-control/low-blood-glucose-hypoglycemia"
ADA_STANDARDS = "https://diabetesjournals.org/care/issue"
CDC_CARB = "https://www.cdc.gov/diabetes/healthy-eating/carb-counting-manage-blood-sugar.html"

REFERENCES = [
    ("ADA: Hypoglycemia (Low Blood Glucose)", ADA_HYPO),
    ("ADA Standards of Care — Glycemic Targets", ADA_STANDARDS),
    ("CDC: Carb Counting Basics", CDC_CARB),
]

DIABETES_TYPES = ["Type 1", "Type 2", "Other / Not sure"]
THERAPY_TYPES = ["Basal–bolus (MDI)", "Premix", "Pump / CSII", "Non-insulin", "Not sure"]
FASTING_RANGES = ["<70 mg/dL", "70–99", "100–125", "126–180", ">180", "Not sure"]

# -----------------------------
# Session state (persistence)
# -----------------------------
if "summary_ready" not in st.session_state:
    st.session_state.summary_ready = False
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""
if "saved_inputs" not in st.session_state:
    st.session_state.saved_inputs = None

# -----------------------------
# Prompt + LLM
# -----------------------------
def build_prompt(user_inputs: dict) -> str:
    return f"""
System role: You are a diabetes EDUCATION assistant for patients. Use kind, plain language.
Rules:
- NO dosing suggestions or insulin changes.
- Share general ADA-based education and safety concepts only.
- Clearly note buccal insulin films are research-stage.

User profile:
{user_inputs}

Write clear sections with friendly headings (use numbered headings 1) 2) ...):
1) Disclaimer (one short paragraph)
2) Your current regimen — a simple description (educational only)
3) ADA glycemic targets — general info only
4) Low glucose: signs & what to know (education)
5) Everyday tips: food, movement, sleep, monitoring (short bullets)
6) Injection comfort ideas
7) New idea (research stage): Buccal insulin films — short explainer
8) Question: “Would you consider this option?”
9) References (short bullets)
Keep sentences short and supportive. Avoid medical instructions or dosing.
"""

def call_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Follow safety rules. Education only. No dosing advice."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=900,
        )
        return resp.choices[0].message.content
    except Exception as e:
        msg = str(e)
        if "insufficient_quota" in msg or "429" in msg:
            st.error("🔒 Your OpenAI project has no remaining credits. Add billing/credits, then try again.")
            if st.toggle("Use offline demo text (no API)"):
                return "### Education Summary (offline demo)\n\n- **Disclaimer:** Education only — please talk to your clinician.\n- **Targets:** ADA targets are individualized.\n- **New idea:** Buccal insulin films are research-stage.\n- **Question:** Would you consider this option?"
        st.error(f"LLM error: {msg}")
        return ""

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.write("This tool gives **education only** for people living with diabetes.")
    st.caption(APP_DISCLAIMER)

# -----------------------------
# Patient form
# -----------------------------
st.markdown('<div class="big-title">🩺 Diabetes Education Assistant</div>', unsafe_allow_html=True)
st.markdown('<p class="subtle">Friendly explanations. No medical advice.</p>', unsafe_allow_html=True)

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
    topics = st.multiselect(
        "What would you like to learn about?",
        ["Low-glucose safety", "Monitoring basics", "Meal planning", "Exercise basics",
         "Injection comfort tips", "New delivery options (research)"],
        default=["Low-glucose safety", "New delivery options (research)"]
    )
    consent = st.checkbox("I understand this is education only (not medical advice).", value=True)
    submitted = st.button("✨ Generate Education Summary")
    st.markdown('</div>', unsafe_allow_html=True)

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
            result = call_llm(build_prompt(user_inputs))
        st.session_state.summary_text = result
        st.session_state.saved_inputs = user_inputs
        st.session_state.summary_ready = True

# -----------------------------
# Inline survey injection
# -----------------------------
def render_summary_with_inline_survey(text: str, ui: dict):
    injected = False
    lines = text.splitlines()
    for line in lines:
        st.markdown(line)
        low = line.lower()
        if not injected and ("would you consider this option" in low or "would you consider" in low and "option" in low):
            injected = True
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

# -----------------------------
# Summary + targets + analytics
# -----------------------------
if st.session_state.summary_ready:
    ui = st.session_state.saved_inputs

    if ui["fasting_range"] in ["126–180", ">180"]:
        st.error("🔴 Your fasting glucose is often above the usual target range. Contact your clinician.")
    if ui["fasting_range"] == "<70 mg/dL":
        st.error("🔴 Your fasting glucose includes low values (<70 mg/dL). Follow your clinician’s plan and seek care if needed.")
        st.markdown(f"• ADA Hypoglycemia education: [{ADA_HYPO}]({ADA_HYPO})")
    st.info(f"**ADA general targets:** Fasting 80–130 mg/dL • Post-meal <180 mg/dL • A1C <7% (individualized) — [ADA Standards]({ADA_STANDARDS})")

    st.subheader("📘 Education Summary")
    render_summary_with_inline_survey(st.session_state.summary_text, ui)

    st.markdown("### 🔗 References")
    for title, url in REFERENCES:
        st.markdown(f"- [{title}]({url})")

    # Analytics (if CSV exists)
    if os.path.exists(RESPONSES_CSV):
        st.markdown("---")
        st.subheader("📊 Survey Responses Summary")
        try:
            df = pd.read_csv(RESPONSES_CSV)
            if not df.empty:
                counts = df["consider_buccal"].value_counts().reindex(["Yes","Maybe","No"]).fillna(0).astype(int)
                st.bar_chart(counts, height=200)
            else:
                st.info("No responses yet. Submit the survey to populate analytics.")
        except Exception as e:
            st.error(f"Could not load analytics: {e}")

st.caption(APP_DISCLAIMER)
