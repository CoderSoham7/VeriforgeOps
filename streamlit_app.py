"""
VeriForgeOps — Pub/Sub Integration Demo
Glassmorphic Streamlit UI
"""

import streamlit as st
import json
import time
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VeriForgeOps · Pub/Sub Demo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Glassmorphic CSS ──────────────────────────────────────────────────────────
GLASS_CSS = """
<style>
/* ── Base & Background ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2e 30%, #0a1628 60%, #071020 100%);
    min-height: 100vh;
}

/* Animated background orbs */
.stApp::before {
    content: '';
    position: fixed;
    top: -20%;
    left: -10%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%);
    border-radius: 50%;
    animation: float1 12s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

.stApp::after {
    content: '';
    position: fixed;
    bottom: -10%;
    right: -5%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(120,0,255,0.08) 0%, transparent 70%);
    border-radius: 50%;
    animation: float2 15s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}

@keyframes float1 {
    0%, 100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(40px, 30px) scale(1.1); }
}
@keyframes float2 {
    0%, 100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(-30px, -40px) scale(1.05); }
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(10, 14, 26, 0.85) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(0, 212, 255, 0.15);
}

[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #00d4ff !important;
}

/* ── Glass card ─────────────────────────────────────────────────────────── */
.glass-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08);
    position: relative;
    overflow: hidden;
}

.glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,0.5), transparent);
}

/* ── Hero header ─────────────────────────────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, rgba(0,212,255,0.08) 0%, rgba(120,0,255,0.08) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 20px;
    padding: 32px 40px;
    margin-bottom: 28px;
    text-align: center;
    box-shadow: 0 0 60px rgba(0,212,255,0.06), 0 8px 32px rgba(0,0,0,0.4);
}

.hero-title {
    font-size: 2.6rem;
    font-weight: 700;
    background: linear-gradient(135deg, #00d4ff, #7b2fff, #00d4ff);
    background-size: 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 4s linear infinite;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}

@keyframes shimmer {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}

.hero-subtitle {
    color: rgba(200,220,255,0.65);
    font-size: 1rem;
    font-weight: 400;
    margin: 0;
    letter-spacing: 0.3px;
}

/* ── Metric cards ───────────────────────────────────────────────────────── */
.metric-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.metric-card:hover {
    border-color: rgba(0,212,255,0.35);
    box-shadow: 0 8px 32px rgba(0,212,255,0.08);
    transform: translateY(-2px);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #00d4ff;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.2;
}

.metric-label {
    font-size: 0.75rem;
    color: rgba(180,200,240,0.6);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

.metric-delta {
    font-size: 0.8rem;
    color: #00ff9d;
    margin-top: 2px;
}

/* ── Status badge ───────────────────────────────────────────────────────── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

.badge-live {
    background: rgba(0,255,100,0.12);
    border: 1px solid rgba(0,255,100,0.3);
    color: #00ff9d;
}

.badge-mock {
    background: rgba(255,180,0,0.12);
    border: 1px solid rgba(255,180,0,0.3);
    color: #ffb400;
}

.badge-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.7); }
}

/* ── Event stream ───────────────────────────────────────────────────────── */
.event-row {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
}

.event-row:hover {
    background: rgba(0,212,255,0.05);
    border-color: rgba(0,212,255,0.2);
    border-left-color: #00d4ff;
}

.event-row.gcp { border-left-color: #4285f4; }
.event-row.azure { border-left-color: #00bcf2; }
.event-row.aws { border-left-color: #ff9900; }
.event-row.sanas { border-left-color: #a855f7; }
.event-row.aitools { border-left-color: #00d4ff; }

/* ── Flow diagram ───────────────────────────────────────────────────────── */
.flow-step {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
    font-size: 0.82rem;
    color: rgba(200,220,255,0.85);
}

.flow-step.active {
    border-color: rgba(0,212,255,0.4);
    background: rgba(0,212,255,0.06);
    box-shadow: 0 0 20px rgba(0,212,255,0.12);
}

.flow-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(0,212,255,0.5);
    font-size: 1.4rem;
}

/* ── Cloud provider chip ────────────────────────────────────────────────── */
.cloud-chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.chip-gcp { background: rgba(66,133,244,0.2); color: #4285f4; border: 1px solid rgba(66,133,244,0.3); }
.chip-azure { background: rgba(0,188,242,0.2); color: #00bcf2; border: 1px solid rgba(0,188,242,0.3); }
.chip-aws { background: rgba(255,153,0,0.2); color: #ff9900; border: 1px solid rgba(255,153,0,0.3); }
.chip-sanas { background: rgba(168,85,247,0.2); color: #a855f7; border: 1px solid rgba(168,85,247,0.3); }
.chip-ai { background: rgba(0,212,255,0.2); color: #00d4ff; border: 1px solid rgba(0,212,255,0.3); }

/* ── Section title ──────────────────────────────────────────────────────── */
.section-title {
    font-size: 1rem;
    font-weight: 600;
    color: rgba(200,220,255,0.9);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(0,212,255,0.3), transparent);
}

/* ── Streamlit overrides ─────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(120,0,255,0.15)) !important;
    border: 1px solid rgba(0,212,255,0.35) !important;
    color: #00d4ff !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    backdrop-filter: blur(8px) !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,212,255,0.25), rgba(120,0,255,0.25)) !important;
    border-color: rgba(0,212,255,0.6) !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.2) !important;
    transform: translateY(-1px) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

div[data-testid="stSelectbox"] > div,
div[data-testid="stNumberInput"] > div input,
div[data-testid="stTextInput"] > div input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
    color: rgba(200,220,255,0.9) !important;
}

.stSlider > div {
    color: rgba(200,220,255,0.9);
}

div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}

/* Plotly chart backgrounds */
.js-plotly-plot .plotly .bg { fill: transparent !important; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: rgba(180,200,240,0.6) !important;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,212,255,0.12) !important;
    color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff !important;
}

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.2); border-radius: 3px; }

/* Labels */
label, .stMarkdown p, .stMarkdown li { color: rgba(180,200,240,0.8) !important; }
h1, h2, h3 { color: rgba(220,235,255,0.95) !important; }

/* Alert / info boxes */
.stAlert { background: rgba(0,212,255,0.06) !important; border: 1px solid rgba(0,212,255,0.2) !important; border-radius: 10px !important; }
</style>
"""

