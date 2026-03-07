import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import anthropic
import io
import json
from datetime import datetime
from supabase import create_client

# ── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Event Engagement System | EY wavespace",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #F0F4F8; }
    .stApp { background-color: #F0F4F8; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 4px solid #00B4D8;
    }
    .score-big { font-size: 48px; font-weight: 800; color: #0D1F3C; }
    .score-label { font-size: 13px; color: #8BA4C0; text-transform: uppercase; letter-spacing: 1px; }
    .driver-card {
        background: white; border-radius: 10px; padding: 15px 20px;
        margin: 6px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .advisory-box {
        background: #0D1F3C; color: white; border-radius: 12px;
        padding: 24px; margin-top: 16px; line-height: 1.7;
    }
    .section-header {
        background: #0D1F3C; color: #00B4D8; padding: 10px 16px;
        border-radius: 8px; font-weight: 700; letter-spacing: 1px;
        font-size: 13px; margin: 20px 0 12px 0;
    }
    div[data-testid="stSidebar"] { background-color: #0D1F3C; }
    div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
TEXT_TO_NUM = {
    "Strongly Agree": 7, "Agree": 6, "Slightly Agree": 5,
    "Neutral": 4, "Slightly Disagree": 3, "Disagree": 2, "Strongly Disagree": 1
}

EVENT_TYPES = ["Internal / Leadership", "Innovation / AI", "Client Workshop", "Thought Leadership"]

DRIVER_COLORS = {
    "Identity Alignment": "#00B4D8",
    "Community Belonging": "#7B61FF",
    "Sensory Immersion": "#00C48C",
    "Novelty / Surprise": "#E8A838",
    "Emotional Engagement": "#1A3A6B",
    "BEI / Advocacy": "#8BA4C0"
}

# ── SUPABASE ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def load_history():
    try:
        sb = get_supabase()
        res = sb.table("event_history").select("*").order("date", desc=False).execute()
        rows = res.data or []
        for r in rows:
            r["driver_means"] = json.loads(r["driver_means"]) if isinstance(r["driver_means"], str) else r["driver_means"]
            r["correlations"] = json.loads(r["correlations"]) if isinstance(r["correlations"], str) else r["correlations"]
        return rows
    except Exception as e:
        st.error(f"Error loading history: {e}")
        return []

def save_to_history(event_name, event_type, eng_score, eng_pct, driver_means, corrs, ee_bei, n_responses):
    try:
        sb = get_supabase()
        today = datetime.now().strftime("%Y-%m-%d")
        # Delete existing entry with same event name + today's date (upsert by name+day)
        sb.table("event_history").delete().eq("event_name", event_name).like("date", f"{today}%").execute()
        entry = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "event_name": event_name,
            "event_type": event_type,
            "engagement_score": eng_score,
            "engagement_pct": eng_pct,
            "n_responses": n_responses,
            "driver_means": json.dumps(driver_means),
            "correlations": json.dumps(corrs),
            "ee_bei": ee_bei,
        }
        sb.table("event_history").insert(entry).execute()
    except Exception as e:
        st.error(f"Error saving: {e}")

def delete_from_history(entry_id):
    try:
        sb = get_supabase()
        sb.table("event_history").delete().eq("id", entry_id).execute()
    except Exception as e:
        st.error(f"Error deleting: {e}")

# ── HELPERS ──────────────────────────────────────────────────────────────────
def detect_columns(df):
    col_map = {}
    keywords = {
        "Q1": ["consistent", "brand stands for", "identity"],
        "Q2": ["sense of belonging", "belonging during"],
        "Q3": ["immersive", "sensory", "atmosphere", "environment"],
        "Q4": ["surprised", "novel", "surprising"],
        "Q5": ["emotionally engaged", "emotional"],
        "Q6": ["recommend", "colleague"],
        "Q7": ["strengthened", "belonging at ey", "understanding of ai", "relevant to my", "challenged how"],
        "Q8": ["connected to my colleagues", "leader in this space", "engage further", "share the insights"]
    }
    for col in df.columns:
        col_lower = col.lower()
        for q, kws in keywords.items():
            if any(kw in col_lower for kw in kws):
                if q not in col_map:
                    col_map[q] = col
    return col_map

def convert_text_to_num(df, col_map):
    numeric = {}
    for q, col in col_map.items():
        if col in df.columns:
            numeric[q] = df[col].map(lambda x: TEXT_TO_NUM.get(str(x).strip(), None))
    return pd.DataFrame(numeric)

def calculate_scores(num_df, event_type):
    scores = {}
    if event_type == "Innovation / AI" and "Q8" in num_df.columns:
        scores["Identity Alignment"] = num_df[["Q1", "Q8"]].mean(axis=1, skipna=True)
    else:
        scores["Identity Alignment"] = num_df.get("Q1")

    if event_type == "Internal / Leadership" and "Q7" in num_df.columns and "Q8" in num_df.columns:
        scores["Community Belonging"] = num_df[["Q2", "Q7", "Q8"]].mean(axis=1, skipna=True)
    else:
        scores["Community Belonging"] = num_df.get("Q2")

    scores["Sensory Immersion"] = num_df.get("Q3")

    if event_type == "Thought Leadership" and "Q7" in num_df.columns:
        scores["Novelty / Surprise"] = num_df[["Q4", "Q7"]].mean(axis=1, skipna=True)
    else:
        scores["Novelty / Surprise"] = num_df.get("Q4")

    scores["Emotional Engagement"] = num_df.get("Q5")

    if event_type in ["Client Workshop", "Thought Leadership"] and "Q8" in num_df.columns:
        scores["BEI / Advocacy"] = num_df[["Q6", "Q8"]].mean(axis=1, skipna=True)
    else:
        scores["BEI / Advocacy"] = num_df.get("Q6")

    scores_df = pd.DataFrame({k: v for k, v in scores.items() if v is not None})
    scores_df["Engagement Score"] = scores_df.mean(axis=1, skipna=True)
    return scores_df

def get_driver_means(scores_df):
    drivers = ["Identity Alignment", "Community Belonging", "Sensory Immersion",
               "Novelty / Surprise", "Emotional Engagement", "BEI / Advocacy"]
    return {d: round(scores_df[d].mean(), 2) for d in drivers if d in scores_df.columns}

def get_correlations(scores_df):
    corrs = {}
    for d in ["Identity Alignment", "Community Belonging", "Sensory Immersion", "Novelty / Surprise"]:
        if d in scores_df.columns and "Emotional Engagement" in scores_df.columns:
            corrs[d] = round(scores_df[d].corr(scores_df["Emotional Engagement"]), 2)
    ee_bei = None
    if "Emotional Engagement" in scores_df.columns and "BEI / Advocacy" in scores_df.columns:
        ee_bei = round(scores_df["Emotional Engagement"].corr(scores_df["BEI / Advocacy"]), 2)
    return corrs, ee_bei

def generate_advisory_claude(api_key, event_name, event_type, driver_means, corrs, ee_bei, eng_score):
    client = anthropic.Anthropic(api_key=api_key)

    drivers_text = "\n".join([f"- {k}: {v}/7" for k, v in driver_means.items()])
    corrs_text = "\n".join([f"- {k} → EE: {v}" for k, v in corrs.items()])

    prompt = f"""You are an expert advisor on experiential marketing and event engagement for corporate events.

Analyze the following event engagement data and provide a concise, actionable advisory report.

EVENT: {event_name}
TYPE: {event_type}
OVERALL ENGAGEMENT SCORE: {eng_score}/7 ({round(eng_score/7*100,1)}%)

DRIVER SCORES (scale 1-7):
{drivers_text}

CORRELATIONS WITH EMOTIONAL ENGAGEMENT:
{corrs_text}

EE → BEI CORRELATION: {ee_bei}

Write a structured advisory with exactly these 4 sections:
1. OVERALL ASSESSMENT (2-3 sentences on what the score means)
2. STRENGTHS (top 2 drivers and what they mean for this specific event type)
3. AREAS FOR IMPROVEMENT (weakest driver with 2-3 specific, tangible recommendations)
4. STRATEGIC INSIGHT (one key insight about what the correlation data reveals)

Be specific, direct, and actionable. Reference the actual numbers. Under 300 words total."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Event Engagement System")
    st.markdown("**EY Wavespace**  |  IE University Thesis")
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    event_name = st.text_input("Event Name", value="Women's Leadership Forum")
    event_type = st.selectbox("Event Type", EVENT_TYPES, index=0)
    st.markdown("---")
    st.markdown("### 🤖 AI Advisory")
    claude_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    st.caption("Get your key at console.anthropic.com")
    st.markdown("---")
    st.markdown("### 📁 Data")
    upload_mode = st.radio("Input mode", ["Upload Excel", "Use sample data"])

# ── MAIN ─────────────────────────────────────────────────────────────────────
st.markdown("# Event Engagement Dashboard")
st.markdown(f"**{event_name}** · {event_type}")
st.markdown("---")

# ── DATA ─────────────────────────────────────────────────────────────────────
df_raw = None

if upload_mode == "Upload Excel":
    uploaded = st.file_uploader("Upload Microsoft Forms Excel export", type=["xlsx", "csv"])
    if uploaded:
        df_raw = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"✓ {len(df_raw)} responses loaded")
else:
    sample = {
        "Q1_text": ["Strongly Agree","Agree","Agree","Slightly Agree","Agree","Agree","Neutral","Agree"],
        "Q2_text": ["Strongly Agree","Agree","Agree","Agree","Agree","Agree","Slightly Agree","Agree"],
        "Q3_text": ["Strongly Agree","Agree","Agree","Slightly Agree","Agree","Agree","Slightly Agree","Agree"],
        "Q4_text": ["Strongly Agree","Strongly Agree","Agree","Agree","Agree","Agree","Slightly Agree","Agree"],
        "Q5_text": ["Strongly Agree","Strongly Agree","Slightly Agree","Agree","Slightly Agree","Agree","Slightly Agree","Agree"],
        "Q6_text": ["Strongly Agree","Agree","Agree","Agree","Agree","Agree","Slightly Agree","Agree"],
        "Q7_text": ["Strongly Agree","Agree","Slightly Agree","Agree","Slightly Agree","Agree","Agree","Agree"],
        "Q8_text": ["Strongly Agree","Strongly Agree","Slightly Agree","Agree","Slightly Agree","Agree","Agree","Agree"],
    }
    df_raw = pd.DataFrame(sample)
    st.info("Using sample data — Women's Leadership Forum (8 responses)")

if df_raw is not None:
    col_map = detect_columns(df_raw)
    if len(col_map) < 6:
        q_cols = list(df_raw.columns)
        offset = 4 if upload_mode == "Upload Excel" else 0
        for i, q in enumerate(["Q1","Q2","Q3","Q4","Q5","Q6","Q7","Q8"]):
            idx = i + offset
            if idx < len(q_cols) and q not in col_map:
                col_map[q] = q_cols[idx]

    num_df = convert_text_to_num(df_raw, col_map)
    scores_df = calculate_scores(num_df, event_type)
    driver_means = get_driver_means(scores_df)
    corrs, ee_bei = get_correlations(scores_df)
    eng_score = round(scores_df["Engagement Score"].mean(), 2)
    eng_pct = round(eng_score / 7 * 100, 1)

    # ── TOP METRICS ───────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="score-label">Engagement Score</div><div class="score-big">{eng_score}</div><div class="score-label">out of 7</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card" style="border-left-color:#00C48C"><div class="score-label">Performance</div><div class="score-big" style="color:#00C48C">{eng_pct}%</div><div class="score-label">of maximum</div></div>', unsafe_allow_html=True)
    with c3:
        strongest = max(driver_means, key=driver_means.get)
        st.markdown(f'<div class="metric-card" style="border-left-color:#E8A838"><div class="score-label">Strongest Driver</div><div style="font-size:18px;font-weight:700;color:#0D1F3C;margin:8px 0">{strongest.split("/")[0]}</div><div class="score-label">{driver_means[strongest]}/7</div></div>', unsafe_allow_html=True)
    with c4:
        weakest = min(driver_means, key=driver_means.get)
        st.markdown(f'<div class="metric-card" style="border-left-color:#FF6B6B"><div class="score-label">Needs Attention</div><div style="font-size:18px;font-weight:700;color:#0D1F3C;margin:8px 0">{weakest.split("/")[0]}</div><div class="score-label">{driver_means[weakest]}/7</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SAVE BUTTON ───────────────────────────────────────────────────────────
    col_save, col_msg = st.columns([1, 4])
    with col_save:
        if st.button("💾 Save Results", type="secondary"):
            save_to_history(event_name, event_type, eng_score, eng_pct,
                            driver_means, corrs, ee_bei, len(scores_df))
            st.session_state["save_msg"] = f"✅ '{event_name}' saved to history."
    with col_msg:
        if st.session_state.get("save_msg"):
            st.success(st.session_state["save_msg"])
            st.session_state["save_msg"] = None

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📊 General Model", "🎯 Specific Model", "🤖 AI Advisory", "📁 History"])

    with tab1:
        st.markdown('<div class="section-header">DRIVER SCORES — 6 CORE QUESTIONS</div>', unsafe_allow_html=True)
        col_l, col_r = st.columns([3, 2])

        with col_l:
            fig = go.Figure(go.Bar(
                x=list(driver_means.values()), y=list(driver_means.keys()), orientation='h',
                marker=dict(color=[DRIVER_COLORS.get(d, "#8BA4C0") for d in driver_means], line=dict(width=0)),
                text=[f"{v:.2f}" for v in driver_means.values()], textposition='outside',
                textfont=dict(size=12, color="#0D1F3C")
            ))
            fig.add_vline(x=eng_score, line_dash="dash", line_color="#0D1F3C",
                          annotation_text=f"Avg: {eng_score}", annotation_position="top right")
            fig.update_layout(
                xaxis=dict(range=[0, 7.8], title="Score (1–7)", gridcolor="#E0E0E0"),
                yaxis=dict(title=""), plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0, r=50, t=20, b=40), height=320,
                font=dict(family="Arial", size=11)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            for driver, mean in driver_means.items():
                strength = "Strong" if mean >= 6 else "Moderate" if mean >= 5 else "Needs attention"
                color = "#00C48C" if mean >= 6 else "#E8A838" if mean >= 5 else "#FF6B6B"
                st.markdown(f'''<div class="driver-card">
                    <div style="font-weight:700;color:#0D1F3C;font-size:13px">{driver}</div>
                    <div style="display:flex;justify-content:space-between;margin-top:4px">
                        <span style="font-size:20px;font-weight:800;color:#0D1F3C">{mean}</span>
                        <span style="color:{color};font-size:12px;font-weight:600">{strength}</span>
                    </div></div>''', unsafe_allow_html=True)

        st.markdown('<div class="section-header">CORRELATIONS</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)

        with cc1:
            st.markdown("**Drivers → Emotional Engagement**")
            if corrs:
                fig_c = go.Figure(go.Bar(
                    x=list(corrs.values()), y=list(corrs.keys()), orientation='h',
                    marker=dict(color=["#00C48C" if v >= 0.7 else "#E8A838" if v >= 0.4 else "#FF6B6B" for v in corrs.values()]),
                    text=[f"{v:.2f}" for v in corrs.values()], textposition='outside'
                ))
                fig_c.update_layout(xaxis=dict(range=[-1, 1.3], title="Pearson r", gridcolor="#E0E0E0"),
                    yaxis=dict(title=""), plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(l=0, r=50, t=10, b=40), height=220, font=dict(family="Arial", size=11))
                st.plotly_chart(fig_c, use_container_width=True)

        with cc2:
            st.markdown("**EE → BEI (Advocacy Intent)**")
            if ee_bei is not None:
                interp = "Strong — engagement converts to behavior" if abs(ee_bei) >= 0.7 else \
                         "Moderate — some conversion" if abs(ee_bei) >= 0.4 else "Weak — not converting"
                color = "#00C48C" if abs(ee_bei) >= 0.7 else "#E8A838" if abs(ee_bei) >= 0.4 else "#FF6B6B"
                st.markdown(f'''<div style="background:white;border-radius:12px;padding:30px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
                    <div style="font-size:48px;font-weight:800;color:{color}">{ee_bei}</div>
                    <div style="font-size:13px;color:#8BA4C0;margin-top:8px">Pearson r</div>
                    <div style="font-size:13px;color:#0D1F3C;margin-top:12px;font-weight:600">{interp}</div>
                </div>''', unsafe_allow_html=True)

    with tab2:
        st.markdown(f'<div class="section-header">SPECIFIC MODEL — {event_type.upper()}</div>', unsafe_allow_html=True)

        weight_info = {
            "Internal / Leadership": {"Community Belonging": "Q2 + Q7 + Q8 averaged (3 questions)", "Note": "Contextual questions reinforce internal belonging"},
            "Innovation / AI": {"Identity Alignment": "Q1 + Q8 averaged (EY as leader)", "Note": "Q8 reinforces brand positioning"},
            "Client Workshop": {"BEI / Advocacy": "Q6 + Q8 averaged (further engagement)", "Note": "Q8 reinforces business relationship intent"},
            "Thought Leadership": {"Novelty / Surprise": "Q4 + Q7 averaged", "BEI / Advocacy": "Q6 + Q8 averaged", "Note": "Both contextual questions integrated"}
        }
        info = weight_info.get(event_type, {})
        note = info.pop("Note", "")
        st.markdown(f"**How contextual questions are weighted for {event_type}:**")
        for driver, formula in info.items():
            st.markdown(f"- **{driver}**: {formula}")
        if note:
            st.caption(f"💡 {note}")

        st.markdown("---")
        st.markdown("**Individual Engagement Scores**")
        display_df = scores_df.copy().round(2)
        display_df.index = [f"Respondent {i+1}" for i in range(len(display_df))]
        st.dataframe(display_df, use_container_width=True)

        st.markdown("**Score Distribution**")
        fig_d = px.histogram(scores_df, x="Engagement Score", nbins=7, range_x=[1,7],
                             color_discrete_sequence=["#00B4D8"])
        fig_d.update_layout(plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(title="Engagement Score (1–7)", gridcolor="#E0E0E0"),
            yaxis=dict(title="Count", gridcolor="#E0E0E0"),
            margin=dict(t=20, b=40), height=250)
        st.plotly_chart(fig_d, use_container_width=True)

    with tab3:
        st.markdown('<div class="section-header">AI-POWERED ADVISORY — Claude</div>', unsafe_allow_html=True)

        if not claude_key:
            st.warning("Enter your Anthropic API key in the sidebar to generate AI advisory.")
            st.markdown("Get your free key at [console.anthropic.com](https://console.anthropic.com)")
        else:
            if st.button("🤖 Generate Advisory with Claude", type="primary"):
                with st.spinner("Claude is analyzing your event data..."):
                    try:
                        advisory = generate_advisory_claude(
                            claude_key, event_name, event_type,
                            driver_means, corrs, ee_bei, eng_score
                        )
                        st.markdown(f'''<div class="advisory-box">{advisory.replace(chr(10), "<br>")}</div>''',
                                    unsafe_allow_html=True)
                        st.download_button("📥 Download Advisory",
                            data=advisory,
                            file_name=f"Advisory_{event_name.replace(' ','_')}.txt",
                            mime="text/plain")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.markdown("---")
        st.markdown("**Quick Insights (rule-based)**")
        for driver, mean in driver_means.items():
            if mean < 5:
                st.markdown(f"⚠️ **{driver}** is below 5.0 — needs attention in future events")
            elif mean >= 6.5:
                st.markdown(f"✅ **{driver}** is exceptionally strong ({mean}/7)")
        if ee_bei is not None:
            if ee_bei >= 0.7:
                st.markdown(f"✅ **EE → BEI = {ee_bei}** — emotional engagement is strongly converting into advocacy")
            elif ee_bei >= 0.4:
                st.markdown(f"🔶 **EE → BEI = {ee_bei}** — moderate conversion, room to improve")
            else:
                st.markdown(f"⚠️ **EE → BEI = {ee_bei}** — engagement not converting into behavior")

    with tab4:
        st.markdown('<div class="section-header">EVENT HISTORY</div>', unsafe_allow_html=True)
        history = load_history()
        if not history:
            st.info("No saved events yet. Analyze an event and click **💾 Save Results** to start building your history.")
        else:
            # ── COMPARISON CHART ──────────────────────────────────────────
            hist_df = pd.DataFrame([{
                "Event": h["event_name"],
                "Date": h["date"][:10],
                "Type": h["event_type"],
                "Score": h["engagement_score"],
                "%": h["engagement_pct"],
                "Responses": h["n_responses"],
                **{k: v for k, v in h["driver_means"].items()}
            } for h in history])

            st.markdown("**Engagement Score Comparison**")
            fig_hist = go.Figure()
            colors_hist = ["#00B4D8", "#7B61FF", "#00C48C", "#E8A838", "#1A3A6B", "#FF6B6B", "#8BA4C0", "#F4A261", "#2A9D8F"]
            for i, row in hist_df.iterrows():
                fig_hist.add_trace(go.Bar(
                    x=[row["Event"]], y=[row["Score"]],
                    name=row["Event"],
                    marker_color=colors_hist[i % len(colors_hist)],
                    text=[f"{row['Score']}<br>({row['%']}%)"],
                    textposition="outside"
                ))
            fig_hist.add_hline(y=7, line_dash="dot", line_color="#8BA4C0", annotation_text="Max (7)")
            fig_hist.update_layout(
                yaxis=dict(range=[0, 8], title="Engagement Score (1–7)", gridcolor="#E0E0E0"),
                xaxis=dict(title=""), plot_bgcolor="white", paper_bgcolor="white",
                showlegend=False, margin=dict(t=30, b=40), height=300,
                font=dict(family="Arial", size=11)
            )
            st.plotly_chart(fig_hist, use_container_width=True)

            # ── DRIVER RADAR COMPARISON ────────────────────────────────────
            drivers_list = ["Identity Alignment", "Community Belonging", "Sensory Immersion",
                            "Novelty / Surprise", "Emotional Engagement", "BEI / Advocacy"]
            available_drivers = [d for d in drivers_list if d in hist_df.columns]
            if len(history) > 1 and available_drivers:
                st.markdown("**Driver Radar — All Events**")
                fig_radar = go.Figure()
                for i, h in enumerate(history):
                    vals = [h["driver_means"].get(d, 0) for d in available_drivers]
                    vals_closed = vals + [vals[0]]
                    cats_closed = available_drivers + [available_drivers[0]]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals_closed, theta=cats_closed,
                        fill='toself', name=h["event_name"],
                        line_color=colors_hist[i % len(colors_hist)], opacity=0.7
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                    showlegend=True, paper_bgcolor="white",
                    margin=dict(t=30, b=30), height=380,
                    font=dict(family="Arial", size=11)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # ── EVENTS TABLE ──────────────────────────────────────────────
            st.markdown("**Saved Events**")
            for h in reversed(history):
                with st.expander(f"**{h['event_name']}** — {h['date'][:10]}  |  Score: {h['engagement_score']}/7  |  {h['event_type']}"):
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown(f"**Responses:** {h['n_responses']}")
                        st.markdown(f"**Performance:** {h['engagement_pct']}%")
                        st.markdown(f"**EE → BEI:** {h['ee_bei']}")
                    with col_d2:
                        for driver, val in h["driver_means"].items():
                            bar = "█" * int(val) + "░" * (7 - int(val))
                            st.markdown(f"`{bar}` {driver}: **{val}**")
                    if st.button("🗑️ Delete", key=f"del_{h['id']}"):
                        delete_from_history(h["id"])
                        st.rerun()

            # ── EXPORT ────────────────────────────────────────────────────
            st.markdown("---")
            export_df = hist_df[["Event", "Date", "Type", "Score", "%", "Responses"] + available_drivers].copy()
            csv = export_df.to_csv(index=False)
            st.download_button("📥 Export History as CSV", data=csv,
                               file_name="event_history.csv", mime="text/csv")

else:
    st.markdown('''<div style="text-align:center;padding:60px;color:#8BA4C0">
        <div style="font-size:48px">📊</div>
        <div style="font-size:20px;margin-top:16px;color:#0D1F3C;font-weight:700">Upload your Microsoft Forms data to begin</div>
        <div style="font-size:14px;margin-top:8px">Or select "Use sample data" in the sidebar</div>
    </div>''', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align:center;color:#8BA4C0;font-size:12px">Event Engagement System · EY Wavespace Pilot · IE University Thesis 2026</div>',
            unsafe_allow_html=True)
