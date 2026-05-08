"""
BatteryDock — Minimal EV Battery Intelligence Dashboard
F1 Telemetry-inspired monochrome UI with live polling from FastAPI.
"""

import sys
import time
import json
import urllib.request
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt

# ── Force UTF-8 on Windows ─────────────────────────────────────
for stream in (sys.stdout, sys.stderr):
    if stream and hasattr(stream, "reconfigure") and getattr(stream, "encoding", "utf-8").lower() != "utf-8":
        stream.reconfigure(encoding="utf-8")

# ── Page Configuration ─────────────────────────────────────────
st.set_page_config(
    page_title="BatteryDock | Telemetry",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS for F1 Telemetry Styling ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

/* Base Theme overrides */
html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
    background-color: #050505 !important;
    color: #e0e0e0;
}

/* Hide standard Streamlit header/footer */
header {visibility: hidden;}
footer {visibility: hidden;}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #fff !important;
}

/* Glassmorphism Monochrome Cards */
.telemetry-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    padding: 20px;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.telemetry-card:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.04);
}
/* Subtle scanning line animation on hover */
.telemetry-card::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 50%; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent);
    transition: 0.5s;
}
.telemetry-card:hover::after {
    left: 100%;
    transition: 0.8s ease-in-out;
}

.card-title {
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
}
.card-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}
.card-unit {
    font-size: 1rem;
    color: #555;
    font-weight: 400;
    margin-left: 4px;
}

/* Progress Bars */
.progress-bg {
    background: #1a1a1a;
    height: 2px;
    width: 100%;
    margin-top: 12px;
}
.progress-fill {
    background: #fff;
    height: 100%;
    transition: width 0.5s ease-in-out;
}