st.markdown(GLASS_CSS, unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "published_events" not in st.session_state:
    st.session_state.published_events = []
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 0
if "pubsub_mode" not in st.session_state:
    st.session_state.pubsub_mode = "mock"

# ── Mock data generators ──────────────────────────────────────────────────────
PROVIDER_META = {
    "GCP": {
        "services": ["Vertex AI", "Cloud Speech-to-Text", "Cloud Translation", "Vertex AI Embeddings"],
        "regions": ["us-central1", "asia-northeast1", "europe-west3", "us-east4"],
        "models": [
            ("gemini-1.5-pro", "002", "LLM"),
            ("gemini-1.5-flash", "001", "LLM"),
            ("gemini-2.0-flash", "exp", "Multimodal"),
            ("speech-to-text", "stable", "Speech"),
            ("textembedding-gecko", "003", "Embedding"),
        ],
        "operations": ["completion", "transcribe", "translate", "embedding"],
        "account": "cog01k24f1ea555zdv7ynzthxanz5",
    },
    "Azure": {
        "services": ["Azure OpenAI", "Azure Cognitive Services", "Azure Translator"],
        "regions": ["eastus", "westeurope", "southeastasia", "australiaeast"],
        "models": [
            ("gpt-4o", "2024-05", "LLM"),
            ("gpt-4", "turbo", "LLM"),
            ("text-embedding-ada-002", "v2", "Embedding"),
        ],
        "operations": ["chat", "completion", "embedding", "translate"],
        "account": "sub-cog-azure-0042",
    },
    "AWS": {
        "services": ["AWS Bedrock", "Amazon Transcribe", "Amazon Translate"],
        "regions": ["us-east-1", "ap-southeast-1", "eu-west-1"],
        "models": [
            ("anthropic.claude-3-sonnet", "20240229", "LLM"),
            ("amazon.nova-pro", "v1", "Multimodal"),
            ("amazon.titan-embed", "v2", "Embedding"),
        ],
        "operations": ["InvokeModel", "transcribe", "translate"],
        "account": "aws-cog-012345678",
    },
    "Sanas": {
        "services": ["Sanas Voice AI"],
        "regions": ["us-west-2", "eu-central-1"],
        "models": [("sanas-clarity", "v3", "Speech")],
        "operations": ["speech_clarification"],
        "account": "sanas-cog-enterprise",
    },
    "AI Tools": {
        "services": ["Claude Code", "GitHub Copilot", "Tabnine", "Cursor AI"],
        "regions": ["global"],
        "models": [
            ("claude-code", "4.6", "LLM"),
            ("copilot-gpt4", "turbo", "LLM"),
        ],
        "operations": ["code_generation", "code_completion", "explain_code"],
        "account": "ai-tools-cog-global",
    },
}

ASSOCIATES = [
    "soham.ganguly", "priya.sharma", "john.doe", "clara.oswald",
    "ravi.kumar", "mei.chen", "alex.johnson", "fatima.al-rashid",
]
COST_CENTRES = [
    "CC-AI-RESEARCH", "CC-BFSI-PRODUCTS", "CC-HEALTHCARE-DEV",
    "CC-OPERATIONS", "CC-DATA-ENGINEERING", "CC-CLOUD-PLATFORM",
]
PROJECTS = [
    "PROJ-VERIFORGE-OPS", "PROJ-UNDERWRITING-BOT", "PROJ-CLINICAL-TRANSCRIPT",
    "PROJ-CHATBOT-PLATFORM", "PROJ-FRAUD-DETECTION", "PROJ-CUSTOMER-360",
]

PROVIDER_COLORS = {
    "GCP": "#4285f4",
    "Azure": "#00bcf2",
    "AWS": "#ff9900",
    "Sanas": "#a855f7",
    "AI Tools": "#00d4ff",
}


def _rand_request_units(service: str, operation: str) -> Dict[str, Any]:
    if operation in ("transcribe", "speech_clarification"):
        return {
            "input_audio_seconds": round(random.uniform(10, 300), 1),
            "output_characters": random.randint(100, 2000),
        }
    if operation == "translate":
        return {"input_characters": random.randint(500, 50000)}
    if operation == "embedding":
        return {
            "input_tokens": random.randint(100, 8000),
            "output_tokens": 0,
            "total_tokens": random.randint(100, 8000),
        }
    inp = random.randint(500, 500_000)
    out = random.randint(100, 8000)
    cached = random.randint(0, inp // 2) if random.random() > 0.5 else 0
    ru = {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}
    if cached:
        ru["cached_tokens"] = cached
    if random.random() > 0.7:
        ru["input_images"] = random.randint(1, 8)
    if random.random() > 0.8:
        ru["input_audio_seconds"] = round(random.uniform(1, 60), 1)
    return ru


def _approx_cost(provider: str, operation: str, request_units: Dict) -> float:
    if "input_audio_seconds" in request_units and operation in ("transcribe", "speech_clarification"):
        return round(request_units["input_audio_seconds"] * 0.0004, 6)
    if "input_characters" in request_units:
        return round(request_units["input_characters"] * 0.00002 / 1000, 6)
    inp = request_units.get("input_tokens", 0)
    out = request_units.get("output_tokens", 0)
    cached = request_units.get("cached_tokens", 0)
    rate_map = {"GCP": (1.25, 5.0, 0.31), "Azure": (10.0, 30.0, 0), "AWS": (3.0, 15.0, 0),
                "Sanas": (0, 0, 0), "AI Tools": (8.0, 24.0, 0)}
    ri, ro, rc = rate_map.get(provider, (5.0, 15.0, 0))
    cost = ((inp - cached) * ri + out * ro + cached * rc) / 1_000_000
    images = request_units.get("input_images", 0)
    cost += images * 0.0025
    audio = request_units.get("input_audio_seconds", 0)
    cost += audio * 0.000125
    return max(0.000001, round(cost, 6))


def generate_mock_event(provider: str = None) -> Dict[str, Any]:
    if provider is None:
        provider = random.choice(list(PROVIDER_META.keys()))
    meta = PROVIDER_META[provider]
    service = random.choice(meta["services"])
    region = random.choice(meta["regions"])
    model_name, model_ver, model_type = random.choice(meta["models"])
    operation = random.choice(meta["operations"])
    associate = random.choice(ASSOCIATES)
    cc = random.choice(COST_CENTRES)
    proj = random.choice(PROJECTS)
    ru = _rand_request_units(service, operation)
    cost = _approx_cost(provider, operation, ru)

    st.session_state.msg_counter += 1
    msg_id = f"mock-msg-{st.session_state.msg_counter:04d}"

    return {
        "message_id": msg_id,
        "data": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "cloud": provider,
            "service": service,
            "region": region,
            "account_id": meta["account"],
            "resource_id": f"endpoint-{model_name}-deployment",
            "operation": operation,
            "associate_id": associate,
            "cost_centre": cc,
            "project_code": proj,
            "request_units": ru,
            "cost": cost,
            "model_version": model_ver,
            "model_type": model_type,
            "latency_ms": random.randint(200, 8000),
        },
    }


def _cloud_chip(cloud: str) -> str:
    c_map = {"GCP": "gcp", "Azure": "azure", "AWS": "aws", "Sanas": "sanas"}
    cls = c_map.get(cloud, "ai")
    return f'<span class="cloud-chip chip-{cls}">{cloud}</span>'


def _fmt_cost(cost: float) -> str:
    if cost < 0.001:
        return f"${cost:.6f}"
    return f"${cost:.4f}"


# ── Plotly theme helper ───────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="rgba(180,200,240,0.8)", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    colorway=list(PROVIDER_COLORS.values()),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SIDEBAR                                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 20px;">
        <div style="font-size:2.2rem; line-height:1;">⚡</div>
        <div style="font-size:1.1rem; font-weight:700; color:#00d4ff; letter-spacing:0.5px;">VeriForgeOps</div>
        <div style="font-size:0.7rem; color:rgba(180,200,240,0.5); margin-top:2px;">Pub/Sub Integration Demo</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### ⚙️ Publisher Settings")
    pubsub_mode = st.selectbox(
        "Mode",
        options=["Mock (Local JSONL)", "Simulated Live"],
        index=0,
        help="Mock mode writes to JSONL; Simulated Live streams to the UI in real time.",
    )
    st.session_state.pubsub_mode = "mock" if "Mock" in pubsub_mode else "live"

    st.markdown("### 📡 Publish Events")
    publish_provider = st.selectbox(
        "Cloud Provider",
        options=["Random"] + list(PROVIDER_META.keys()),
    )
    publish_count = st.slider("Batch Size", min_value=1, max_value=20, value=5)

    col_a, col_b = st.columns(2)
    with col_a:
        do_publish = st.button("▶ Publish", use_container_width=True)
    with col_b:
        do_clear = st.button("⟳ Reset", use_container_width=True)

    if do_clear:
        st.session_state.published_events = []
        st.session_state.total_cost = 0.0
        st.session_state.msg_counter = 0
        st.rerun()

    if do_publish:
        provider_arg = None if publish_provider == "Random" else publish_provider
        new_events = [generate_mock_event(provider_arg) for _ in range(publish_count)]
        st.session_state.published_events = new_events + st.session_state.published_events
        st.session_state.total_cost = sum(e["data"]["cost"] for e in st.session_state.published_events)
        st.rerun()

    st.divider()

    # Connection info card
    mode_badge = (
        '<span class="status-badge badge-mock"><span class="badge-dot"></span>MOCK</span>'
        if st.session_state.pubsub_mode == "mock"
        else '<span class="status-badge badge-live"><span class="badge-dot"></span>LIVE</span>'
    )
    st.markdown(f"""
    <div class="glass-card" style="padding:14px 16px;">
        <div style="font-size:0.7rem; color:rgba(180,200,240,0.5); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Connection</div>
        <div style="margin-bottom:6px;">{mode_badge}</div>
        <div style="font-size:0.72rem; color:rgba(180,200,240,0.7); margin-top:8px;">
            <div>📦 Topic: <code style="color:#00d4ff;">veriforgeops-telemetry-ingest</code></div>
            <div style="margin-top:4px;">🗂 Project: <code style="color:#00d4ff;">cog01k24...</code></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load sample data button
    if st.button("📂 Load Sample JSONL", use_container_width=True):
        jsonl_path = os.path.join(os.path.dirname(__file__), "mock_telemetry_pubsub.jsonl")
        if os.path.exists(jsonl_path):
            loaded = []
            with open(jsonl_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            loaded.append(json.loads(line))
                        except Exception:
                            pass
            if loaded:
                st.session_state.published_events = loaded + st.session_state.published_events
                st.session_state.total_cost = sum(e["data"]["cost"] for e in st.session_state.published_events)
                st.session_state.msg_counter = max(st.session_state.msg_counter, len(loaded))
                st.rerun()
            else:
                st.warning("JSONL file is empty.")
        else:
            st.warning("mock_telemetry_pubsub.jsonl not found.")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  MAIN CONTENT                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div class="hero-title">⚡ VeriForgeOps · Pub/Sub Integration</div>
    <div class="hero-subtitle">
        Multi-cloud telemetry normalization &amp; real-time FinOps ingestion pipeline
        &nbsp;·&nbsp; GCP · Azure · AWS · Sanas · AI Tools
    </div>
</div>
""", unsafe_allow_html=True)

events = st.session_state.published_events
n_events = len(events)
total_cost = st.session_state.total_cost
providers_seen = set(e["data"]["cloud"] for e in events) if events else set()
total_tokens = sum(
    e["data"]["request_units"].get("total_tokens", 0) +
    e["data"]["request_units"].get("input_tokens", 0)
    for e in events
) if events else 0
avg_latency = (
    sum(e["data"].get("latency_ms", 0) for e in events if e["data"].get("latency_ms")) /
    max(1, sum(1 for e in events if e["data"].get("latency_ms")))
) if events else 0

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
kpi_data = [
    (k1, str(n_events), "Messages Published", ""),
    (k2, f"${total_cost:.4f}", "Total Cost (USD)", ""),
    (k3, f"{total_tokens:,}", "Total Tokens", ""),
    (k4, f"{avg_latency:.0f} ms", "Avg Latency", ""),
    (k5, str(len(providers_seen)), "Cloud Providers", ""),
]
for col, val, label, delta in kpi_data:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
            {f'<div class="metric-delta">{delta}</div>' if delta else ''}
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Architecture Flow ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🔄 Pub/Sub Pipeline Architecture</div>', unsafe_allow_html=True)
flow_cols = st.columns([2, 0.6, 2, 0.6, 2, 0.6, 2, 0.6, 2])
flow_steps = [
    ("☁️", "Cloud Providers", "GCP · Azure · AWS\nSanas · AI Tools"),
    ("→", "", ""),
    ("🔌", "Connectors", "Normalize to\nCanonicalUsageEvent"),
    ("→", "", ""),
    ("📤", "PubSub Publisher", "google-cloud-pubsub\nAsync + Callbacks"),
    ("→", "", ""),
    ("📨", "Topic Ingestion", "veriforgeops-\ntelemetry-ingest"),
    ("→", "", ""),
    ("📊", "FinOps Aggregator", "Cost Attribution\n& Analytics"),
]
for i, (col, (icon, title, subtitle)) in enumerate(zip(flow_cols, flow_steps)):
    with col:
        if icon == "→":
            st.markdown('<div class="flow-arrow">→</div>', unsafe_allow_html=True)
        else:
            active_cls = "active" if n_events > 0 and i < len(flow_steps) else ""
            st.markdown(f"""
            <div class="flow-step {active_cls}">
                <div style="font-size:1.4rem; margin-bottom:4px;">{icon}</div>
                <div style="font-weight:600; color:rgba(220,235,255,0.9); font-size:0.8rem;">{title}</div>
                <div style="font-size:0.68rem; color:rgba(150,170,210,0.6); margin-top:4px; white-space:pre-line;">{subtitle}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_stream, tab_analytics, tab_schema, tab_docs = st.tabs([
    "📡 Event Stream", "📊 Analytics", "📋 Schema Inspector", "📖 Integration Guide"
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — EVENT STREAM
# ════════════════════════════════════════════════════════════════════
with tab_stream:
    if not events:
        st.markdown("""
        <div class="glass-card" style="text-align:center; padding:48px 24px;">
            <div style="font-size:3rem; margin-bottom:12px;">📭</div>
            <div style="font-size:1.1rem; color:rgba(200,220,255,0.7); font-weight:500;">No events yet</div>
            <div style="font-size:0.85rem; color:rgba(150,170,210,0.5); margin-top:8px;">
                Use the sidebar to publish events or load the sample JSONL file.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Filter bar
        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 2])
        with filter_col1:
            filter_cloud = st.multiselect("Filter by Cloud", options=list(PROVIDER_META.keys()), default=[])
        with filter_col2:
            filter_op = st.multiselect("Filter by Operation", options=list({e["data"]["operation"] for e in events}), default=[])
        with filter_col3:
            filter_assoc = st.multiselect("Filter by Associate", options=list({e["data"]["associate_id"] for e in events}), default=[])

        filtered = events
        if filter_cloud:
            filtered = [e for e in filtered if e["data"]["cloud"] in filter_cloud]
        if filter_op:
            filtered = [e for e in filtered if e["data"]["operation"] in filter_op]
        if filter_assoc:
            filtered = [e for e in filtered if e["data"]["associate_id"] in filter_assoc]

        st.markdown(f'<div style="font-size:0.78rem; color:rgba(150,170,210,0.5); margin:8px 0 12px;">Showing {len(filtered)} of {n_events} events</div>', unsafe_allow_html=True)

        for ev in filtered[:50]:
            d = ev["data"]
            cloud = d["cloud"]
            cls_map = {"GCP": "gcp", "Azure": "azure", "AWS": "aws", "Sanas": "sanas"}
            row_cls = cls_map.get(cloud, "aitools")
            ru = d.get("request_units", {})
            tokens_str = f"{ru.get('total_tokens', ru.get('input_tokens', 0)):,} tok" if "input_tokens" in ru or "total_tokens" in ru else ""
            audio_str = f"{ru.get('input_audio_seconds', 0):.1f}s audio" if "input_audio_seconds" in ru else ""
            chars_str = f"{ru.get('input_characters', 0):,} chars" if "input_characters" in ru else ""
            usage_str = " · ".join(filter(None, [tokens_str, audio_str, chars_str])) or "—"
            cached_str = f"💾 {ru.get('cached_tokens', 0):,} cached" if ru.get("cached_tokens") else ""

            st.markdown(f"""
            <div class="event-row {row_cls}">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    {_cloud_chip(cloud)}
                    <span style="color:rgba(220,235,255,0.9); font-weight:500;">{d['service']}</span>
                    <span style="color:rgba(150,170,210,0.5);">·</span>
                    <span style="color:rgba(180,200,240,0.7);">{d['operation']}</span>
                    <span style="color:rgba(150,170,210,0.5);">·</span>
                    <span style="color:rgba(200,220,255,0.6); font-size:0.72rem;">{d.get('model_type','—')} / v{d.get('model_version','?')}</span>
                    <span style="margin-left:auto; color:#00d4ff; font-weight:600;">{_fmt_cost(d['cost'])}</span>
                </div>
                <div style="display:flex; gap:16px; margin-top:6px; font-size:0.72rem; color:rgba(150,170,210,0.6);">
                    <span>👤 {d['associate_id']}</span>
                    <span>🏷 {d['cost_centre']}</span>
                    <span>📁 {d['project_code']}</span>
                    <span>🌍 {d['region']}</span>
                    <span>⏱ {d.get('latency_ms','—')} ms</span>
                    <span>📊 {usage_str}</span>
                    {f'<span style="color:#00ff9d;">{cached_str}</span>' if cached_str else ''}
                    <span style="margin-left:auto; color:rgba(120,140,180,0.4);">{ev['message_id']} · {d['timestamp']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if len(filtered) > 50:
            st.info(f"Showing first 50 of {len(filtered)} events. Use filters to narrow down.")


# ════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYTICS
# ════════════════════════════════════════════════════════════════════
with tab_analytics:
    if not events:
        st.markdown("""
        <div class="glass-card" style="text-align:center; padding:48px 24px;">
            <div style="font-size:3rem; margin-bottom:12px;">📊</div>
            <div style="font-size:1.1rem; color:rgba(200,220,255,0.7);">No data to analyze yet</div>
            <div style="font-size:0.85rem; color:rgba(150,170,210,0.5); margin-top:8px;">Publish some events first.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        df = pd.DataFrame([
            {
                "message_id": e["message_id"],
                "timestamp": e["data"]["timestamp"],
                "cloud": e["data"]["cloud"],
                "service": e["data"]["service"],
                "region": e["data"]["region"],
                "operation": e["data"]["operation"],
                "associate_id": e["data"]["associate_id"],
                "cost_centre": e["data"]["cost_centre"],
                "project_code": e["data"]["project_code"],
                "cost": e["data"]["cost"],
                "model_type": e["data"].get("model_type", "Unknown"),
                "latency_ms": e["data"].get("latency_ms", 0),
                "input_tokens": e["data"]["request_units"].get("input_tokens", 0),
                "output_tokens": e["data"]["request_units"].get("output_tokens", 0),
                "cached_tokens": e["data"]["request_units"].get("cached_tokens", 0),
                "input_audio_seconds": e["data"]["request_units"].get("input_audio_seconds", 0),
            }
            for e in events
        ])

        row1_c1, row1_c2 = st.columns(2)

        # Cost by Cloud Provider
        with row1_c1:
            st.markdown('<div class="section-title">💰 Cost by Cloud Provider</div>', unsafe_allow_html=True)
            cost_by_cloud = df.groupby("cloud")["cost"].sum().reset_index()
            fig1 = go.Figure(go.Pie(
                labels=cost_by_cloud["cloud"],
                values=cost_by_cloud["cost"],
                hole=0.55,
                marker=dict(
                    colors=[PROVIDER_COLORS.get(c, "#888") for c in cost_by_cloud["cloud"]],
                    line=dict(color="rgba(0,0,0,0.3)", width=1),
                ),
                textfont=dict(size=11, color="rgba(200,220,255,0.85)"),
                hovertemplate="<b>%{label}</b><br>$%{value:.4f}<br>%{percent}<extra></extra>",
            ))
            fig1.update_layout(**PLOTLY_LAYOUT, height=280)
            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

        # Cost by Associate
        with row1_c2:
            st.markdown('<div class="section-title">👤 Cost by Associate</div>', unsafe_allow_html=True)
            cost_by_assoc = df.groupby("associate_id")["cost"].sum().reset_index().sort_values("cost", ascending=True)
            fig2 = go.Figure(go.Bar(
                x=cost_by_assoc["cost"],
                y=cost_by_assoc["associate_id"],
                orientation="h",
                marker=dict(
                    color=cost_by_assoc["cost"],
                    colorscale=[[0, "#1e3a5f"], [0.5, "#0072ff"], [1, "#00d4ff"]],
                    line=dict(color="rgba(0,212,255,0.3)", width=0.5),
                ),
                hovertemplate="<b>%{y}</b><br>$%{x:.4f}<extra></extra>",
                text=[f"${v:.4f}" for v in cost_by_assoc["cost"]],
                textposition="outside",
                textfont=dict(size=9, color="rgba(180,200,240,0.7)"),
            ))
            fig2.update_layout(**PLOTLY_LAYOUT, height=280,
                               xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                               yaxis=dict(gridcolor="rgba(255,255,255,0.03)"))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        row2_c1, row2_c2 = st.columns(2)

        # Cost by Cost Centre
        with row2_c1:
            st.markdown('<div class="section-title">🏷 Cost Centre Allocation</div>', unsafe_allow_html=True)
            cost_by_cc = df.groupby("cost_centre")["cost"].sum().reset_index().sort_values("cost", ascending=False)
            fig3 = go.Figure(go.Bar(
                x=cost_by_cc["cost_centre"],
                y=cost_by_cc["cost"],
                marker=dict(
                    color=cost_by_cc["cost"],
                    colorscale=[[0, "#1e1b4b"], [0.5, "#7b2fff"], [1, "#c084fc"]],
                    line=dict(color="rgba(120,0,255,0.3)", width=0.5),
                ),
                hovertemplate="<b>%{x}</b><br>$%{y:.4f}<extra></extra>",
            ))
            fig3.update_layout(**PLOTLY_LAYOUT, height=260,
                               xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickangle=-20, tickfont=dict(size=9)),
                               yaxis=dict(gridcolor="rgba(255,255,255,0.04)"))
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        # Latency distribution
        with row2_c2:
            st.markdown('<div class="section-title">⏱ Latency Distribution</div>', unsafe_allow_html=True)
            lat_df = df[df["latency_ms"] > 0]
            if not lat_df.empty:
                fig4 = go.Figure(go.Histogram(
                    x=lat_df["latency_ms"],
                    nbinsx=20,
                    marker=dict(
                        color="rgba(0,212,255,0.5)",
                        line=dict(color="rgba(0,212,255,0.8)", width=0.5),
                    ),
                    hovertemplate="Latency: %{x} ms<br>Count: %{y}<extra></extra>",
                ))
                fig4.update_layout(**PLOTLY_LAYOUT, height=260,
                                   xaxis=dict(title="ms", gridcolor="rgba(255,255,255,0.05)"),
                                   yaxis=dict(title="Count", gridcolor="rgba(255,255,255,0.04)"))
                st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

        row3_c1, row3_c2 = st.columns(2)

        # Regional distribution
        with row3_c1:
            st.markdown('<div class="section-title">🌍 Regional Load Distribution</div>', unsafe_allow_html=True)
            region_counts = df.groupby("region")["cost"].sum().reset_index().sort_values("cost", ascending=False)
            fig5 = go.Figure(go.Bar(
                x=region_counts["cost"],
                y=region_counts["region"],
                orientation="h",
                marker=dict(
                    color=region_counts["cost"],
                    colorscale=[[0, "#0a2a1a"], [0.5, "#00b87a"], [1, "#00ff9d"]],
                    line=dict(color="rgba(0,255,100,0.2)", width=0.5),
                ),
                hovertemplate="<b>%{y}</b><br>$%{x:.4f}<extra></extra>",
            ))
            fig5.update_layout(**PLOTLY_LAYOUT, height=280,
                               xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                               yaxis=dict(gridcolor="rgba(255,255,255,0.03)"))
            st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

        # Model type breakdown
        with row3_c2:
            st.markdown('<div class="section-title">🤖 Model Type Breakdown</div>', unsafe_allow_html=True)
            model_df = df.groupby("model_type").agg(total_cost=("cost", "sum"), count=("cost", "count")).reset_index()
            fig6 = go.Figure()
            fig6.add_trace(go.Bar(
                x=model_df["model_type"],
                y=model_df["total_cost"],
                name="Cost",
                marker_color="rgba(0,212,255,0.6)",
                yaxis="y",
                hovertemplate="<b>%{x}</b><br>Cost: $%{y:.4f}<extra></extra>",
            ))
            fig6.add_trace(go.Scatter(
                x=model_df["model_type"],
                y=model_df["count"],
                name="Count",
                mode="lines+markers",
                marker=dict(color="#a855f7", size=8),
                line=dict(color="#a855f7", width=2),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Events: %{y}<extra></extra>",
            ))
            fig6.update_layout(
                **PLOTLY_LAYOUT,
                height=280,
                yaxis=dict(title="Cost ($)", gridcolor="rgba(255,255,255,0.05)", titlefont=dict(color="#00d4ff")),
                yaxis2=dict(title="Count", overlaying="y", side="right", titlefont=dict(color="#a855f7")),
                legend=dict(bgcolor="rgba(0,0,0,0)", x=0.01, y=0.99),
            )
            st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})

        # Token usage table
        st.markdown('<div class="section-title">🔢 Token & Usage Summary</div>', unsafe_allow_html=True)
        summary = df.groupby("cloud").agg(
            events=("cost", "count"),
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            total_input_tokens=("input_tokens", "sum"),
            total_output_tokens=("output_tokens", "sum"),
            total_cached_tokens=("cached_tokens", "sum"),
            avg_latency_ms=("latency_ms", "mean"),
        ).reset_index()
        summary.columns = ["Cloud", "Events", "Total Cost ($)", "Avg Cost ($)", "Input Tokens", "Output Tokens", "Cached Tokens", "Avg Latency (ms)"]
        summary["Total Cost ($)"] = summary["Total Cost ($)"].round(6)
        summary["Avg Cost ($)"] = summary["Avg Cost ($)"].round(6)
        summary["Avg Latency (ms)"] = summary["Avg Latency (ms)"].round(0).astype(int)
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )


