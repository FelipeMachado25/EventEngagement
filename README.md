# Event Engagement System
**EY wavespace Pilot · IE University Thesis 2026**

A Streamlit app for analyzing event engagement data from Microsoft Forms surveys. Built as part of the thesis *"From Experience to Economic Value: A Framework to Translate Experiential Marketing into Managerial Metrics — The Case of Red Bull"*.

---

## What it does

- Uploads Microsoft Forms Excel exports and converts text responses (Strongly Agree → 7, etc.) automatically
- Calculates 6 driver scores: Identity Alignment, Community Belonging, Sensory Immersion, Novelty, Emotional Engagement, BEI
- Adapts weights based on event type (Internal, Innovation/AI, Client Workshop, Thought Leadership)
- Generates Pearson correlations between drivers and Emotional Engagement, and EE → BEI
- Produces AI-powered advisory using Claude (Anthropic API)

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get your Anthropic API key

Go to [console.anthropic.com](https://console.anthropic.com) → API Keys → Create key.

### 3. Run the app

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

### 4. Enter your API key

Paste your Anthropic API key in the sidebar under **AI Advisory**.

---

## How to use

1. Export your Microsoft Forms responses as Excel (.xlsx)
2. Upload the file in the sidebar
3. Select the event type from the dropdown
4. View driver scores, correlations, and dashboard in the tabs
5. Click **Generate Advisory with Claude** to get AI-powered recommendations

---

## Event Types & Logic

| Event Type | Contextual Weighting |
|---|---|
| Internal / Leadership | CB = avg(Q2, Q7, Q8) |
| Innovation / AI | IA = avg(Q1, Q8) |
| Client Workshop | BEI = avg(Q6, Q8) |
| Thought Leadership | NS = avg(Q4, Q7) · BEI = avg(Q6, Q8) |

---

## Survey Questions (8 questions)

**6 CORE (all events):**
1. This event felt consistent with what EY stands for. *(Identity Alignment)*
2. I felt a sense of belonging during this event. *(Community Belonging)*
3. The event environment felt immersive — space, energy, atmosphere. *(Sensory Immersion)*
4. This event included elements that genuinely surprised me. *(Novelty)*
5. I felt emotionally engaged during this event. *(Emotional Engagement)*
6. I would recommend this type of event to a colleague. *(BEI)*

**2 CONTEXTUAL (by event type):**
- Q7 and Q8 adapt based on the event type selected

Scale: 1 (Strongly Disagree) → 7 (Strongly Agree)

---

## Deployment (Streamlit Cloud)

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and select `app.py`
4. Add your Anthropic API key as a secret: `ANTHROPIC_API_KEY`
5. Deploy — you get a public URL in minutes

---

## Project Structure

```
EventEngagement/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Tech Stack

- **Streamlit** — web interface
- **Pandas** — data processing
- **Plotly** — interactive charts
- **Anthropic SDK** — Claude AI advisory
- **OpenPyXL** — Excel file handling

---

## Academic Context

This tool is the quantitative pilot component (Stage 2) of a mixed-methods thesis exploring how experiential marketing drivers translate into measurable engagement metrics for managerial decision-making.

**Framework:** 4 drivers (IA, CB, SI, NS) → Emotional Engagement → Behavioral Engagement Intentions → Engagement Score

**Supervisor:** Rosa Maria Reig Ramellat · IE University · 2026
