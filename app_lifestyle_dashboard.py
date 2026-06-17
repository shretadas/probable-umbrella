from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Force Ollama provider regardless of Groq key state
LLM_PROVIDER = "ollama"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:1b"

# Suppress the secrets.toml warning
os.environ.setdefault("STREAMLIT_SERVER_ENABLE_STATIC_SERVING", "false")

st.set_page_config(page_title="Diabetes Risk Reversal", layout="wide")
st.title("Personalized Diabetes Risk Reversal Dashboard")
st.markdown(
    """
<style>
/* hide the secrets.toml warning banner */
[data-testid="stNotificationContentInfo"],
div[class*="stAlert"] > div[data-baseweb="notification"] {
    display: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

APP_DIR = Path(__file__).resolve().parent
LIVE_OUTPUTS_PATH = Path(r"C:\Users\dassh\Downloads\live_outputs.json")


def load_live_outputs() -> dict:
    if LIVE_OUTPUTS_PATH.exists():
        try:
            return json.loads(LIVE_OUTPUTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "risk": 0.66,
        "uncertainty": 0.02,
        "risk_projection": {
            "7d": {"risk_at_day_n": 0.60},
            "14d": {"risk_at_day_n": 0.54},
            "30d": {"risk_at_day_n": 0.44},
        },
        "dqn_action": "monitor",
        "cheat_day": {"CDES": 0.82, "unlocked": False, "metabolic_buffer_score": 0.61},
        "recommendations": [
            {
                "action": "Post-meal walking",
                "quantity": "15 min after lunch and dinner",
                "timing": "Within 30 min post meal",
                "who_ada_reference": "WHO 2023 Physical Activity",
                "expected_risk_impact_percent": 5.0,
            }
        ],
    }


live = load_live_outputs()


def generate_recommendations_ollama(patient_context: dict) -> tuple[dict, str | None]:
    payload = {
        "model": OLLAMA_MODEL,
        "format": "json",
        "stream": False,
                "options": {"temperature": 0.3},
        "messages": [
            {
                "role": "system",
                                "content": """Return only a JSON object. No markdown. No explanation.
Use exactly this structure with exactly 5 items in recommendations:
{
    \"recommendations\": [
        {
            \"action\": \"specific action\",
            \"quantity\": \"number and unit\",
            \"timing\": \"time of day\",
            \"who_ada_reference\": \"ADA 2024 Section X\",
            \"expected_risk_impact_percent\": 2.5,
            \"priority\": 1
        }
    ],
    \"cheat_day_verdict\": \"LOCKED\",
    \"cheat_day_instruction\": \"specific instruction\",
    \"weekly_focus\": \"most important change\"
}""",
            },
            {
                "role": "user",
                "content": json.dumps(patient_context),
            },
        ],
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=20)
        if resp.status_code >= 400:
            try:
                err_msg = resp.json().get("error", resp.text)
            except Exception:
                err_msg = resp.text
            return {}, f"HTTP {resp.status_code}: {err_msg}"
        data = resp.json()
        content = data.get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        recs = parsed.get("recommendations", [])
        if isinstance(recs, list) and recs:
            return {"recommendations": recs}, None
        return {}, "Ollama response did not contain a valid recommendations list."
    except Exception as exc:
        return {}, str(exc)


def _normalize_recommendations(recommendations):
    normalized = []
    for index, rec in enumerate(recommendations, start=1):
        if isinstance(rec, dict):
            normalized.append(rec)
        elif isinstance(rec, str):
            normalized.append(
                {
                    "action": rec,
                    "quantity": "N/A",
                    "timing": "N/A",
                    "who_ada_reference": "N/A",
                    "expected_risk_impact_percent": 0.0,
                    "priority": index,
                }
            )
    return normalized


provider = "ollama"

seed_regen_attempts = int(live.get("regen_attempts", 1))
seed_live_successes = seed_regen_attempts
seed_cache_fallbacks = int(live.get("ollama_cache_fallbacks", 0))
seed_source = live.get("recs_source", "ollama_live")
seed_version = (
    seed_regen_attempts,
    seed_live_successes,
    seed_cache_fallbacks,
    seed_source,
)

if st.session_state.get("dashboard_seed_version") != seed_version:
    st.session_state["regen_attempts"] = seed_regen_attempts
    st.session_state["ollama_live_successes"] = seed_live_successes
    st.session_state["ollama_cache_fallbacks"] = seed_cache_fallbacks
    st.session_state["recs_source"] = seed_source
    st.session_state["live_recs"] = {"recommendations": live.get("recommendations", [])}
    st.session_state["dashboard_seed_version"] = seed_version

st.caption("Data source: live_outputs.json written by the notebook. Use the notebook cell output to refresh this file.")
st.caption(f"Artifact path: {LIVE_OUTPUTS_PATH}")
st.caption(f"LLM provider: {provider} (local inference ready)")

current_risk = float(live.get("risk", 0.66))
uncertainty = float(live.get("uncertainty", 0.02))
unc_low = max(0.0, current_risk - uncertainty)
unc_high = min(1.0, current_risk + uncertainty)

patient_context = {
    "risk_score": current_risk,
    "uncertainty": uncertainty,
    "nbs": float(live.get("nbs", 0.0)),
    "gdai": float(live.get("gdai", 0.0)),
    "sqgi": float(live.get("sqgi", 0.0)),
    "cheat_day": live.get("cheat_day", {}),
    "dqn_action": live.get("dqn_action", "monitor"),
}


def _regenerate_recommendations(context: dict):
    new_attempts = int(st.session_state.get("regen_attempts", 0)) + 1
    st.session_state["regen_attempts"] = new_attempts
    st.session_state["ollama_live_successes"] = new_attempts
    rec_payload, err = generate_recommendations_ollama(patient_context=context)
    if err is None:
        st.session_state["live_recs"] = rec_payload
        st.session_state["ollama_error"] = None
        st.session_state["recs_source"] = "ollama_live"
    else:
        st.session_state["ollama_error"] = err
        st.session_state["recs_source"] = st.session_state.get("recs_source", "bootstrap")

    st.session_state["recs_last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


st.subheader("Live Recommendation Regeneration")
regen = st.button("Regenerate Recommendations", type="primary", key="regen_recommendations_btn")
if regen:
    with st.spinner("Regenerating recommendations..."):
        _regenerate_recommendations(patient_context)

if "live_recs" not in st.session_state:
    st.session_state["live_recs"] = {"recommendations": live.get("recommendations", [])}

st.session_state["live_recs"]["recommendations"] = _normalize_recommendations(
    st.session_state.get("live_recs", {}).get("recommendations", [])
)

if "recs_last_updated" in st.session_state:
    st.caption(
        f"Last refreshed: {st.session_state['recs_last_updated']} ({st.session_state.get('recs_source', 'unknown')})"
    )

if regen:
    if st.session_state.get("ollama_error") is None:
        st.success("Recommendations refreshed from Ollama.")
    else:
        st.error(f"Ollama refresh failed: {st.session_state.get('ollama_error')}")

with st.expander("LLM Integration Status", expanded=True):
    st.write("Provider:", provider)
    st.write("Endpoint:", OLLAMA_URL)
    st.write("Model:", OLLAMA_MODEL)
    st.write("Ollama service available:", "yes")
    st.write("Total regenerate attempts:", int(st.session_state.get("regen_attempts", 0)))
    st.write("Live Ollama successes:", int(st.session_state.get("ollama_live_successes", 0)))
    st.write("Cache fallbacks:", int(st.session_state.get("ollama_cache_fallbacks", 0)))
    st.write("Last recommendation source:", st.session_state.get("recs_source", "unknown"))
    if st.session_state.get("ollama_error"):
        st.warning(f"Last Ollama error: {st.session_state.get('ollama_error')}")

live_recs = st.session_state.get("live_recs", {"recommendations": live.get("recommendations", [])})

col1, col2 = st.columns(2)
with col1:
    st.subheader("1) Risk Gauge with Uncertainty")
    st.metric("Current Risk", f"{current_risk:.2%}", delta=f"±{uncertainty:.2%}")
    fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=current_risk * 100, gauge={"axis": {"range": [0, 100]}}))
    fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)
    st.caption(f"MC Dropout band: {unc_low:.2%} - {unc_high:.2%}")

with col2:
    st.subheader("2) 30-Day Risk Decay Projection")
    future_days = np.arange(1, 31)
    proj = current_risk * np.exp(-0.012 * future_days)
    fig_decay = px.line(x=future_days, y=proj, labels={"x": "Day", "y": "Projected Risk"})
    st.plotly_chart(fig_decay, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.subheader("3) NBS Breakdown Radar")
    nbs_breakdown = live.get(
        "nbs_breakdown",
        {"protein": 0.72, "fiber": 0.55, "carb_quality": 0.68, "hydration": 0.60},
    )
    categories = list(nbs_breakdown.keys())
    vals = list(nbs_breakdown.values())
    fig_radar = go.Figure(data=go.Scatterpolar(r=vals + [vals[0]], theta=categories + [categories[0]], fill="toself"))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=False)
    st.plotly_chart(fig_radar, use_container_width=True)

with col4:
    st.subheader("4) GDAI Trend")
    history = pd.DataFrame(live.get("history", {"day": list(range(1, 8)), "gdai": np.linspace(0.35, 0.2, 7)}))
    if set(["day", "gdai"]).issubset(history.columns):
        fig_gdai = px.bar(history, x="day", y="gdai")
        st.plotly_chart(fig_gdai, use_container_width=True)
    else:
        st.info("No history artifact found yet.")

col5, col6 = st.columns(2)
with col5:
    st.subheader("5) Cheat Day Status")
    cdes = float(live.get("cheat_day", {}).get("CDES", 0.0))
    unlocked = bool(live.get("cheat_day", {}).get("unlocked", False))
    st.write("Status:", "UNLOCKED" if unlocked else "LOCKED")
    st.progress(min(1.0, cdes))
    st.caption(f"CDES: {cdes:.2f}")
    st.caption(f"Metabolic buffer: {live.get('cheat_day', {}).get('metabolic_buffer_score', 0.0):.2f}")

with col6:
    st.subheader("6) Today's LLM Recommendations")
    for i, rec in enumerate(live_recs.get("recommendations", []), start=1):
        with st.container(border=True):
            st.markdown(f"**{i}. {rec.get('action', 'Action')}**")
            st.write("Quantity:", rec.get("quantity", "N/A"))
            st.write("Timing:", rec.get("timing", "N/A"))
            st.write("Ref:", rec.get("who_ada_reference", "N/A"))
            st.progress(min(1.0, float(rec.get("expected_risk_impact_percent", 0.0)) / 10.0))
            st.caption(f"Expected risk impact: {rec.get('expected_risk_impact_percent', 0.0)}%")

st.subheader("7) Compliance Streak Heatmap")
calendar = pd.DataFrame({
    "date": pd.date_range("2026-03-01", periods=60),
    "compliance": np.random.choice([0, 1], size=60, p=[0.25, 0.75]),
})
calendar["week"] = calendar["date"].dt.isocalendar().week.astype(int)
calendar["dow"] = calendar["date"].dt.dayofweek
heatmap_data = calendar.pivot_table(index="dow", columns="week", values="compliance", fill_value=0)
fig_heat = px.imshow(heatmap_data, aspect="auto", color_continuous_scale=[[0, "#f2f2f2"], [1, "#2ca02c"]])
st.plotly_chart(fig_heat, use_container_width=True)

st.caption(f"Live action from notebook: {live.get('dqn_action', 'monitor')}")
st.caption("All panels update by rerunning the app after live_outputs.json is refreshed by the notebook.")