# ════════════════════════════════════════════════════════════════════
# TAB 3 — SCHEMA INSPECTOR
# ════════════════════════════════════════════════════════════════════
with tab_schema:
    sc1, sc2 = st.columns([1, 1])

    with sc1:
        st.markdown('<div class="section-title">📋 CanonicalUsageEvent Schema</div>', unsafe_allow_html=True)
        schema_fields = {
            "timestamp": ("str", "ISO 8601 UTC timestamp"),
            "cloud": ("str", "Cloud provider (GCP / Azure / AWS / ...)"),
            "service": ("str", "Service name (Vertex AI, Bedrock, ...)"),
            "region": ("str", "Deployment region"),
            "account_id": ("str", "Subscription / Project / Account ID"),
            "resource_id": ("str", "Specific resource or model deployment"),
            "operation": ("str", "Operation type (chat / completion / ...)"),
            "associate_id": ("str", "Employee ID for cost attribution"),
            "cost_centre": ("str", "Budget cost center code"),
            "project_code": ("str", "Project billing code"),
            "request_units": ("Dict[str, float]", "Usage metrics (tokens, seconds, chars...)"),
            "cost": ("float", "Calculated cost in USD"),
            "model_version": ("str?", "Model version snapshot tag"),
            "model_type": ("str?", "Model category (LLM / Multimodal / ...)"),
            "latency_ms": ("int?", "API response latency in ms"),
        }
        rows = "".join(
            f"""<tr>
                <td style="padding:6px 10px; font-family:'JetBrains Mono',monospace; color:#00d4ff; font-size:0.78rem;">{k}</td>
                <td style="padding:6px 10px; font-family:'JetBrains Mono',monospace; color:#a855f7; font-size:0.75rem;">{t}</td>
                <td style="padding:6px 10px; color:rgba(180,200,240,0.7); font-size:0.75rem;">{desc}</td>
            </tr>"""
            for k, (t, desc) in schema_fields.items()
        )
        st.markdown(f"""
        <div class="glass-card" style="padding:0; overflow:hidden;">
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background:rgba(0,212,255,0.07); border-bottom:1px solid rgba(0,212,255,0.15);">
                        <th style="padding:8px 10px; text-align:left; font-size:0.72rem; color:rgba(150,170,210,0.7); font-weight:600; text-transform:uppercase; letter-spacing:0.8px;">Field</th>
                        <th style="padding:8px 10px; text-align:left; font-size:0.72rem; color:rgba(150,170,210,0.7); font-weight:600; text-transform:uppercase; letter-spacing:0.8px;">Type</th>
                        <th style="padding:8px 10px; text-align:left; font-size:0.72rem; color:rgba(150,170,210,0.7); font-weight:600; text-transform:uppercase; letter-spacing:0.8px;">Description</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with sc2:
        st.markdown('<div class="section-title">🔍 Sample Message Payload</div>', unsafe_allow_html=True)
        sample = events[0] if events else {
            "message_id": "mock-msg-0001",
            "data": {
                "timestamp": "2026-06-25T14:02:15.184Z",
                "cloud": "GCP",
                "service": "Vertex AI",
                "region": "us-central1",
                "account_id": "cog01k24f1ea555zdv7ynzthxanz5",
                "resource_id": "endpoint-gemini-1.5-pro-002-deployment",
                "operation": "completion",
                "associate_id": "soham.ganguly",
                "cost_centre": "CC-AI-RESEARCH",
                "project_code": "PROJ-VERIFORGE-OPS",
                "request_units": {
                    "input_tokens": 420000,
                    "output_tokens": 4500,
                    "total_tokens": 424500,
                    "cached_tokens": 380000,
                    "input_images": 4,
                    "input_audio_seconds": 15.4,
                },
                "cost": 0.096425,
                "model_version": "002",
                "model_type": "Multimodal",
                "latency_ms": 5280,
            },
        }
        st.code(json.dumps(sample, indent=2), language="json")

        st.markdown('<div class="section-title" style="margin-top:16px;">⚡ Pub/Sub Wrapper API</div>', unsafe_allow_html=True)
        st.code("""from src.pubsub_wrapper import PubSubTelemetryWrapper

# Initialize in mock mode (no GCP credentials needed)
wrapper = PubSubTelemetryWrapper(mock_mode=True)

# Option A — publish a pre-built CanonicalUsageEvent
wrapper.publish_event(canonical_event)

# Option B — normalize raw provider payload
wrapper.publish_raw(
    cloud_provider="gcp",       # azure / aws / sanas / ai_tools
    raw_payload=raw_log_dict,
    identity_context={
        "associate_id": "priya.sharma",
        "cost_centre": "CC-BFSI-PRODUCTS",
        "project_code": "PROJ-UNDERWRITING-BOT",
    }
)

# Retrieve published events (mock mode)
events = wrapper.get_mock_events()
""", language="python")


# ════════════════════════════════════════════════════════════════════
# TAB 4 — INTEGRATION GUIDE
# ════════════════════════════════════════════════════════════════════
with tab_docs:
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("""
        <div class="glass-card">
            <div class="section-title">🚀 Quick Start</div>
            <div style="font-size:0.82rem; color:rgba(180,200,240,0.8); line-height:1.7;">
                <strong style="color:#00d4ff;">1. Install dependencies</strong><br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px; color:#a855f7;">pip install google-cloud-pubsub pydantic</code>
                <br><br>
                <strong style="color:#00d4ff;">2. Set environment variables</strong><br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px; color:#a855f7; font-size:0.75rem;">GOOGLE_CLOUD_PROJECT=cog01k24f1ea555zdv7ynzthxanz5<br>VERIFORGE_PUBSUB_TOPIC=veriforgeops-telemetry-ingest</code>
                <br><br>
                <strong style="color:#00d4ff;">3. Authenticate</strong><br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px; color:#a855f7;">gcloud auth application-default login</code>
                <br><br>
                <strong style="color:#00d4ff;">4. Run the demo</strong><br>
                <code style="background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px; color:#a855f7;">python demo.py</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card">
            <div class="section-title">☁️ Supported Cloud Providers</div>
            <div style="font-size:0.82rem; color:rgba(180,200,240,0.8); line-height:1.8;">
                <span style="color:#4285f4;">●</span> <strong>GCP</strong> — Vertex AI (Gemini 1.5/2.0), Speech-to-Text, Translation, Embeddings<br>
                <span style="color:#00bcf2;">●</span> <strong>Azure</strong> — OpenAI (GPT-4o, GPT-4), Cognitive Services, Translator<br>
                <span style="color:#ff9900;">●</span> <strong>AWS</strong> — Bedrock (Claude 3, Nova Pro), Transcribe, Translate<br>
                <span style="color:#a855f7;">●</span> <strong>Sanas</strong> — Voice AI speech clarification<br>
                <span style="color:#00d4ff;">●</span> <strong>AI Tools</strong> — Claude Code, GitHub Copilot, Tabnine, Cursor AI
            </div>
        </div>
        """, unsafe_allow_html=True)

    with d2:
        st.markdown("""
        <div class="glass-card">
            <div class="section-title">🔄 Pipeline Flow</div>
            <div style="font-size:0.82rem; color:rgba(180,200,240,0.8); line-height:1.9;">
                <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:8px;">
                    <span style="background:rgba(0,212,255,0.15); border:1px solid rgba(0,212,255,0.3); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.7rem; color:#00d4ff; flex-shrink:0; margin-top:1px;">1</span>
                    <span><strong>Raw Telemetry Collection</strong> — Cloud logs, SDK intercepts, billing exports arrive from provider-native formats.</span>
                </div>
                <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:8px;">
                    <span style="background:rgba(0,212,255,0.15); border:1px solid rgba(0,212,255,0.3); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.7rem; color:#00d4ff; flex-shrink:0; margin-top:1px;">2</span>
                    <span><strong>Connector Normalization</strong> — Provider-specific connectors transform raw payloads into <code>CanonicalUsageEvent</code> with cost calculation.</span>
                </div>
                <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:8px;">
                    <span style="background:rgba(0,212,255,0.15); border:1px solid rgba(0,212,255,0.3); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.7rem; color:#00d4ff; flex-shrink:0; margin-top:1px;">3</span>
                    <span><strong>Pub/Sub Publishing</strong> — Validated events are serialized and asynchronously published to the GCP topic with callbacks.</span>
                </div>
                <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:8px;">
                    <span style="background:rgba(0,212,255,0.15); border:1px solid rgba(0,212,255,0.3); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.7rem; color:#00d4ff; flex-shrink:0; margin-top:1px;">4</span>
                    <span><strong>FinOps Aggregation</strong> — Subscribers consume messages; MongoDB stores events with cost attribution, anomaly detection, and budget alerts.</span>
                </div>
                <div style="display:flex; align-items:flex-start; gap:10px;">
                    <span style="background:rgba(0,212,255,0.15); border:1px solid rgba(0,212,255,0.3); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-size:0.7rem; color:#00d4ff; flex-shrink:0; margin-top:1px;">5</span>
                    <span><strong>Dashboard & Reporting</strong> — Cost breakdown by associate, cost centre, project, model, and region with budget alerts.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card">
            <div class="section-title">📌 NFR Compliance</div>
            <div style="font-size:0.82rem; color:rgba(180,200,240,0.8); line-height:1.8;">
                <span style="color:#00ff9d;">✓</span> <strong>NFR-M1</strong> — Cost centre & project attribution per event<br>
                <span style="color:#00ff9d;">✓</span> <strong>NFR-M2</strong> — Associate-level attribution via employee ID<br>
                <span style="color:#00ff9d;">✓</span> <strong>NFR-M3</strong> — Multimodal usage tracking (tokens, images, audio, video)<br>
                <span style="color:#00ff9d;">✓</span> <strong>NFR-P1</strong> — Cached token savings tracking (75% discount)<br>
                <span style="color:#00ff9d;">✓</span> <strong>NFR-P2</strong> — Latency monitoring per API call<br>
                <span style="color:#ffb400;">~</span> <strong>NFR-S1</strong> — Mock mode for local development without GCP creds
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:24px 0 8px; color:rgba(120,140,180,0.35); font-size:0.72rem; letter-spacing:0.5px;">
    VeriForgeOps · FinOps Telemetry Platform · Cognizant Technology Solutions
    &nbsp;·&nbsp; Built with Streamlit &amp; Google Cloud Pub/Sub
</div>
""", unsafe_allow_html=True)
