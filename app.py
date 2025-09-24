# =========================
# Patient form (updated with meds)
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

    # NEW: medications input
    st.markdown("### 💊 Medications")
    medications = st.text_area(
        "List your current diabetes medications (e.g., 'Metformin oral, Lantus injection, IV insulin')"
    )

    if topics:
        st.write("**Focus areas:** ", "  ".join([f"`{t}`" for t in topics]))

    consent = st.checkbox("I understand this is education only (not medical advice).", value=True)
    submitted = st.button("✨ Generate Education Summary")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Prompt builder (extended)
# =========================
def build_prompt(user_inputs: dict) -> str:
    return f"""
System role: You are a kind, clear diabetes education assistant.
Audience: Adults with diabetes (patients, not clinicians).
Tone: Warm, encouraging, simple language. Avoid medical jargon.

Rules:
- NO dosing suggestions or insulin adjustments.
- Focus on general education and ADA/FDA-aligned safety.
- Always include red flags for when to contact a doctor.
- Mark that buccal insulin films are experimental/research stage.
- Keep output short and scannable (bullets, headings).

User profile:
{user_inputs}

Write a patient-friendly education plan with the following sections:

1) **Disclaimer**
   - Short paragraph reminding this is education only.

2) **Your Current Regimen (Education)**
   - Restate their diabetes type, therapy, injections per day, and any medications in simple terms.

3) **ADA Glycemic Targets**
   - General fasting, post-meal, A1C targets with note these are individualized.

4) **Lifestyle & Self-Care**
   - **Diet, Exercise, Monitoring, Stress/Sleep** (short bullets).

5) **Injection Comfort & Adherence**
   - Simple comfort tips.

6) **Red Flags & Safety**
   - When to contact a doctor.

7) **Medication Education (Based on ADA & FDA)**
   - For each medication they listed, generate a short patient-friendly handout:
     - What it is (drug class, simple explanation)
     - When/how it is generally used (oral/injection/IV, food timing if relevant)
     - Common side effects
     - Safety alerts / red flags (from ADA/FDA patient guidance)
   - If multiple meds, list them separately.

8) **New Delivery Option: Buccal Insulin Films (Research Stage)**
   - Explain briefly in plain language.

9) **Question: Would You Consider This Option?**

10) **References**
   - ADA Standards of Care, ADA Hypoglycemia guidance, CDC Carb Counting basics.

Output must use numbered headings and bullet points for clarity.
"""

# =========================
# Collect inputs for prompt
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
            "medications": medications,  # << NEW
            "timestamp": datetime.utcnow().isoformat()
        }
        with st.spinner("Generating your summary…"):
            summary = call_llm(build_prompt(user_inputs))
        st.session_state.summary_text = summary
        st.session_state.saved_inputs = user_inputs
        st.session_state.summary_ready = bool(summary)
