import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from groq import Groq
import io

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Red Bull · Event Engagement System",
    page_icon="🐂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp { background-color: #050505; }
.main { background-color: #050505; }
.block-container { padding-top: 1rem; }

/* Welcome screen */
.welcome-wrap {
    min-height: 90vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}
.welcome-logo {
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    letter-spacing: 6px;
    color: #CC0000;
    font-weight: 700;
    margin-bottom: 12px;
}
.welcome-name {
    font-family: 'Oswald', sans-serif;
    font-size: 72px;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1;
    margin: 0;
}
.welcome-sub {
    font-size: 16px;
    color: #787878;
    margin-top: 12px;
    letter-spacing: 1px;
}
.welcome-divider {
    width: 80px;
    height: 3px;
    background: #CC0000;
    margin: 28px auto;
}

/* Cards */
.metric-card {
    background: #0D0D0D;
    border: 1px solid #1A1A1A;
    border-top: 3px solid #CC0000;
    padding: 20px;
    text-align: center;
}
.metric-big {
    font-family: 'Oswald', sans-serif;
    font-size: 52px;
    font-weight: 700;
    color: #CC0000;
    line-height: 1;
}
.metric-label {
    font-size: 10px;
    color: #787878;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 6px;
}
.metric-sub {
    font-size: 13px;
    color: #C8C8C8;
    margin-top: 4px;
}

/* Driver card */
.driver-row {
    background: #0D0D0D;
    border: 1px solid #1A1A1A;
    border-left: 3px solid #CC0000;
    padding: 12px 16px;
    margin: 6px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.driver-name { color: #FFFFFF; font-size: 13px; font-weight: 500; }
.driver-score {
    font-family: 'Oswald', sans-serif;
    font-size: 22px;
    color: #CC0000;
    font-weight: 700;
}

/* Section headers */
.sec-header {
    font-family: 'Oswald', sans-serif;
    font-size: 11px;
    letter-spacing: 4px;
    color: #CC0000;
    font-weight: 600;
    padding: 10px 0 6px;
    border-bottom: 1px solid #1A1A1A;
    margin: 20px 0 12px;
}

/* Advisory */
.advisory-wrap {
    background: #0D0D0D;
    border: 1px solid #CC0000;
    padding: 28px;
    margin-top: 12px;
    line-height: 1.8;
    color: #C8C8C8;
    font-size: 14px;
}

/* Sidebar */
div[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid #1A1A1A;
}
div[data-testid="stSidebar"] * { color: #C8C8C8 !important; }
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stTextInput label,
div[data-testid="stSidebar"] .stRadio label { color: #787878 !important; font-size: 11px !important; letter-spacing: 1px; }

/* Event selector tabs */
.event-pill {
    display: inline-block;
    padding: 6px 18px;
    background: #1A1A1A;
    border: 1px solid #333;
    color: #787878;
    font-size: 12px;
    cursor: pointer;
    margin-right: 6px;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 1px;
}
.event-pill.active {
    background: #CC0000;
    border-color: #CC0000;
    color: #FFFFFF;
}

/* Hide streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
TEXT_TO_NUM = {
    "Strongly Agree": 7, "Agree": 6, "Slightly Agree": 5,
    "Neutral": 4, "Slightly Disagree": 3, "Disagree": 2, "Strongly Disagree": 1
}

DRIVER_COLORS = {
    "Identity Alignment": "#CC0000",
    "Community Belonging": "#E8A838",
    "Sensory Immersion": "#C8C8C8",
    "Novelty / Surprise": "#787878",
    "Emotional Engagement": "#CC0000",
    "BEI / Advocacy": "#E8A838"
}

# ── RED BULL SAMPLE DATA ──────────────────────────────────────────────────────
RB_EVENTS = {
    "X-Fighters Madrid 2025": {
        "type": "Live Sports Event",
        "desc": "FMX World Tour · Estadio Metropolitano · 45,000 attendees",
        "data": {
            "Q1": [7,7,6,7,7,6,7,7,6,7,7,6,7,7,6,7,7,6,7,7],
            "Q2": [6,6,5,6,7,6,6,6,5,6,7,6,6,5,6,6,7,6,6,6],
            "Q3": [7,7,7,6,7,7,7,6,7,7,7,6,7,7,7,6,7,7,7,7],
            "Q4": [7,7,6,7,7,7,6,7,7,7,6,7,7,7,6,7,7,7,6,7],
            "Q5": [7,6,7,7,7,6,7,7,6,7,7,7,6,7,7,6,7,7,7,6],
            "Q6": [7,6,6,7,7,6,7,6,7,7,6,7,6,7,7,6,7,6,7,7],
        }
    },
    "Music Lab Barcelona 2025": {
        "type": "Cultural / Music Event",
        "desc": "Underground Music Series · Sala Apolo · 800 attendees",
        "data": {
            "Q1": [7,7,6,7,6,7,7,6,7,7,6,7,6,7,7,6,7,7,6,7],
            "Q2": [7,7,7,6,7,7,7,7,6,7,7,7,6,7,7,7,6,7,7,7],
            "Q3": [6,5,6,6,5,6,6,5,6,6,5,6,6,5,6,6,5,6,5,6],
            "Q4": [6,6,5,6,6,6,5,6,6,6,5,6,5,6,6,6,5,6,6,5],
            "Q5": [7,7,6,7,7,7,6,7,7,7,6,7,7,6,7,7,7,6,7,7],
            "Q6": [7,6,7,7,6,7,7,6,7,7,6,7,7,6,7,7,6,7,6,7],
        }
    },
    "Soapbox Race Valencia 2025": {
        "type": "Brand Activation",
        "desc": "DIY Racing · Ciudad de las Artes · 28,000 attendees",
        "data": {
            "Q1": [6,6,5,6,6,5,6,6,5,6,5,6,6,5,6,5,6,6,5,6],
            "Q2": [7,6,7,6,7,6,7,6,7,6,7,6,7,6,7,6,7,6,7,6],
            "Q3": [5,5,4,5,5,4,5,5,4,5,4,5,5,4,5,4,5,5,4,5],
            "Q4": [7,7,7,7,6,7,7,7,7,6,7,7,7,7,6,7,7,7,7,6],
            "Q5": [6,6,5,6,6,5,6,6,5,6,5,6,6,5,6,5,6,6,5,6],
            "Q6": [6,6,6,5,6,6,5,6,6,5,6,6,5,6,6,5,6,6,5,6],
        }
    }
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def calculate_scores_from_dict(data_dict):
    df = pd.DataFrame(data_dict)
    scores = {}
    scores["Identity Alignment"] = df["Q1"]
    scores["Community Belonging"] = df["Q2"]
    scores["Sensory Immersion"] = df["Q3"]
    scores["Novelty / Surprise"] = df["Q4"]
    scores["Emotional Engagement"] = df["Q5"]
    scores["BEI / Advocacy"] = df["Q6"]
    scores_df = pd.DataFrame(scores)
    scores_df["Engagement Score"] = scores_df.mean(axis=1)
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

def detect_columns(df):
    col_map = {}
    keywords = {
        "Q1": ["consistent", "brand stands for", "identity"],
        "Q2": ["sense of belonging", "belonging during"],
        "Q3": ["immersive", "sensory", "atmosphere", "environment"],
        "Q4": ["surprised", "novel", "surprising"],
        "Q5": ["emotionally engaged", "emotional"],
        "Q6": ["recommend", "colleague"],
        "Q7": ["strengthened", "understanding of ai", "relevant to my", "challenged how"],
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

def generate_advisory(api_key, event_name, event_type, driver_means, corrs, ee_bei, eng_score):
    client = Groq(api_key=api_key)
    drivers_text = "\n".join([f"- {k}: {v}/7" for k, v in driver_means.items()])
    corrs_text = "\n".join([f"- {k} → EE: {v}" for k, v in corrs.items()])
    prompt = f"""You are a senior brand strategist specializing in experiential marketing for high-performance brands like Red Bull.

Analyze this event engagement data for a Red Bull event and provide a concise, strategic advisory.

EVENT: {event_name}
TYPE: {event_type}
OVERALL ENGAGEMENT SCORE: {eng_score}/7 ({round(eng_score/7*100,1)}%)

DRIVER SCORES:
{drivers_text}

DRIVER → EMOTIONAL ENGAGEMENT CORRELATIONS:
{corrs_text}

EE → BEI CORRELATION: {ee_bei}

Write a structured advisory with exactly these 4 sections:
1. OVERALL ASSESSMENT — what this score means for a Red Bull event at this scale
2. STRENGTHS — the top 2 drivers and why they matter for Red Bull's brand strategy
3. AREAS FOR IMPROVEMENT — the weakest driver with 2-3 specific, tangible Red Bull-relevant recommendations
4. STRATEGIC INSIGHT — one sharp insight about what the correlation data reveals about how Red Bull converts experience into behavior

Be direct. Reference the actual numbers. Under 280 words. No fluff."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def make_bar_chart(driver_means, eng_score):
    drivers = list(driver_means.keys())
    values = list(driver_means.values())
    colors = ["#CC0000" if v == max(values) else "#333333" for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=drivers, orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.2f}" for v in values],
        textposition='outside',
        textfont=dict(size=11, color="#C8C8C8")
    ))
    fig.add_vline(x=eng_score, line_dash="dot", line_color="#CC0000",
                  annotation_text=f"AVG {eng_score}", annotation_font_color="#CC0000",
                  annotation_position="top right")
    fig.update_layout(
        xaxis=dict(range=[0, 8], title="", gridcolor="#1A1A1A", color="#787878",
                   tickfont=dict(color="#787878", size=10)),
        yaxis=dict(title="", tickfont=dict(color="#C8C8C8", size=11)),
        plot_bgcolor="#0D0D0D", paper_bgcolor="#0D0D0D",
        margin=dict(l=0, r=60, t=10, b=20), height=280,
        font=dict(family="Inter", size=11)
    )
    return fig

def make_corr_chart(corrs):
    fig = go.Figure(go.Bar(
        x=list(corrs.values()), y=list(corrs.keys()), orientation='h',
        marker=dict(
            color=["#CC0000" if v >= 0.7 else "#E8A838" if v >= 0.4 else "#333333" for v in corrs.values()],
            line=dict(width=0)
        ),
        text=[f"{v:.2f}" for v in corrs.values()],
        textposition='outside',
        textfont=dict(size=11, color="#C8C8C8")
    ))
    fig.update_layout(
        xaxis=dict(range=[-0.2, 1.4], title="Pearson r", gridcolor="#1A1A1A",
                   tickfont=dict(color="#787878", size=10), color="#787878"),
        yaxis=dict(title="", tickfont=dict(color="#C8C8C8", size=11)),
        plot_bgcolor="#0D0D0D", paper_bgcolor="#0D0D0D",
        margin=dict(l=0, r=60, t=10, b=20), height=200,
        font=dict(family="Inter", size=11)
    )
    return fig

# ── WELCOME SCREEN ────────────────────────────────────────────────────────────
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False

if not st.session_state.welcomed:
    st.markdown("""
    <div class="welcome-wrap">
        <div class="welcome-logo">RED BULL · EVENT ENGAGEMENT SYSTEM</div>
        <h1 class="welcome-name">BIENVENIDO,<br>LUCAS.</h1>
        <p class="welcome-sub">Trade Marketing Manager · Red Bull España</p>
        <div class="welcome-divider"></div>
        <p style="color:#787878; font-size:13px; letter-spacing:1px;">
            From Experience to Economic Value<br>
            <span style="color:#333; font-size:11px;">IE University · Felipe Machado Restrepo · 2026</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2,1,2])
    with col2:
        if st.button("ENTRAR →", use_container_width=True, type="primary"):
            st.session_state.welcomed = True
            st.rerun()
    st.stop()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 8px;">
        <div style="font-family:'Oswald',sans-serif; font-size:11px; letter-spacing:5px; color:#CC0000; font-weight:700;">RED BULL</div>
        <div style="font-size:13px; color:#C8C8C8; margin-top:2px;">Event Engagement System</div>
        <div style="height:2px; background:#CC0000; margin-top:12px;"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; letter-spacing:2px; color:#787878;'>DATA SOURCE</div>", unsafe_allow_html=True)
    data_source = st.radio("", ["Red Bull Events", "Upload Your Data"], label_visibility="collapsed")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; letter-spacing:2px; color:#787878;'>AI ADVISORY</div>", unsafe_allow_html=True)
    groq_key = st.text_input("", type="password", placeholder="Groq API key · gsk_...", label_visibility="collapsed")
    st.markdown("<div style='font-size:10px; color:#333; margin-top:4px;'>console.groq.com · free</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px; letter-spacing:2px; color:#787878;'>THESIS</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px; color:#555; line-height:1.6;'>From Experience to Economic Value<br>IE University · 2026<br>Supervisor: Rosa M. Reig</div>", unsafe_allow_html=True)

# ── MAIN HEADER ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:flex-end; padding-bottom:16px; border-bottom:1px solid #1A1A1A; margin-bottom:24px;">
    <div>
        <div style="font-family:'Oswald',sans-serif; font-size:10px; letter-spacing:4px; color:#CC0000; font-weight:700;">RED BULL · EVENT ENGAGEMENT SYSTEM</div>
        <div style="font-family:'Oswald',sans-serif; font-size:28px; color:#FFFFFF; font-weight:700; margin-top:4px;">EXPERIENTIAL METRICS DASHBOARD</div>
    </div>
    <div style="text-align:right; font-size:11px; color:#555;">
        4 Drivers · Emotional Engagement · BEI<br>
        Framework: Schmitt · Brakus · Brodie · Pine & Gilmore
    </div>
</div>
""", unsafe_allow_html=True)

# ── DATA LOADING ──────────────────────────────────────────────────────────────
scores_df = None
driver_means = None
corrs = None
ee_bei = None
eng_score = None
eng_pct = None
active_event = None
active_type = None

if data_source == "Red Bull Events":
    st.markdown('<div class="sec-header">SELECT EVENT</div>', unsafe_allow_html=True)
    event_names = list(RB_EVENTS.keys())
    cols_ev = st.columns(len(event_names))
    if "selected_event" not in st.session_state:
        st.session_state.selected_event = event_names[0]

    for i, (col, name) in enumerate(zip(cols_ev, event_names)):
        with col:
            label = name.replace("2025", "").strip()
            if st.button(label, key=f"ev_{i}", use_container_width=True,
                        type="primary" if st.session_state.selected_event == name else "secondary"):
                st.session_state.selected_event = name
                st.rerun()

    ev = RB_EVENTS[st.session_state.selected_event]
    active_event = st.session_state.selected_event
    active_type = ev["type"]
    st.markdown(f"<div style='font-size:12px; color:#555; margin:8px 0 20px;'>{ev['desc']}</div>", unsafe_allow_html=True)
    scores_df = calculate_scores_from_dict(ev["data"])

else:
    st.markdown('<div class="sec-header">UPLOAD EVENT DATA</div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px; color:#555; margin-bottom:12px;'>Upload your Microsoft Forms Excel export. The app detects columns automatically.</div>", unsafe_allow_html=True)

    col_up1, col_up2 = st.columns([3, 1])
    with col_up1:
        uploaded = st.file_uploader("", type=["xlsx", "csv"], label_visibility="collapsed")
    with col_up2:
        active_event = st.text_input("", placeholder="Event name", label_visibility="collapsed",
                                      value="My Event")
        active_type = st.selectbox("", ["Internal / Leadership", "Innovation / AI",
                                        "Client Workshop", "Thought Leadership"],
                                   label_visibility="collapsed")

    if uploaded:
        df_raw = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"✓ {len(df_raw)} responses loaded")

        col_map = detect_columns(df_raw)
        if len(col_map) < 6:
            q_cols = list(df_raw.columns)
            offset = 4 if len(df_raw.columns) > 8 else 0
            for i, q in enumerate(["Q1","Q2","Q3","Q4","Q5","Q6","Q7","Q8"]):
                idx = i + offset
                if idx < len(q_cols) and q not in col_map:
                    col_map[q] = q_cols[idx]

        num_df = convert_text_to_num(df_raw, col_map)

        # Calculate scores with event type weighting
        s = {}
        if active_type == "Innovation / AI" and "Q8" in num_df.columns:
            s["Identity Alignment"] = num_df[["Q1","Q8"]].mean(axis=1, skipna=True)
        else:
            s["Identity Alignment"] = num_df.get("Q1")
        if active_type == "Internal / Leadership" and "Q7" in num_df.columns and "Q8" in num_df.columns:
            s["Community Belonging"] = num_df[["Q2","Q7","Q8"]].mean(axis=1, skipna=True)
        else:
            s["Community Belonging"] = num_df.get("Q2")
        s["Sensory Immersion"] = num_df.get("Q3")
        if active_type == "Thought Leadership" and "Q7" in num_df.columns:
            s["Novelty / Surprise"] = num_df[["Q4","Q7"]].mean(axis=1, skipna=True)
        else:
            s["Novelty / Surprise"] = num_df.get("Q4")
        s["Emotional Engagement"] = num_df.get("Q5")
        if active_type in ["Client Workshop","Thought Leadership"] and "Q8" in num_df.columns:
            s["BEI / Advocacy"] = num_df[["Q6","Q8"]].mean(axis=1, skipna=True)
        else:
            s["BEI / Advocacy"] = num_df.get("Q6")
        scores_df = pd.DataFrame({k: v for k, v in s.items() if v is not None})
        scores_df["Engagement Score"] = scores_df.mean(axis=1, skipna=True)
    else:
        st.info("Upload an Excel file to analyze your event data.")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
if scores_df is not None:
    driver_means = get_driver_means(scores_df)
    corrs, ee_bei = get_correlations(scores_df)
    eng_score = round(scores_df["Engagement Score"].mean(), 2)
    eng_pct = round(eng_score / 7 * 100, 1)
    strongest = max(driver_means, key=driver_means.get)
    weakest = min(driver_means, key=driver_means.get)

    # ── TOP METRICS ───────────────────────────────────────────────────────────
    st.markdown(f'<div class="sec-header">{active_event.upper() if active_event else "RESULTS"} · {len(scores_df)} RESPONSES</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-big">{eng_score}</div><div class="metric-sub">/ 7.00</div><div class="metric-label">Engagement Score</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-big" style="color:#E8A838">{eng_pct}%</div><div class="metric-sub">of maximum</div><div class="metric-label">Performance</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-big" style="font-size:20px; padding-top:8px;">{strongest.split("/")[0].strip()}</div><div class="metric-sub">{driver_means[strongest]}/7</div><div class="metric-label">Strongest Driver</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-big" style="font-size:20px; padding-top:8px; color:#555;">{weakest.split("/")[0].strip()}</div><div class="metric-sub">{driver_means[weakest]}/7</div><div class="metric-label">Needs Attention</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["DRIVER SCORES", "CORRELATIONS", "INDIVIDUAL DATA", "AI ADVISORY"])

    with tab1:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="sec-header">DRIVER SCORES · SCALE 1–7</div>', unsafe_allow_html=True)
            st.plotly_chart(make_bar_chart(driver_means, eng_score), use_container_width=True)
        with c2:
            st.markdown('<div class="sec-header">DRIVER BREAKDOWN</div>', unsafe_allow_html=True)
            for driver, mean in sorted(driver_means.items(), key=lambda x: x[1], reverse=True):
                strength = "STRONG" if mean >= 6.5 else "GOOD" if mean >= 5.5 else "MODERATE" if mean >= 4.5 else "WEAK"
                color = "#CC0000" if mean >= 6.5 else "#E8A838" if mean >= 5.5 else "#555" if mean >= 4.5 else "#333"
                st.markdown(f'''
                <div class="driver-row">
                    <div>
                        <div class="driver-name">{driver}</div>
                        <div style="font-size:10px; color:{color}; letter-spacing:1px; margin-top:2px;">{strength}</div>
                    </div>
                    <div class="driver-score">{mean}</div>
                </div>''', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="sec-header">DRIVER → EMOTIONAL ENGAGEMENT</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; color:#555; margin-bottom:12px;'>Which driver best predicts emotional engagement? Higher = stronger predictor.</div>", unsafe_allow_html=True)
        if corrs:
            st.plotly_chart(make_corr_chart(corrs), use_container_width=True)

        st.markdown('<div class="sec-header">EE → BEI · EMOTIONAL TO BEHAVIORAL</div>', unsafe_allow_html=True)
        if ee_bei is not None:
            strength_text = "STRONG — engagement converts to behavior" if abs(ee_bei) >= 0.7 else \
                           "MODERATE — partial conversion" if abs(ee_bei) >= 0.4 else "WEAK — not converting"
            color = "#CC0000" if abs(ee_bei) >= 0.7 else "#E8A838" if abs(ee_bei) >= 0.4 else "#555"
            col_ee1, col_ee2 = st.columns([1, 3])
            with col_ee1:
                st.markdown(f'<div class="metric-card"><div class="metric-big">{ee_bei}</div><div class="metric-label">Pearson r</div></div>', unsafe_allow_html=True)
            with col_ee2:
                st.markdown(f"""
                <div style="background:#0D0D0D; border:1px solid #1A1A1A; padding:24px; height:100%;">
                    <div style="font-family:'Oswald',sans-serif; font-size:16px; color:{color}; letter-spacing:2px;">{strength_text}</div>
                    <div style="font-size:12px; color:#555; margin-top:12px; line-height:1.6;">
                        A correlation of <strong style="color:#C8C8C8">{ee_bei}</strong> means that attendees who reported 
                        higher emotional engagement also showed stronger behavioral intentions — 
                        they're more likely to recommend, return, and amplify the event.
                    </div>
                </div>""", unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="sec-header">INDIVIDUAL SCORES · {0} RESPONDENTS</div>'.format(len(scores_df)), unsafe_allow_html=True)
        display_df = scores_df.round(2).copy()
        display_df.index = [f"#{i+1}" for i in range(len(display_df))]
        st.dataframe(
            display_df.style.background_gradient(subset=["Engagement Score"], cmap="Reds", vmin=1, vmax=7),
            use_container_width=True
        )

        st.markdown('<div class="sec-header">SCORE DISTRIBUTION</div>', unsafe_allow_html=True)
        fig_dist = px.histogram(scores_df, x="Engagement Score", nbins=7, range_x=[1,7],
                                color_discrete_sequence=["#CC0000"])
        fig_dist.update_layout(
            plot_bgcolor="#0D0D0D", paper_bgcolor="#0D0D0D",
            xaxis=dict(title="Engagement Score (1–7)", gridcolor="#1A1A1A", color="#787878",
                       tickfont=dict(color="#787878")),
            yaxis=dict(title="Count", gridcolor="#1A1A1A", color="#787878",
                       tickfont=dict(color="#787878")),
            margin=dict(t=10, b=40), height=220,
            font=dict(family="Inter", color="#C8C8C8")
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with tab4:
        st.markdown('<div class="sec-header">AI-POWERED STRATEGIC ADVISORY</div>', unsafe_allow_html=True)

        # Rule-based insights always visible
        st.markdown("<div style='font-size:12px; color:#555; margin-bottom:8px;'>QUICK INSIGHTS</div>", unsafe_allow_html=True)
        for driver, mean in driver_means.items():
            if mean >= 6.5:
                st.markdown(f"<div style='font-size:12px; color:#CC0000; padding:4px 0;'>↑ <strong>{driver}</strong> is exceptionally strong ({mean}/7) — protect this in future events</div>", unsafe_allow_html=True)
            elif mean < 5.0:
                st.markdown(f"<div style='font-size:12px; color:#555; padding:4px 0;'>↓ <strong>{driver}</strong> needs attention ({mean}/7)</div>", unsafe_allow_html=True)
        if ee_bei is not None:
            if ee_bei >= 0.7:
                st.markdown(f"<div style='font-size:12px; color:#E8A838; padding:4px 0;'>→ EE→BEI = {ee_bei} — emotional engagement is converting strongly into advocacy</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if not groq_key:
            st.markdown("""
            <div style="background:#0D0D0D; border:1px solid #1A1A1A; padding:20px; text-align:center;">
                <div style="font-family:'Oswald',sans-serif; font-size:13px; color:#333; letter-spacing:2px;">ADD GROQ API KEY TO UNLOCK AI ADVISORY</div>
                <div style="font-size:11px; color:#333; margin-top:8px;">console.groq.com · free · 2 minutes</div>
            </div>""", unsafe_allow_html=True)
        else:
            if st.button("GENERATE STRATEGIC ADVISORY →", type="primary", use_container_width=True):
                with st.spinner("Analyzing event data..."):
                    try:
                        advisory = generate_advisory(
                            groq_key, active_event, active_type,
                            driver_means, corrs, ee_bei, eng_score
                        )
                        st.markdown(f'<div class="advisory-wrap">{advisory.replace(chr(10), "<br>")}</div>',
                                    unsafe_allow_html=True)
                        st.download_button(
                            "DOWNLOAD ADVISORY →",
                            data=advisory,
                            file_name=f"RB_Advisory_{(active_event or 'event').replace(' ','_')}.txt",
                            mime="text/plain"
                        )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:40px; padding-top:16px; border-top:1px solid #1A1A1A; display:flex; justify-content:space-between;">
    <div style="font-size:10px; color:#333;">RED BULL · EVENT ENGAGEMENT SYSTEM · IE UNIVERSITY THESIS 2026</div>
    <div style="font-size:10px; color:#333;">Felipe Machado Restrepo · Supervisor: Rosa María Reig Ramellat</div>
</div>
""", unsafe_allow_html=True)