/* Live Indicator */
.live-wrapper {
    display: flex;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #888;
    letter-spacing: 1px;
}
.live-indicator {
    height: 6px;
    width: 6px;
    background-color: #fff;
    border-radius: 50%;
    display: inline-block;
    animation: blink 1.2s infinite ease-in-out;
    margin-right: 8px;
}
@keyframes blink {
    0% { opacity: 0.1; }
    50% { opacity: 1; box-shadow: 0 0 6px #fff; }
    100% { opacity: 0.1; }
}

/* Terminal styled boxes */
.terminal-box {
    border-left: 2px solid #333;
    padding-left: 15px;
    margin-top: 10px;
}
.terminal-text {
    color: #aaa;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    margin-bottom: 6px;
    line-height: 1.4;
}
.terminal-critical { color: #fff; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Session State for Historical Data ──────────────────────────
if 'history' not in st.session_state:
    st.session_state.history = {
        'time': [],
        'soh': [],
        'temperature': [],
        'voltage': [],
        'degradation': []
    }

# ── API Fetch Function ─────────────────────────────────────────
def fetch_live_data():
    try:
        req = urllib.request.Request("http://localhost:8000/live-data")
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read())
    except Exception as e:
        return None

# ── UI Components ──────────────────────────────────────────────
def render_metric_card(title, value, unit="", progress=None):
    prog_html = ""
    if progress is not None:
        # Clamp progress between 0 and 100
        p_val = max(0, min(100, progress))
        prog_html = f'<div class="progress-bg"><div class="progress-fill" style="width: {p_val}%"></div></div>'
    
    html = f"""
    <div class="telemetry-card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}<span class="card-unit">{unit}</span></div>
        {prog_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def remove_emojis(text):
    """Strips emojis to maintain the serious F1 engineering aesthetic."""
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def render_f1_chart(df, y_col, title):
    """Renders a monochrome minimal Altair chart with line and points."""
    if len(df) < 2:
        st.markdown(f'<div style="height:180px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(255,255,255,0.05); color:#333; font-family:JetBrains Mono; font-size:0.7rem; letter-spacing:2px;">[ INITIALIZING TELEMETRY BUFFER... ]</div>', unsafe_allow_html=True)
        return

    # Base chart encoding
    base = alt.Chart(df).encode(
        x=alt.X('time:T', axis=alt.Axis(
            title='', labels=True, grid=False, labelColor="#444", tickColor="#222", 
            format='%H:%M:%S', labelFlush=True
        )),
        y=alt.Y(f'{y_col}:Q', scale=alt.Scale(zero=False, padding=20), 
                axis=alt.Axis(title='', gridColor="#111", tickColor="#222", domainColor="#222", labelColor="#666", labelFont="JetBrains Mono"))
    )
    
    # Combined Line and Points for F1 telemetry feel
    line = base.mark_line(color="#ffffff", strokeWidth=2, interpolate='monotone', opacity=0.8)
    points = base.mark_point(color="#ffffff", size=20, filled=True, opacity=1.0)
    
    chart = (line + points).properties(
        height=180, 
    ).configure_view(
        strokeWidth=0
    )
    
    st.markdown(f'<div style="font-family: JetBrains Mono; font-size: 0.7rem; color: #666; letter-spacing: 2px; margin-bottom: 5px; margin-top: 10px;">{title}</div>', unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=True)

# ── Main Dashboard Layout ──────────────────────────────────────

# ── Hero Section (Formula E Theme) ──────────────────────────
st.markdown("<div style='margin-bottom: 40px;'>", unsafe_allow_html=True)
hero_col1, hero_col2 = st.columns([3, 2])

with hero_col1:
    st.markdown("""
        <h1 style='font-size: 3.5rem; line-height: 1; margin-bottom: 10px;'>ELECTRIFYING<br><span style='color: #666;'>PRECISION.</span></h1>
        <p style='font-family: JetBrains Mono; color: #888; letter-spacing: 1px; font-size: 0.9rem; max-width: 400px;'>
            Formula E GEN3 Battery Intelligence System. Advanced telemetry for the next generation of electric motorsport.
        </p>
        <div style='height: 2px; width: 60px; background: #fff; margin: 25px 0;'></div>
        <div style='font-family: JetBrains Mono; font-size: 0.7rem; color: #444; letter-spacing: 3px;'>[ MISSION CONTROL // PADDOCK ACCESS ]</div>
    """, unsafe_allow_html=True)

with hero_col2:
    # Using the generated Formula E image
    st.image("C:\\Users\\hmura\\.gemini\\antigravity\\brain\\4aaed9f4-13ec-4505-ad7d-b83a70291297\\formula_e_hero_monochrome_1778264359675.png", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 1px; background: #222; margin: 15px 0 30px 0;'></div>", unsafe_allow_html=True)

# Fetch Data
data = fetch_live_data()

if not data:
    st.error("SYS_ERR: UNABLE TO CONNECT TO TELEMETRY STREAM (http://localhost:8000/live-data)")
    st.stop()

# Update History
current_time = datetime.now()
st.session_state.history['time'].append(current_time)
st.session_state.history['soh'].append(data['soh_prediction'])
st.session_state.history['temperature'].append(data['temperature'])
st.session_state.history['voltage'].append(data['voltage'])
st.session_state.history['degradation'].append(data['degradation_percentage'])

# Keep only last 60 points (approx 2 minutes if refreshing every 2s)
for key in st.session_state.history:
    st.session_state.history[key] = st.session_state.history[key][-60:]

history_df = pd.DataFrame(st.session_state.history)
history_df['time'] = pd.to_datetime(history_df['time'])

# 1. Main Telemetry Cards (AI Outputs)
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card("SYS_HEALTH // SOH", f"{data['soh_prediction']:.1f}", "%", progress=data['soh_prediction'])
with col2:
    render_metric_card("WEAR // DEGRADATION", f"{data['degradation_percentage']:.1f}", "%", progress=data['degradation_percentage'])
with col3:
    render_metric_card("EST // CYCLES", f"{data['estimated_cycle_aging']}")
with col4:
    cond = str(data['battery_condition']).upper()
    render_metric_card("SYS // CONDITION", cond)

# 2. Live Sensor Panel
st.markdown("<div style='font-family: JetBrains Mono; font-size: 0.7rem; color: #444; letter-spacing: 2px; margin: 20px 0 10px 0;'>GEN3 POWER UNIT TELEMETRY</div>", unsafe_allow_html=True)
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
with sc1:
    render_metric_card("ERS // VOLT", f"{data['voltage']:.2f}", "V")
with sc2:
    render_metric_card("MGU-K // CURR", f"{data['current']:.2f}", "A")
with sc3:
    render_metric_card("THERMAL // CORE", f"{data['temperature']:.1f}", "°C")
with sc4:
    render_metric_card("SOC // RESERVE", f"{data['battery_percentage']:.1f}", "%")
with sc5:
    render_metric_card("ENV // HUMD", f"{data['humidity']:.1f}", "%")

# 3. Charts Section
st.markdown("<div style='height: 1px; background: #111; margin: 20px 0 25px 0;'></div>", unsafe_allow_html=True)
ch1, ch2 = st.columns(2)
with ch1:
    render_f1_chart(history_df, 'soh', 'SOH TREND [%]')
with ch2:
    render_f1_chart(history_df, 'temperature', 'THERMAL TREND [°C]')

ch3, ch4 = st.columns(2)
with ch3:
    render_f1_chart(history_df, 'voltage', 'VOLTAGE TREND [V]')
with ch4:
    render_f1_chart(history_df, 'degradation', 'DEGRADATION ACCUMULATION [%]')

st.markdown("<div style='height: 1px; background: #111; margin: 30px 0 20px 0;'></div>", unsafe_allow_html=True)

# 4. Alerts & Recommendations
al1, al2 = st.columns(2)

with al1:
    st.markdown("<div style='font-family: JetBrains Mono; font-size: 0.7rem; color: #666; letter-spacing: 2px; margin-bottom: 10px;'>ACTIVE ALERTS</div>", unsafe_allow_html=True)
    alerts = data.get('alerts', [])
    html = '<div class="terminal-box">'
    if not alerts:
        html += '<div class="terminal-text">[ SYS_NOMINAL : NO ACTIVE ALERTS ]</div>'
    for a in alerts:
        clean_msg = remove_emojis(a["message"]).upper()
        prefix = "[ WRN ]" if a['level'] == 'warning' else "[ CRT ]"
        css_class = "terminal-critical" if a['level'] == 'critical' else "terminal-text"
        html += f'<div class="{css_class}" style="margin-bottom: 8px;">> {prefix} {clean_msg}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

with al2:
    st.markdown("<div style='font-family: JetBrains Mono; font-size: 0.7rem; color: #666; letter-spacing: 2px; margin-bottom: 10px;'>AI RECOMMENDATIONS</div>", unsafe_allow_html=True)
    recs = data.get('recommendations', [])
    html = '<div class="terminal-box">'
    for r in recs:
        clean_rec = remove_emojis(r)
        html += f'<div class="terminal-text">> {clean_rec}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ── Auto-Refresh Logic ─────────────────────────────────────────
# Wait 2 seconds and rerun to fetch new live data
time.sleep(2)
st.rerun()
