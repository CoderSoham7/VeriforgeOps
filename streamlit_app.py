"""
VeriForgeOps — Vertex AI Telemetry & FinOps Engine
Streamlit UI styled to match the FinOps dashboard (Tailwind/glassmorphic).
"""

import streamlit as st
import json
import random
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
from typing import Dict, Any, List
import os

# Live Pub/Sub integration (optional — UI still works in mock mode if GCP is unreachable)
try:
    from src import pubsub_live
    _LIVE_AVAILABLE = True
except Exception:
    pubsub_live = None
    _LIVE_AVAILABLE = False

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VeriForge Ops · Vertex AI Telemetry & FinOps",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── HTML helper (collapses indentation so Streamlit never code-blocks it) ─────
def html(markup: str):
    cleaned = "".join(line.strip() for line in markup.splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


# ── Palette (mirrors the dashboard's Tailwind config) ─────────────────────────
C = {
    "bg": "#0b0f19",
    "card": "rgba(17, 24, 39, 0.7)",
    "border": "rgba(255,255,255,0.08)",
    "brand500": "#6366f1",
    "brand600": "#4f46e5",
    "brand700": "#4338ca",
    "indigo300": "#a5b4fc",
    "indigo400": "#818cf8",
    "blue": "#4285F4",
    "red": "#EA4335",
    "yellow": "#FBBC05",
    "green": "#34A853",
    "purple": "#a855f7",
    "gray400": "#9ca3af",
    "gray500": "#6b7280",
}

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

.stApp {{ background-color: {C['bg']}; color: #f3f4f6; }}

#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; }}
.block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px; }}

/* ── Glass card ─────────────────────────────────────────────────────────── */
.glass-card {{
    background: {C['card']};
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}
.glass-card:hover {{
    border-color: rgba(99,102,241,0.3);
    box-shadow: 0 10px 30px -10px rgba(99,102,241,0.15);
}}

/* ── Header ─────────────────────────────────────────────────────────────── */
.vf-header {{
    background: {C['card']};
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 18px 24px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
}}
.vf-logo {{
    height: 44px; width: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, {C['brand500']}, {C['brand700']});
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 8px 24px -6px rgba(99,102,241,0.4);
}}
.vf-eyebrow {{
    font-size: 0.68rem; font-weight: 700; letter-spacing: 2px;
    color: {C['brand500']}; text-transform: uppercase;
}}
.vf-title {{ font-size: 1.35rem; font-weight: 700; color: #fff; letter-spacing:-0.3px; margin:0; }}
.vf-active {{
    display:inline-block; font-size:0.6rem; font-weight:600; padding:1px 8px;
    border-radius:20px; background:rgba(52,168,83,0.1); color:{C['green']};
    border:1px solid rgba(52,168,83,0.3); margin-left:8px; vertical-align:middle;
}}

/* ── KPI cards ──────────────────────────────────────────────────────────── */
.kpi {{
    background: {C['card']};
    backdrop-filter: blur(12px);
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 22px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    height: 100%;
}}
.kpi:hover {{ border-color: rgba(99,102,241,0.3); box-shadow: 0 10px 30px -10px rgba(99,102,241,0.15); }}
.kpi-blur {{ position:absolute; top:0; right:0; width:120px; height:120px; border-radius:50%; filter:blur(48px); }}
.kpi-head {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; }}
.kpi-icon {{ padding:12px; border-radius:12px; font-size:1.2rem; line-height:1; }}
.kpi-tag {{ font-size:0.65rem; font-weight:600; padding:4px 9px; border-radius:8px; }}
.kpi-value {{ font-size:1.9rem; font-weight:800; color:#fff; letter-spacing:-0.5px; line-height:1.1; }}
.kpi-label {{ font-size:0.82rem; font-weight:500; color:{C['gray400']}; margin-top:4px; }}
.kpi-foot {{ font-size:0.7rem; margin-top:14px; display:flex; align-items:center; gap:6px; }}

/* ── Section heads ──────────────────────────────────────────────────────── */
.sec-title {{ font-size:1.05rem; font-weight:700; color:#fff; margin:0; }}
.sec-sub {{ font-size:0.72rem; color:{C['gray400']}; margin-top:2px; }}

/* ── Tables ─────────────────────────────────────────────────────────────── */
.vf-table {{ width:100%; border-collapse:collapse; font-size:0.78rem; }}
.vf-table thead tr {{ border-bottom:1px solid rgba(255,255,255,0.08); color:{C['gray400']}; }}
.vf-table th {{ padding:10px 12px; text-align:left; font-weight:600; }}
.vf-table td {{ padding:11px 12px; border-bottom:1px solid rgba(255,255,255,0.05); }}
.vf-table tbody tr:hover {{ background:rgba(17,24,39,0.5); }}
.dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:8px; }}
.mono {{ font-family:'JetBrains Mono', monospace; }}

/* ── Progress bars ──────────────────────────────────────────────────────── */
.bar-track {{ width:100%; height:8px; background:rgba(255,255,255,0.06); border-radius:8px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:8px; }}

/* ── Associate rows ─────────────────────────────────────────────────────── */
.assoc-row {{
    display:flex; align-items:center; justify-content:space-between;
    padding:12px; background:rgba(17,24,39,0.5); border:1px solid rgba(255,255,255,0.06);
    border-radius:12px; margin-bottom:12px;
}}
.assoc-avatar {{
    height:34px; width:34px; border-radius:50%;
    background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2);
    display:flex; align-items:center; justify-content:center;
    font-size:0.72rem; font-weight:700; color:{C['indigo400']};
}}

/* ── Pipeline nodes ─────────────────────────────────────────────────────── */
.flow-node {{
    border-left:4px solid rgba(255,255,255,0.1);
    background:rgba(17,24,39,0.5);
    padding:16px; border-radius:0 12px 12px 0; height:100%;
}}
.flow-node.active {{ border-left-color:{C['brand500']}; background:rgba(99,102,241,0.1); }}

/* ── Insight cards ──────────────────────────────────────────────────────── */
.insight {{ padding:16px; border-radius:12px; height:100%; }}

/* ── Streamlit widget overrides ─────────────────────────────────────────── */
.stButton > button {{
    background: {C['brand600']} !important;
    border: 1px solid rgba(99,102,241,0.4) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{ background: {C['brand700']} !important; box-shadow: 0 8px 20px -6px rgba(99,102,241,0.5) !important; }}

[data-testid="stSidebar"] {{
    background: rgba(13,17,28,0.92) !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}}

div[data-testid="stSelectbox"] > div, .stNumberInput input, .stTextInput input {{
    background: rgba(13,17,28,0.9) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e5e7eb !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    background: rgba(13,17,28,0.8);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 5px; gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent; border-radius: 8px;
    color: {C['gray400']} !important; font-weight: 500; font-size: 0.8rem;
    padding: 6px 14px;
}}
.stTabs [aria-selected="true"] {{ background: {C['brand600']} !important; color: #fff !important; }}

label, .stMarkdown p {{ color: #d1d5db; }}
h1,h2,h3 {{ color:#fff !important; }}

::-webkit-scrollbar {{ width:6px; height:6px; }}
::-webkit-scrollbar-track {{ background: rgba(11,15,25,0.5); }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.15); border-radius:3px; }}

.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: {C['brand500']} !important; }}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "published_events" not in st.session_state:
    st.session_state.published_events = []
if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 0
if "live_mode" not in st.session_state:
    st.session_state.live_mode = False
if "status_banner" not in st.session_state:
    st.session_state.status_banner = None  # (kind, text)


# ── Provider metadata & generators ────────────────────────────────────────────
PROVIDER_META = {
    "GCP": {
        "services": ["Vertex AI", "Cloud Speech-to-Text", "Cloud Translation", "Vertex AI Embeddings"],
        "regions": ["us-central1", "asia-northeast1", "europe-west3", "us-east4"],
        "models": [
            ("gemini-1.5-pro", "001", "Multimodal"),
            ("gemini-1.5-pro", "002", "Multimodal"),
            ("gemini-1.5-flash", "001", "LLM"),
            ("gemini-1.5-flash", "002", "LLM"),
            ("gemini-2.0-flash", "exp", "Multimodal"),
            ("speech-to-text", "stable", "Speech"),
            ("translation", "stable", "Translation"),
            ("textembedding-gecko", "003", "Embedding"),
        ],
        "operations": ["completion", "transcribe", "translate", "embedding"],
        "account": "cog01k24f1ea555zdv7ynzthxanz5",
    },
    "Azure": {
        "services": ["Azure OpenAI", "Azure Cognitive Services", "Azure Translator"],
        "regions": ["eastus", "westeurope", "southeastasia", "australiaeast"],
        "models": [("gpt-4o", "2024-05", "LLM"), ("gpt-4", "turbo", "LLM"), ("text-embedding-ada-002", "v2", "Embedding")],
        "operations": ["chat", "completion", "embedding", "translate"],
        "account": "sub-cog-azure-0042",
    },
    "AWS": {
        "services": ["AWS Bedrock", "Amazon Transcribe", "Amazon Translate"],
        "regions": ["us-east-1", "ap-southeast-1", "eu-west-1"],
        "models": [("anthropic.claude-3-sonnet", "20240229", "LLM"), ("amazon.nova-pro", "v1", "Multimodal"), ("amazon.titan-embed", "v2", "Embedding")],
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
        "models": [("claude-code", "4.6", "LLM"), ("copilot-gpt4", "turbo", "LLM")],
        "operations": ["code_generation", "code_completion", "explain_code"],
        "account": "ai-tools-cog-global",
    },
}

ASSOCIATES = {
    "soham.ganguly": "CC-AI-RESEARCH",
    "priya.sharma": "CC-BFSI-PRODUCTS",
    "john.doe": "CC-HEALTHCARE-DEV",
    "clara.oswald": "CC-OPERATIONS",
    "ravi.kumar": "CC-DATA-ENGINEERING",
    "mei.chen": "CC-CLOUD-PLATFORM",
}
PROJECTS = ["PROJ-VERIFORGE-OPS", "PROJ-UNDERWRITING-BOT", "PROJ-CLINICAL-TRANSCRIPT", "PROJ-CHATBOT-PLATFORM", "PROJ-FRAUD-DETECTION"]

PROVIDER_COLORS = {"GCP": C["blue"], "Azure": "#00bcf2", "AWS": C["yellow"], "Sanas": C["purple"], "AI Tools": C["brand500"]}
REGION_COLORS = [C["blue"], C["yellow"], C["red"], C["brand500"], C["green"], C["purple"]]


def _rand_request_units(operation: str) -> Dict[str, Any]:
    if operation in ("transcribe", "speech_clarification"):
        return {"input_audio_seconds": round(random.uniform(10, 300), 1), "output_characters": random.randint(100, 2000)}
    if operation == "translate":
        return {"input_characters": random.randint(500, 50000)}
    if operation == "embedding":
        t = random.randint(100, 8000)
        return {"input_tokens": t, "output_tokens": 0, "total_tokens": t}
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
    if random.random() > 0.85:
        ru["input_video_seconds"] = round(random.uniform(1, 30), 1)
    return ru


def _approx_cost(provider: str, operation: str, ru: Dict) -> float:
    if "input_audio_seconds" in ru and operation in ("transcribe", "speech_clarification"):
        return round(ru["input_audio_seconds"] * 0.0004, 6)
    if "input_characters" in ru:
        return round(ru["input_characters"] * 0.00002, 6)
    inp = ru.get("input_tokens", 0)
    out = ru.get("output_tokens", 0)
    cached = ru.get("cached_tokens", 0)
    rate_map = {"GCP": (1.25, 5.0, 0.3125), "Azure": (10.0, 30.0, 0), "AWS": (3.0, 15.0, 0), "Sanas": (0, 0, 0), "AI Tools": (8.0, 24.0, 0)}
    ri, ro, rc = rate_map.get(provider, (5.0, 15.0, 0))
    cost = ((inp - cached) * ri + out * ro + cached * rc) / 1_000_000
    cost += ru.get("input_images", 0) * 0.0025
    cost += ru.get("input_audio_seconds", 0) * 0.000125
    cost += ru.get("input_video_seconds", 0) * 0.002
    return max(0.000001, round(cost, 6))


def generate_mock_event(provider: str = None) -> Dict[str, Any]:
    if provider is None:
        provider = random.choice(list(PROVIDER_META.keys()))
    meta = PROVIDER_META[provider]
    model_name, model_ver, model_type = random.choice(meta["models"])
    operation = random.choice(meta["operations"])
    associate = random.choice(list(ASSOCIATES.keys()))
    ru = _rand_request_units(operation)
    cost = _approx_cost(provider, operation, ru)
    st.session_state.msg_counter += 1
    return {
        "message_id": f"mock-msg-{st.session_state.msg_counter:04d}",
        "data": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "cloud": provider,
            "service": random.choice(meta["services"]),
            "region": random.choice(meta["regions"]),
            "account_id": meta["account"],
            "resource_id": f"{model_name}-{model_ver}",
            "operation": operation,
            "associate_id": associate,
            "cost_centre": ASSOCIATES[associate],
            "project_code": random.choice(PROJECTS),
            "request_units": ru,
            "cost": cost,
            "model_version": model_ver,
            "model_type": model_type,
            "latency_ms": random.randint(200, 8000),
        },
    }


# ── Plotly layout ─────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=C["gray400"], size=11),
    margin=dict(l=10, r=10, t=20, b=10),
)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SIDEBAR — Pub/Sub Publisher                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with st.sidebar:
    html(f"""
    <div style="text-align:center; padding:8px 0 16px;">
        <div style="font-size:2rem;">⚡</div>
        <div style="font-size:1.05rem; font-weight:700; color:{C['brand500']};">VeriForge Ops</div>
        <div style="font-size:0.68rem; color:{C['gray500']}; margin-top:2px;">Pub/Sub Telemetry Publisher</div>
    </div>
    """)
    st.divider()

    # ── Mode toggle: Mock (session only) vs Live (real GCP Pub/Sub) ───────────
    live_default = st.session_state.live_mode
    st.session_state.live_mode = st.toggle(
        "🛰 Live GCP Pub/Sub",
        value=live_default,
        help="OFF = local mock (session only). ON = publish to / pull from the real "
             "Pub/Sub topic. Requires GCP credentials.",
        disabled=not _LIVE_AVAILABLE,
    )
    LIVE = st.session_state.live_mode and _LIVE_AVAILABLE

    # Surface credential status when live mode is requested.
    if LIVE:
        ok_creds, creds_msg = pubsub_live.connection_status()
        if ok_creds:
            st.caption(f"✅ Credentials: {creds_msg}")
        else:
            st.caption(f"⚠️ {creds_msg}")
    elif st.session_state.live_mode and not _LIVE_AVAILABLE:
        st.caption("⚠️ Live module unavailable — using mock mode.")

    st.markdown("##### 📡 Publish Telemetry")
    publish_provider = st.selectbox("Cloud Provider", ["Random"] + list(PROVIDER_META.keys()))
    publish_count = st.slider("Batch Size", 1, 30, 10)

    # Delivery method (only relevant in live mode).
    delivery = "Direct to Topic"
    if LIVE:
        delivery = st.radio(
            "Delivery method",
            ["Direct to Topic", "Via Log Router (Cloud Logging)"],
            help="Direct to Topic = Publisher API straight to the topic (does NOT "
                 "increment the Log Router sink volume). Via Log Router = write to "
                 "Cloud Logging so the vertex-ai-telemetry-sink routes it to the "
                 "topic (this DOES increment the sink volume; routing takes a few seconds).",
        )

    cA, cB = st.columns(2)
    with cA:
        do_publish = st.button("▶ Publish", use_container_width=True)
    with cB:
        do_clear = st.button("⟳ Reset", use_container_width=True)

    if do_clear:
        st.session_state.published_events = []
        st.session_state.msg_counter = 0
        st.session_state.status_banner = None
        st.rerun()

    if do_publish:
        prov = None if publish_provider == "Random" else publish_provider
        new = [generate_mock_event(prov) for _ in range(publish_count)]
        if LIVE and delivery.startswith("Via Log Router"):
            ok, msg, n = pubsub_live.log_events([e["data"] for e in new])
            st.session_state.status_banner = ("success" if ok else "error", msg)
            if ok:
                # Show locally; routed copies will also be pullable from the topic.
                for e in new:
                    e["data"]["_routed_via_log_router"] = True
                st.session_state.published_events = new + st.session_state.published_events
        elif LIVE:
            ok, msg, ids = pubsub_live.publish_events([e["data"] for e in new])
            st.session_state.status_banner = ("success" if ok else "error", msg)
            if ok:
                # Reflect the real Pub/Sub message IDs in the local view.
                for e, mid in zip(new, ids):
                    e["message_id"] = mid
                st.session_state.published_events = new + st.session_state.published_events
        else:
            st.session_state.published_events = new + st.session_state.published_events
        st.rerun()

    # Live pull control (only meaningful in live mode).
    if LIVE:
        if st.button("⬇ Pull Live Events", use_container_width=True):
            ok, msg, recs = pubsub_live.pull_events(max_messages=50)
            st.session_state.status_banner = ("success" if ok else "error", msg)
            if ok and recs:
                st.session_state.published_events = recs + st.session_state.published_events
            st.rerun()

    if st.button("📂 Load Sample JSONL", use_container_width=True):
        p = os.path.join(os.path.dirname(__file__), "mock_telemetry_pubsub.jsonl")
        if os.path.exists(p):
            loaded = []
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            loaded.append(json.loads(line))
                        except Exception:
                            pass
            if loaded:
                st.session_state.published_events = loaded + st.session_state.published_events
                st.session_state.msg_counter = max(st.session_state.msg_counter, len(loaded))
                st.rerun()

    st.divider()
    if LIVE:
        mode_badge = f'<span style="color:{C["green"]}; font-weight:700;">● LIVE — GCP PUB/SUB</span>'
    else:
        mode_badge = '<span class="vf-active" style="margin:0;">● MOCK MODE</span>'
    html(f"""
    <div style="font-size:0.7rem; color:{C['gray400']}; line-height:1.7;">
        <div style="font-size:0.62rem; text-transform:uppercase; letter-spacing:1px; color:{C['gray500']}; margin-bottom:6px;">Pub/Sub Connection</div>
        <div>{mode_badge}</div>
        <div style="margin-top:8px;">📦 Topic: <span class="mono" style="color:{C['brand500']};">veriforgeops-telemetry-ingest</span></div>
        <div style="margin-top:4px;">🗂 Project: <span class="mono" style="color:{C['brand500']};">cog01k24f1...</span></div>
    </div>
    """)


# ── Aggregate published events ────────────────────────────────────────────────
events = st.session_state.published_events
USING_SAMPLE = len(events) == 0

if events:
    df = pd.DataFrame([{
        "cloud": e["data"]["cloud"], "service": e["data"]["service"], "region": e["data"]["region"],
        "operation": e["data"]["operation"], "associate_id": e["data"]["associate_id"],
        "cost_centre": e["data"]["cost_centre"], "project_code": e["data"]["project_code"],
        "resource_id": e["data"]["resource_id"], "cost": e["data"]["cost"],
        "model_type": e["data"].get("model_type", "—"), "model_version": e["data"].get("model_version", "—"),
        "latency_ms": e["data"].get("latency_ms", 0),
        "input_tokens": e["data"]["request_units"].get("input_tokens", 0),
        "output_tokens": e["data"]["request_units"].get("output_tokens", 0),
        "total_tokens": e["data"]["request_units"].get("total_tokens", e["data"]["request_units"].get("input_tokens", 0)),
        "cached_tokens": e["data"]["request_units"].get("cached_tokens", 0),
        "input_images": e["data"]["request_units"].get("input_images", 0),
        "input_audio_seconds": e["data"]["request_units"].get("input_audio_seconds", 0),
        "input_video_seconds": e["data"]["request_units"].get("input_video_seconds", 0),
    } for e in events])

    total_cost = df["cost"].sum()
    total_tokens = int(df["total_tokens"].sum())
    prompt_tokens = int(df["input_tokens"].sum())
    output_tokens = int(df["output_tokens"].sum())
    cached_tokens = int(df["cached_tokens"].sum())
    cache_savings = cached_tokens * (1.25 - 0.3125) / 1_000_000
    lat = df[df["latency_ms"] > 0]["latency_ms"]
    avg_latency = lat.mean() if not lat.empty else 0
    n_events = len(df)
    total_images = int(df["input_images"].sum())
    total_audio = df["input_audio_seconds"].sum()
    total_video = df["input_video_seconds"].sum()
else:
    df = None
    total_cost, total_tokens, prompt_tokens, output_tokens = 10.0179, 5089213, 4843370, 245843
    cached_tokens, cache_savings, avg_latency, n_events = 585830, 0.3048, 3539.63, 150
    total_images, total_audio, total_video = 102, 4005.0, 377.0


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  HEADER                                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
html(f"""
<div class="vf-header">
    <div style="display:flex; align-items:center; gap:14px;">
        <div class="vf-logo">⚡</div>
        <div>
            <div class="vf-eyebrow">VeriForge Ops <span class="vf-active">Active</span></div>
            <h1 class="vf-title">Vertex AI Telemetry &amp; FinOps Engine</h1>
        </div>
    </div>
    <div style="font-size:0.72rem; color:{C['gray400']}; text-align:right;">
        <div>Multi-cloud Pub/Sub ingestion pipeline</div>
        <div class="mono" style="color:{C['brand500']}; margin-top:2px;">{n_events} events ingested</div>
    </div>
</div>
""")

if USING_SAMPLE:
    html(f"""<div style="background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.2); border-radius:10px; padding:10px 16px; margin-bottom:18px; font-size:0.76rem; color:{C['indigo300']};">
    📊 Showing reference figures from the 150-event sample. Use the sidebar to <strong>Publish</strong> live mock telemetry or <strong>Load Sample JSONL</strong> to drive every panel from real data.</div>""")


# ── KPI cards ─────────────────────────────────────────────────────────────────
def kpi(col, icon, icon_bg, icon_color, blur_color, tag, tag_bg, tag_color, value, value_color, label, foot_icon, foot_color, foot_text):
    with col:
        html(f"""
        <div class="kpi">
            <div class="kpi-blur" style="background:{blur_color};"></div>
            <div class="kpi-head">
                <div class="kpi-icon" style="background:{icon_bg}; color:{icon_color}; border:1px solid {icon_color}33;">{icon}</div>
                <span class="kpi-tag" style="background:{tag_bg}; color:{tag_color}; border:1px solid {tag_color}33;">{tag}</span>
            </div>
            <div class="kpi-value" style="color:{value_color};">{value}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-foot" style="color:{foot_color};">{foot_icon}&nbsp;<span>{foot_text}</span></div>
        </div>
        """)


k1, k2, k3, k4 = st.columns(4)
kpi(k1, "💲", "rgba(99,102,241,0.1)", C["brand500"], "rgba(99,102,241,0.15)",
    "Aggregated", "rgba(99,102,241,0.1)", C["indigo400"],
    f"${total_cost:,.4f}", "#fff", "Total Telemetry Cost", "🧱", C["indigo400"], f"From {n_events} ingested events")
kpi(k2, "✨", "rgba(52,168,83,0.1)", C["green"], "rgba(52,168,83,0.15)",
    "75% Save Rate", "rgba(52,168,83,0.1)", C["green"],
    f"${cache_savings:,.4f}", C["green"], "Context Cache Savings", "⚡", C["green"], f"{cached_tokens:,} tokens cached")
kpi(k3, "🗄️", "rgba(66,133,244,0.1)", C["blue"], "rgba(66,133,244,0.15)",
    "In/Out Tokens", "rgba(66,133,244,0.1)", C["blue"],
    f"{total_tokens:,}", "#fff", "Total Transacted Tokens", "↘", C["blue"], f"{prompt_tokens/1e6:.2f}M prompt · {output_tokens/1e3:.0f}K output")
kpi(k4, "⏱️", "rgba(251,188,5,0.1)", C["yellow"], "rgba(251,188,5,0.15)",
    "Average", "rgba(251,188,5,0.1)", C["yellow"],
    f"{avg_latency:,.0f} <span style='font-size:0.9rem; font-weight:400; color:{C['gray400']};'>ms</span>", "#fff",
    "Mean API Latency", "✅", C["yellow"], "Flash models lead efficiency")

# Surface live publish/pull status from the most recent sidebar action.
if st.session_state.status_banner:
    _kind, _text = st.session_state.status_banner
    (st.success if _kind == "success" else st.error)(_text)

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TABS                                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
tab_overview, tab_flow, tab_pricing, tab_stream, tab_code = st.tabs([
    "📊 Executive Overview", "🔀 Telemetry Flow", "🧮 Pricing Matrix", "📡 Event Stream", "</> Code Updates"
])


# ════════════════════════════════════════════════════════════════════
# TAB — EXECUTIVE OVERVIEW
# ════════════════════════════════════════════════════════════════════
with tab_overview:
    left, right = st.columns([2, 1])

    # ---- LEFT COLUMN ----
    with left:
        # Cost breakdown chart
        html("""<div class="glass-card" style="margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                <div><div class="sec-title">Project &amp; Cost Centre Breakdowns</div>
                <div class="sec-sub">Verified spend allocations across departments and engineering pods.</div></div>
            </div></div>""")

        breakdown_mode = st.radio("Breakdown", ["Cost Centre", "Project Code"], horizontal=True, label_visibility="collapsed")
        group_col = "cost_centre" if breakdown_mode == "Cost Centre" else "project_code"

        if df is not None:
            alloc = df.groupby(group_col)["cost"].sum().reset_index().sort_values("cost", ascending=False)
            labels, values = alloc[group_col].tolist(), alloc["cost"].tolist()
        else:
            if group_col == "cost_centre":
                labels = ["CC-AI-RESEARCH", "CC-BFSI-PRODUCTS", "CC-HEALTHCARE-DEV", "CC-OPERATIONS"]
            else:
                labels = ["PROJ-VERIFORGE-OPS", "PROJ-UNDERWRITING-BOT", "PROJ-CLINICAL-TRANSCRIPT", "PROJ-SUPPORT-BOT"]
            values = [3.0792, 3.0764, 2.4825, 1.3797]

        bar_colors = (REGION_COLORS * 5)[:len(labels)]
        fig_alloc = go.Figure(go.Bar(
            x=labels, y=values,
            marker=dict(color=bar_colors, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            hovertemplate="<b>%{x}</b><br>$%{y:.4f} USD<extra></extra>",
        ))
        fig_alloc.update_layout(**PLOTLY_LAYOUT, height=300,
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
            bargap=0.45)
        fig_alloc.update_traces(marker_line_width=1)
        st.plotly_chart(fig_alloc, use_container_width=True, config={"displayModeBar": False})

        # Model performance table
        html("""<div class="glass-card" style="margin-bottom:8px;">
            <div class="sec-title">Model Versions Performance Matrix</div>
            <div class="sec-sub">Transacted tokens, execution latency, and financial overhead per endpoint.</div>
        </div>""")

        if df is not None:
            perf = df.groupby(["resource_id", "model_type"]).agg(
                calls=("cost", "count"), latency=("latency_ms", "mean"),
                tokens=("total_tokens", "sum"), spend=("cost", "sum")).reset_index().sort_values("spend", ascending=False)
            rows = ""
            type_color = {"Multimodal": C["red"], "LLM": C["blue"], "Speech": C["green"], "Translation": C["purple"], "Embedding": C["yellow"]}
            for _, r in perf.head(10).iterrows():
                dotc = type_color.get(r["model_type"], C["gray400"])
                spend_color = C["red"] if r["spend"] > total_cost * 0.15 else C["indigo300"]
                tok = f"{int(r['tokens']):,}" if r["tokens"] > 0 else "—"
                rows += f"""<tr>
                    <td style="color:#fff;"><span class="dot" style="background:{dotc};"></span>{r['resource_id']}</td>
                    <td>{int(r['calls'])} calls</td>
                    <td>{r['latency']:,.0f} ms</td>
                    <td class="mono">{tok}</td>
                    <td style="text-align:right; color:{spend_color}; font-weight:700;">${r['spend']:.4f}</td></tr>"""
        else:
            sample_rows = [
                ("gemini-1.5-pro-001", C["red"], "20 calls", "4,014.9 ms", "1,614,513", "$3.6607", C["red"]),
                ("gemini-1.5-pro-002", C["red"], "13 calls", "3,312.9 ms", "1,008,119", "$1.6315", C["indigo400"]),
                ("gemini-1.5-flash-001", C["blue"], "17 calls", "3,851.1 ms", "738,379", "$0.0578", C["indigo300"]),
                ("gemini-1.5-flash-002", C["blue"], "20 calls", "3,956.4 ms", "946,710", "$0.0828", C["indigo300"]),
                ("gemini-2.0-flash-exp", C["yellow"], "18 calls", "3,132.1 ms", "757,177", "$0.0630", C["indigo300"]),
                ("translation-deployment", C["purple"], "23 calls", "2,903.8 ms", "0 (Chars)", "$3.6911", C["red"]),
                ("speech-to-text-deployment", C["green"], "12 calls", "3,483.0 ms", "0 (Secs)", "$0.8285", C["indigo300"]),
            ]
            rows = ""
            for name, dotc, calls, latency, tok, spend, sc in sample_rows:
                rows += f"""<tr>
                    <td style="color:#fff;"><span class="dot" style="background:{dotc};"></span>{name}</td>
                    <td>{calls}</td><td>{latency}</td><td class="mono">{tok}</td>
                    <td style="text-align:right; color:{sc}; font-weight:700;">{spend}</td></tr>"""

        html(f"""<div class="glass-card" style="padding:0; margin-top:-4px;">
            <table class="vf-table">
                <thead><tr>
                    <th>Endpoint Snapshot (Version)</th><th>Calls</th><th>Mean Latency</th><th>Total Tokens</th>
                    <th style="text-align:right;">Aggregated Spend</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>""")

    # ---- RIGHT COLUMN ----
    with right:
        # Regional distribution
        if df is not None:
            reg = df.groupby("region").size().reset_index(name="calls").sort_values("calls", ascending=False)
            reg_total = reg["calls"].sum()
            reg_items = [(r["region"], int(r["calls"]), r["calls"] / reg_total * 100) for _, r in reg.head(6).iterrows()]
        else:
            reg_items = [("us-central1 (Iowa)", 44, 29.3), ("asia-northeast1 (Tokyo)", 36, 24.0),
                         ("europe-west3 (Frankfurt)", 35, 23.3), ("us-east4 (N. Virginia)", 35, 23.3)]
        bars = ""
        for i, (name, calls, pct) in enumerate(reg_items):
            col = REGION_COLORS[i % len(REGION_COLORS)]
            bars += f"""<div style="margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; font-size:0.72rem; margin-bottom:6px;">
                    <span style="color:#fff; font-weight:600;">{name}</span>
                    <span style="color:{C['gray400']}; font-weight:600;">{calls} calls ({pct:.1f}%)</span>
                </div>
                <div class="bar-track"><div class="bar-fill" style="width:{pct}%; background:{col};"></div></div>
            </div>"""
        html(f"""<div class="glass-card">
            <div class="sec-title">Regional Distribution</div>
            <div class="sec-sub" style="margin-bottom:16px;">Operations balanced across globally distributed endpoints.</div>
            {bars}
        </div>""")

        # Team consumption
        if df is not None:
            team = df.groupby(["associate_id", "cost_centre"]).agg(calls=("cost", "count"), spend=("cost", "sum")).reset_index().sort_values("spend", ascending=False)
            team_items = [(r["associate_id"], r["cost_centre"], int(r["calls"]), r["spend"]) for _, r in team.head(5).iterrows()]
        else:
            team_items = [("soham.ganguly", "CC-AI-RESEARCH", 32, 3.0792), ("priya.sharma", "CC-BFSI-PRODUCTS", 41, 3.0764),
                          ("john.doe", "CC-HEALTHCARE-DEV", 46, 2.4825), ("clara.oswald", "CC-OPERATIONS", 31, 1.3797)]
        max_spend = max((t[3] for t in team_items), default=1)
        arows = ""
        for name, cc, calls, spend in team_items:
            initials = "".join(p[0] for p in name.split(".")[:2]).upper()
            sc = C["red"] if spend > max_spend * 0.7 else C["indigo400"]
            arows += f"""<div class="assoc-row">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div class="assoc-avatar">{initials}</div>
                    <div><div style="font-size:0.74rem; font-weight:700; color:#fff;">{name}</div>
                    <div style="font-size:0.64rem; color:{C['gray500']};">{calls} Calls • {cc}</div></div>
                </div>
                <span style="font-size:0.76rem; font-weight:700; color:{sc};">${spend:.4f}</span>
            </div>"""
        html(f"""<div class="glass-card">
            <div class="sec-title">Team Resource Consumption</div>
            <div class="sec-sub" style="margin-bottom:16px;">Top cost generators and resource owners.</div>
            {arows}
        </div>""")

        # Modality metrics
        html(f"""<div class="glass-card">
            <div class="sec-title">Raw Modality Ingestion</div>
            <div class="sec-sub" style="margin-bottom:16px;">Aggregate media files &amp; durations ingested.</div>
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; text-align:center;">
                <div style="padding:12px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                    <div style="font-size:1.1rem;">🖼️</div>
                    <div style="font-size:0.9rem; font-weight:700; color:#fff;">{total_images:,}</div>
                    <div style="font-size:0.58rem; color:{C['gray500']};">Images</div></div>
                <div style="padding:12px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                    <div style="font-size:1.1rem;">🎵</div>
                    <div style="font-size:0.9rem; font-weight:700; color:#fff;">{total_audio:,.0f}s</div>
                    <div style="font-size:0.58rem; color:{C['gray500']};">Audio</div></div>
                <div style="padding:12px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                    <div style="font-size:1.1rem;">🎬</div>
                    <div style="font-size:0.9rem; font-weight:700; color:#fff;">{total_video:,.0f}s</div>
                    <div style="font-size:0.58rem; color:{C['gray500']};">Video</div></div>
            </div>
        </div>""")

    # Leadership insights
    html(f"""<div class="glass-card">
        <div class="sec-title" style="margin-bottom:14px;">🏆 Leadership FinOps Insights</div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px;">
            <div class="insight" style="background:rgba(52,168,83,0.05); border:1px solid rgba(52,168,83,0.2);">
                <div style="font-size:0.66rem; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">🐷 Prompt Cache Saving Power</div>
                <div style="font-size:0.74rem; color:{C['gray400']}; line-height:1.6;">Ingesting cached tokens separately demonstrated dynamic context caching saved <strong style="color:#fff;">${cache_savings:.4f} USD</strong> on <strong style="color:#fff;">{cached_tokens:,} cached tokens</strong> (GCP's 75% rate reduction).</div>
            </div>
            <div class="insight" style="background:rgba(66,133,244,0.05); border:1px solid rgba(66,133,244,0.2);">
                <div style="font-size:0.66rem; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">⏲ Latency Consistency Analysis</div>
                <div style="font-size:0.74rem; color:{C['gray400']}; line-height:1.6;">Flash-based models showed <strong style="color:#fff;">~22% higher execution speed (~3,132 ms)</strong> over Pro configs (~4,014 ms), validating performance-tier selection.</div>
            </div>
            <div class="insight" style="background:rgba(99,102,241,0.05); border:1px solid rgba(99,102,241,0.2);">
                <div style="font-size:0.66rem; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">🛡 Corporate Audit Readiness</div>
                <div style="font-size:0.74rem; color:{C['gray400']}; line-height:1.6;">Accurate association mapping fully resolves compliance, security policies, and internal project chargeback requirements (NFRs).</div>
            </div>
        </div>
    </div>""")


# ════════════════════════════════════════════════════════════════════
# TAB — TELEMETRY FLOW
# ════════════════════════════════════════════════════════════════════
with tab_flow:
    html("""<div class="glass-card" style="margin-bottom:8px;">
        <div class="sec-title">Dynamic Telemetry Pipeline Inspector</div>
        <div class="sec-sub">Select a pipeline stage to inspect telemetry parsing, transformations, and schema mappings.</div>
    </div>""")

    step = st.radio("Pipeline stage", [
        "01 · Capture — Vertex AI Interceptor",
        "02 · Normalize — GCP Connector",
        "03 · Queue — GCP Pub/Sub Ingestion",
        "04 · Process — FinOps Aggregation",
    ], label_visibility="collapsed")
    active_idx = int(step[1]) - 1  # 0..3

    nodes = [
        ("Step 01: Capture", "Vertex AI Interceptor", "Raw logs captured dynamically from live APIs detailing modality payloads & response times."),
        ("Step 02: Normalize", "GCP Connector parsing", "Normalizes model versions, categorizes modalities (audio/video counts), and formats savings."),
        ("Step 03: Queue", "GCP PubSub Ingestion", "Standardized CanonicalUsageEvent schema updates emitted to live analytical subscriber queues."),
        ("Step 04: Process", "FinOps Aggregation", "DB storage updates project, user identity profiles & departmental cost centres."),
    ]
    ncols = st.columns(4)
    for i, (col, (eyebrow, title, desc)) in enumerate(zip(ncols, nodes)):
        active = "active" if i == active_idx else ""
        accent = C["brand500"] if i == active_idx else C["gray500"]
        with col:
            html(f"""<div class="flow-node {active}">
                <div style="font-size:0.6rem; font-weight:700; color:{accent}; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">{eyebrow}</div>
                <div style="font-size:0.82rem; font-weight:700; color:#fff; margin-bottom:8px;">{title}</div>
                <div style="font-size:0.68rem; color:{C['gray400']}; line-height:1.5;">{desc}</div>
            </div>""")

    inspectors = [
        ("📻 Interceptor Engine Operations", C["indigo400"], "Live GCP Log Interception (PubSubTelemetryWrapper)",
         "The inline wrapper hooks directly into Vertex AI's SDK operations, intercepting execution duration (latency_ms), prompt token volumes, and candidate generation token volume before downstream storage.",
         C["green"], "INFO: [PubSubTelemetryWrapper] Capturing execution log — duration: 3539.63ms, tokens: 5089213, cache_hit: True"),
        ("🖥 Normalization & GCP Connector Extraction", C["blue"], "Processing character, speech & caching layers",
         "GCPConnector isolates model tags (-001, -002, -exp) to allocate precise model-type classifications (Speech, Translation, Multimodal, LLM). It computes prompt-cache pricing dynamically (75% savings on hits).",
         C["indigo400"], "DEBUG: [GCPConnector] Matched Gemini 1.5 Pro version '001'. Extracting multimodal image count: 102"),
        ("🔀 Pub/Sub Payload Assembly", C["yellow"], "Canonical Schema Serialization",
         "Normalized attributes are bundled inside the CanonicalUsageEvent schema and broadcast securely over GCP Pub/Sub with robust contract typing for accurate downstream cost calculations.",
         C["yellow"], "MESSAGE: Enqueueing event ID: evt_9281f3b2 with pricing cost metric attribution payload..."),
        ("🥧 FinOps Aggregations & Billing Ledger", C["green"], "Dynamic Multi-Tenant DB Storage Updates",
         "Downstream subscribers ingest canonical queue records into MongoDB (CanonicalUsageEventDocument & EpisodeCostDocument), generating real-time audit trails of associate cost centres, billing codes, and projects.",
         C["green"], "SUCCESS: Updated Billing Cost Centre 'CC-AI-RESEARCH' total spend by +$3.0792."),
    ]
    badge, bc, title, body, logc, logline = inspectors[active_idx]
    html(f"""<div class="glass-card" style="background:rgba(2,6,12,0.6);">
        <div style="font-size:0.8rem; font-weight:700; color:{bc}; margin-bottom:10px;">{badge}</div>
        <div style="font-size:1.05rem; font-weight:700; color:#fff; margin-bottom:8px;">{title}</div>
        <div style="font-size:0.8rem; color:{C['gray400']}; line-height:1.6; margin-bottom:16px;">{body}</div>
        <div class="mono" style="padding:12px; background:rgba(2,6,12,0.8); border:1px solid {C['border']}; border-radius:8px; font-size:0.72rem; color:{logc};">{logline}</div>
    </div>""")


# ════════════════════════════════════════════════════════════════════
# TAB — PRICING MATRIX
# ════════════════════════════════════════════════════════════════════
with tab_pricing:
    pcol, scol = st.columns([2, 1])

    with pcol:
        pricing_rows = [
            ("Gemini 1.5 Pro", "$1.25 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $2.50)</span>", "$0.3125 <span style='color:#6b7280;font-size:0.6rem;'>(75% off)</span>", True, "$5.00 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $10)</span>", "$2,500.00", "$125 / $2,000"),
            ("Gemini 1.5 Flash", "$0.075 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $0.15)</span>", "$0.01875 <span style='color:#6b7280;font-size:0.6rem;'>(75% off)</span>", True, "$0.30 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $0.60)</span>", "$20.00", "$12.50 / $130"),
            ("Gemini 2.0 Flash", "$0.075 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $0.15)</span>", "$0.01875 <span style='color:#6b7280;font-size:0.6rem;'>(75% off)</span>", True, "$0.30 <span style='color:#6b7280;font-size:0.6rem;'>(&gt;128k: $0.60)</span>", "$20.00", "$12.50 / $130"),
            ("textembedding-gecko", "$0.10", "—", False, "$0.00", "—", "— / —"),
            ("speech-to-text", "—", "—", False, "—", "—", "$400 / —"),
            ("translation", "—", "—", False, "—", "—", "Chars: $20 / 1M"),
        ]
        prows = ""
        for name, prompt, cache, cache_green, cand, img, av in pricing_rows:
            cache_cell = f'<span style="color:{C["green"]}; font-weight:700;">{cache}</span>' if cache_green else cache
            prows += f"""<tr>
                <td style="color:#fff;">{name}</td><td>{prompt}</td><td>{cache_cell}</td>
                <td>{cand}</td><td>{img}</td><td>{av}</td></tr>"""
        html(f"""<div class="glass-card" style="padding:24px 24px 8px;">
            <div class="sec-title">Dynamic Ingest Pricing Matrix</div>
            <div class="sec-sub" style="margin-bottom:14px;">Current GCP billing matrix from VeriForge's GCPConnector tracking database.</div>
            <div style="overflow-x:auto;"><table class="vf-table">
                <thead><tr><th>Model (Service)</th><th>Prompt (1M)</th><th>Caching</th><th>Candidates (1M)</th><th>Images (1M)</th><th>Audio/Video (1M s)</th></tr></thead>
                <tbody>{prows}</tbody>
            </table></div>
        </div>""")

    with scol:
        html("""<div class="glass-card" style="margin-bottom:8px;">
            <div class="sec-title">Live Cost Simulator</div>
            <div class="sec-sub">Evaluate dynamic context-caching benefits on models.</div>
        </div>""")
        sim_model = st.selectbox("Model", ["Gemini 2.0 Flash", "Gemini 1.5 Flash", "Gemini 1.5 Pro"])
        sim_prompt = st.slider("Prompt Tokens", 50_000, 2_000_000, 500_000, 50_000)
        sim_cached = st.slider("Cached Prompt Tokens (75% off)", 0, sim_prompt, min(250_000, sim_prompt), 50_000)
        sim_output = st.slider("Output Candidate Tokens", 5_000, 300_000, 50_000, 5_000)

        if sim_model == "Gemini 1.5 Pro":
            rp, rc, ro = 1.25/1e6, 0.3125/1e6, 5.00/1e6
        else:
            rp, rc, ro = 0.075/1e6, 0.01875/1e6, 0.30/1e6
        std_prompt = sim_prompt - sim_cached
        cost = std_prompt*rp + sim_cached*rc + sim_output*ro
        cost_nocache = sim_prompt*rp + sim_output*ro
        saved = cost_nocache - cost

        html(f"""<div class="glass-card" style="margin-top:-4px;">
            <div style="padding:16px; background:rgba(2,6,12,0.6); border:1px solid {C['border']}; border-radius:12px;">
                <div style="font-size:0.62rem; text-transform:uppercase; letter-spacing:1px; color:{C['gray400']}; font-weight:700;">Estimated Total Operation Cost</div>
                <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:6px;">
                    <span style="font-size:1.9rem; font-weight:800; color:#fff;">${cost:.5f}</span>
                    <span style="font-size:0.74rem; color:{C['green']}; font-weight:600;">Saved ${saved:.5f}</span>
                </div>
            </div>
        </div>""")


# ════════════════════════════════════════════════════════════════════
# TAB — EVENT STREAM (live Pub/Sub feed)
# ════════════════════════════════════════════════════════════════════
with tab_stream:
    if not events:
        html(f"""<div class="glass-card" style="text-align:center; padding:48px 24px;">
            <div style="font-size:2.6rem; margin-bottom:10px;">📭</div>
            <div style="font-size:1rem; color:#fff; font-weight:600;">No events published yet</div>
            <div style="font-size:0.8rem; color:{C['gray400']}; margin-top:6px;">Use the sidebar to <strong>Publish</strong> telemetry, <strong>Pull Live Events</strong> (live mode), or <strong>Load Sample JSONL</strong>.</div>
        </div>""")
    else:
        fc1, fc2 = st.columns(2)
        with fc1:
            fcloud = st.multiselect("Filter by cloud", list(PROVIDER_META.keys()), default=[])
        with fc2:
            fassoc = st.multiselect("Filter by associate", sorted({e["data"]["associate_id"] for e in events}), default=[])

        filtered = events
        if fcloud:
            filtered = [e for e in filtered if e["data"]["cloud"] in fcloud]
        if fassoc:
            filtered = [e for e in filtered if e["data"]["associate_id"] in fassoc]

        html(f"""<div style="font-size:0.72rem; color:{C['gray500']}; margin:6px 0 12px;">Showing {min(len(filtered),60)} of {len(filtered)} matching events ({len(events)} total)</div>""")

        for ev in filtered[:60]:
            d = ev["data"]
            ru = d["request_units"]
            cloud = d["cloud"]
            cc = PROVIDER_COLORS.get(cloud, C["brand500"])
            tok = f"{ru.get('total_tokens', ru.get('input_tokens', 0)):,} tok" if ("total_tokens" in ru or "input_tokens" in ru) else ""
            aud = f"{ru.get('input_audio_seconds', 0):.1f}s audio" if "input_audio_seconds" in ru else ""
            chars = f"{ru.get('input_characters', 0):,} chars" if "input_characters" in ru else ""
            usage = " · ".join(filter(None, [tok, aud, chars])) or "—"
            cached_html = f'<span style="color:{C["green"]};">💾 {ru.get("cached_tokens", 0):,} cached</span>' if ru.get("cached_tokens") else ""
            html(f"""<div class="glass-card" style="padding:12px 16px; margin-bottom:8px; border-left:3px solid {cc};">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <span style="background:{cc}22; color:{cc}; border:1px solid {cc}55; font-size:0.6rem; font-weight:700; padding:2px 9px; border-radius:20px; text-transform:uppercase;">{cloud}</span>
                    <span style="color:#fff; font-weight:600; font-size:0.8rem;">{d['service']}</span>
                    <span style="color:{C['gray500']};">·</span>
                    <span style="color:{C['gray400']}; font-size:0.78rem;">{d['operation']}</span>
                    <span style="color:{C['gray500']};">·</span>
                    <span style="color:{C['gray400']}; font-size:0.7rem;">{d.get('model_type','—')} / v{d.get('model_version','?')}</span>
                    <span style="margin-left:auto; color:{C['brand500']}; font-weight:700;">${d['cost']:.5f}</span>
                </div>
                <div style="display:flex; gap:14px; margin-top:7px; font-size:0.68rem; color:{C['gray500']}; flex-wrap:wrap;">
                    <span>👤 {d['associate_id']}</span><span>🏷 {d['cost_centre']}</span>
                    <span>📁 {d['project_code']}</span><span>🌍 {d['region']}</span>
                    <span>⏱ {d.get('latency_ms','—')} ms</span><span>📊 {usage}</span>{cached_html}
                    <span class="mono" style="margin-left:auto; color:#374151;">{ev['message_id']} · {d['timestamp']}</span>
                </div>
            </div>""")


# ════════════════════════════════════════════════════════════════════
# TAB — CODE UPDATES
# ════════════════════════════════════════════════════════════════════
with tab_code:
    cc1, cc2 = st.columns(2)
    with cc1:
        html(f"""<div class="glass-card" style="padding-bottom:8px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:0.6rem; font-weight:600; padding:2px 8px; border-radius:6px; background:rgba(99,102,241,0.1); color:{C['indigo300']}; border:1px solid rgba(99,102,241,0.2);">Pydantic Schema</span>
                <span class="mono" style="font-size:0.7rem; color:{C['gray400']};">src/schemas.py</span>
            </div>
            <div class="sec-title">Canonical Event Updates</div>
        </div>""")
        st.code("""    cost: float = Field(
        ..., description="Calculated cost of the operation in USD (float)"
    )
+   model_version: Optional[str] = Field(
+       default=None,
+       description="Specific model version/snapshot tag (e.g. '001','002','exp')"
+   )
+   model_type: Optional[str] = Field(
+       default=None,
+       description="General category of the model (e.g. 'LLM','Multimodal')"
+   )
+   latency_ms: Optional[int] = Field(
+       default=None,
+       description="API execution latency in milliseconds"
+   )""", language="python")

    with cc2:
        html(f"""<div class="glass-card" style="padding-bottom:8px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:0.6rem; font-weight:600; padding:2px 8px; border-radius:6px; background:rgba(52,168,83,0.1); color:{C['green']}; border:1px solid rgba(52,168,83,0.2);">MongoDB Schema</span>
                <span class="mono" style="font-size:0.7rem; color:{C['gray400']};">src/db_schemas.py</span>
            </div>
            <div class="sec-title">Database Document Schemas</div>
        </div>""")
        st.code("""    cost: float = Field(..., description="Call execution cost in USD")
    duration_ms: int = Field(..., description="Inference API latency")
+   model_version: Optional[str] = Field(default=None, description="Model snapshot")
+   model_type: Optional[str] = Field(default=None, description="Model category")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
# ---------------------------------------------------------------
    request_units: Dict[str, Any] = Field(..., description="Metrics dict")
    cost: float = Field(..., description="Cost of operation in USD")
+   model_version: Optional[str] = Field(default=None, description="Model snapshot")
+   model_type: Optional[str] = Field(default=None, description="Model category")
+   latency_ms: Optional[int] = Field(default=None, description="Execution latency")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)""", language="python")

    html(f"""<div class="glass-card">
        <div class="sec-title" style="font-size:0.9rem;">Internal Framework Interceptor Upgrades</div>
        <div class="sec-sub" style="margin-bottom:14px;">Changes in <span class="mono">src/connectors/gcp.py</span> and <span class="mono">src/vertex_telemetry.py</span> isolate and store dynamic multimodal counts:</div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px;">
            <div style="padding:14px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                <div style="font-size:0.74rem; font-weight:700; color:#fff; margin-bottom:6px;">Split Model Identifiers</div>
                <div style="font-size:0.68rem; color:{C['gray400']}; line-height:1.5;">Extracts model tag suffixes (-001, -002, -exp) dynamically from pipeline strings for clean model tracking.</div>
            </div>
            <div style="padding:14px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                <div style="font-size:0.74rem; font-weight:700; color:#fff; margin-bottom:6px;">Calculate Prompt Savings</div>
                <div style="font-size:0.68rem; color:{C['gray400']}; line-height:1.5;">Extracts cached_tokens within GCP logs and recalculates pricing at a 75% rate reduction.</div>
            </div>
            <div style="padding:14px; background:rgba(17,24,39,0.6); border:1px solid {C['border']}; border-radius:12px;">
                <div style="font-size:0.74rem; font-weight:700; color:#fff; margin-bottom:6px;">Trace Multimodal Dimensions</div>
                <div style="font-size:0.68rem; color:{C['gray400']}; line-height:1.5;">Captures input_images, input_audio_seconds, and input_video_seconds for accurate sub-component pricing.</div>
            </div>
        </div>
    </div>""")


# ── Footer ────────────────────────────────────────────────────────────────────
html(f"""<div style="text-align:center; padding:20px 0 8px; color:#374151; font-size:0.68rem; letter-spacing:0.5px;">
    VeriForge Ops · Vertex AI Telemetry &amp; FinOps Engine · Cognizant Technology Solutions
    &nbsp;·&nbsp; Built with Streamlit · GCP Pub/Sub
</div>""")
