import os
import time
import logging
import random
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# 1. SETUP & CONFIGURATION
# ─────────────────────────────────────────────────────────────────

import requests

# ====================================================================
# ESP32 CONFIGURATION
# Paste the ESP32 IP address below. This becomes the single source of truth.
# ====================================================================
ESP32_API_URL = "http://10.208.217.123/api/data"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("batterydock")

app = FastAPI(
    title="BatteryDock AI Backend",
    description="Production-grade AI backend for EV battery telemetry intelligence.",
    version="4.1.0"
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# 2. MODEL LOADING
# ─────────────────────────────────────────────────────────────────

logger.info("═══════════════════════════════════════")
logger.info("  BatteryDock AI Engine v4.1 Starting  ")
logger.info("═══════════════════════════════════════")

soh_model = None
degradation_model = None
rul_model = None

try:
    soh_model = joblib.load("soh_model.pkl")
    degradation_model = joblib.load("degradation_model.pkl")
    rul_model = joblib.load("rul_model.pkl")
    logger.info("✅ All 3 ML models loaded successfully.")
except Exception as e:
    logger.error(f"❌ Model loading failed: {e}")
    logger.warning("⚠️ Backend will use engineering fallback calculations.")

# ─────────────────────────────────────────────────────────────────
# 3. PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────

class TelemetryInput(BaseModel):
    """Telemetry payload from React frontend sliders.
    Uses cycle_num / capacity_ah to match model training schema."""
    voltage: float
    current: float
    temperature: float
    battery_percentage: float
    humidity: float
    cycle_num: int
    capacity_ah: float


class PredictionResponse(BaseModel):
    """JSON response sent back to the frontend."""
    soh_prediction: float
    degradation_percentage: float
    estimated_rul: int
    battery_condition: str
    alerts: List[str]
    recommendations: List[str]

# ─────────────────────────────────────────────────────────────────
# 4. IN-MEMORY LIVE TELEMETRY STORAGE
#
# This is the bridge between ESP32 hardware and the React frontend.
# When ESP32 POSTs to /telemetry, the data is stored here.
# When the frontend GETs /latest, it reads from here.
#
# This creates an async pipeline:
#   ESP32 → POST /telemetry → latestTelemetry + latestPrediction
#   React → GET /latest → reads latestTelemetry + latestPrediction
# ─────────────────────────────────────────────────────────────────

# Latest telemetry received from ESP32 (None until first ESP32 POST)
latest_telemetry: Optional[dict] = None

# Latest AI prediction computed from ESP32 data
latest_prediction: Optional[dict] = None

# Telemetry history — stores last 50 data points for trend analysis
telemetry_history: List[dict] = []

# Connection status tracking
esp32_connected = False
last_esp32_timestamp: Optional[str] = None

# ─────────────────────────────────────────────────────────────────
# 5. BUSINESS LOGIC
# ─────────────────────────────────────────────────────────────────

def evaluate_condition(soh: float) -> str:
    """Map SOH to human-readable condition."""
    if soh > 85:
        return "Healthy"
    elif soh >= 70:
        return "Moderate"
    else:
        return "Critical"

def generate_alerts(data: TelemetryInput, deg: float) -> List[str]:
    """Generate alerts based on sensor thresholds."""
    alerts = []
    if data.temperature > 45:
        alerts.append("OVERHEATING WARNING: Thermal runaway risk detected.")
    elif data.temperature > 35:
        alerts.append("THERMAL WARNING: Elevated operating temperature.")
    if data.humidity > 80:
        alerts.append("MOISTURE WARNING: High humidity environment.")
    if data.voltage < 3.2:
        alerts.append("LOW VOLTAGE WARNING: Potential cell damage.")
    if data.current > 4:
        alerts.append("HIGH CURRENT WARNING: Aggressive discharge detected.")
    if deg > 30:
        alerts.append("DEGRADATION WARNING: Battery requires service.")
    return alerts

def generate_recommendations(data: TelemetryInput) -> List[str]:
    """Generate actionable recommendations."""
    recs = []
    if data.temperature > 35:
        recs.append("Reduce thermal stress. Ensure proper cooling system operation.")
    if data.current > 3:
        recs.append("Reduce sustained high current draw to extend cycle life.")
    if data.battery_percentage < 20:
        recs.append("Avoid deep discharge. Charge battery soon.")
    if data.humidity > 70:
        recs.append("Inspect sealing system. Avoid moisture exposure.")
    if data.voltage < 3.5:
        recs.append("Voltage approaching critical threshold. Monitor closely.")
    if not recs:
        recs.append("Battery operating within safe parameters. Maintain 20–80% charge window.")
    return recs

# ─────────────────────────────────────────────────────────────────
# 6. AI PREDICTION CORE
# ─────────────────────────────────────────────────────────────────

def run_prediction(data: TelemetryInput) -> dict:
    """
    Core prediction pipeline.
    NEVER crashes — always returns valid JSON.
    """
    try:
        # Feature engineering for the trained model
        normalized_cap = data.capacity_ah / 1.0
        feature_df = pd.DataFrame([{
            "cycle_number": data.cycle_num,
            "capacity_ah": data.capacity_ah,
            "normalized_capacity": normalized_cap,
        }])

        if soh_model and degradation_model and rul_model:
            base_soh = float(soh_model.predict(feature_df)[0])
            base_deg = float(degradation_model.predict(feature_df)[0])
            rul = int(rul_model.predict(feature_df)[0])

            # Real-time physics corrections from live sensor telemetry
            temp_stress = max(0, (data.temperature - 25) * 0.15)
            current_stress = data.current * 0.3
            voltage_dip = max(0, (4.2 - data.voltage)) * 2.0
            humidity_penalty = max(0, (data.humidity - 60) * 0.05)
            soc_penalty = max(0, (50 - data.battery_percentage) * 0.02)

            total_penalty = temp_stress + current_stress + voltage_dip + humidity_penalty + soc_penalty

            soh = max(0.0, min(100.0, base_soh - total_penalty))
            deg = max(0.0, min(100.0, base_deg + total_penalty))
            rul = max(0, int(rul - total_penalty * 5))
        else:
            logger.warning("Using fallback calculation (no ML models).")
            soh = max(0, 100.0 - (data.cycle_num * 0.1) - (data.temperature - 25) * 0.15)
            deg = 100.0 - soh
            rul = max(0, 500 - data.cycle_num)

        soh = round(max(0.0, min(100.0, soh)), 2)
        deg = round(max(0.0, min(100.0, deg)), 2)
        rul = max(0, rul)

        condition = evaluate_condition(soh)
        alerts = generate_alerts(data, deg)
        recs = generate_recommendations(data)

        response = {
            "soh_prediction": soh,
            "degradation_percentage": deg,
            "estimated_rul": rul,
            "battery_condition": condition,
            "alerts": alerts,
            "recommendations": recs,
        }

        logger.info(f"Prediction: SOH={soh}%, Deg={deg}%, RUL={rul}, Cond={condition}")
        return response

    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        return {
            "soh_prediction": 0.0,
            "degradation_percentage": 100.0,
            "estimated_rul": 0,
            "battery_condition": "Critical",
            "alerts": ["SYSTEM ERROR: AI inference failed."],
            "recommendations": ["Check backend logs. Restart server."],
        }

# ─────────────────────────────────────────────────────────────────
# 7. API ROUTES
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Root health check."""
    return {
        "status": "BatteryDock AI Backend Online",
        "version": "4.1",
        "models_loaded": all([soh_model, degradation_model, rul_model]),
        "esp32_connected": esp32_connected,
        "last_esp32_data": last_esp32_timestamp,
        "history_length": len(telemetry_history),
        "timestamp": datetime.now().isoformat(),
    }

# ── ENDPOINT 1: Frontend slider prediction ──────────────────────

@app.post("/predict", response_model=PredictionResponse, tags=["AI Inference"])
def predict_health(data: TelemetryInput):
    """
    Called by React frontend when sliders change.
    Accepts TelemetryInput with cycle_num / capacity_ah field names.
    """
    logger.info(f"📡 /predict: V={data.voltage}, A={data.current}, T={data.temperature}°C, Cycle={data.cycle_num}, Cap={data.capacity_ah}Ah")
    return run_prediction(data)

# ── ENDPOINT 2: ESP32 telemetry receiver ─────────────────────────

@app.post("/telemetry", tags=["ESP32 Hardware"])
def receive_telemetry(data: TelemetryInput):
    """
    DEDICATED ESP32 TELEMETRY RECEIVER.
    
    This is the endpoint your existing ESP32 hardware POSTs to.
    
    Flow:
      1. Receive JSON payload from ESP32
      2. Validate payload (Pydantic handles this)
      3. Convert to internal TelemetryInput format
      4. Run AI prediction
      5. Store latest telemetry + prediction in memory
      6. Append to history
      7. Return prediction response to ESP32
    
    ESP32 payload format:
    {
      "voltage": 3.9,
      "current": 2.1,
      "temperature": 31,
      "battery_percentage": 82,
      "humidity": 45,
      "cycle_num": 120,
      "capacity_ah": 0.91
    }
    """
    global latest_telemetry, latest_prediction, esp32_connected, last_esp32_timestamp

    logger.info("═══════════════════════════════════════")
    logger.info(f"📡 ESP32 TELEMETRY RECEIVED:")
    logger.info(f"   Voltage:     {data.voltage} V")
    logger.info(f"   Current:     {data.current} A")
    logger.info(f"   Temperature: {data.temperature} °C")
    logger.info(f"   Battery %:   {data.battery_percentage} %")
    logger.info(f"   Humidity:    {data.humidity} %")
    logger.info(f"   Cycle:       {data.cycle_num}")
    logger.info(f"   Capacity:    {data.capacity_ah} Ah")

    # Mark ESP32 as connected
    esp32_connected = True
    last_esp32_timestamp = datetime.now().isoformat()

    # Convert ESP32 field names → internal model field names
    internal_data = TelemetryInput(
        voltage=data.voltage,
        current=data.current,
        temperature=data.temperature,
        battery_percentage=data.battery_percentage,
        humidity=data.humidity,
        cycle_num=data.cycle_num,
        capacity_ah=data.capacity_ah,
    )

    # Run AI prediction
    prediction = run_prediction(internal_data)

    # Store latest telemetry (what ESP32 sent)
    latest_telemetry = {
        "voltage": data.voltage,
        "current": data.current,
        "temperature": data.temperature,
        "battery_percentage": data.battery_percentage,
        "humidity": data.humidity,
        "cycle_num": data.cycle_num,
        "capacity_ah": data.capacity_ah,
        "timestamp": last_esp32_timestamp,
    }

    # Store latest prediction
    latest_prediction = prediction

    # Append to history (keep last 50 entries)
    history_entry = {**latest_telemetry, **prediction, "time": datetime.now().strftime("%H:%M:%S")}
    telemetry_history.append(history_entry)
    if len(telemetry_history) > 50:
        telemetry_history.pop(0)

    logger.info(f"✅ Prediction: SOH={prediction['soh_prediction']}%, Condition={prediction['battery_condition']}")
    logger.info(f"📊 History length: {len(telemetry_history)}")
    logger.info("═══════════════════════════════════════")

    return prediction

# ── ENDPOINT 3: Frontend auto-sync (polls this every 2s) ────────

@app.get("/latest", tags=["Live Sync"])
def get_latest():
    """
    FRONTEND AUTO-SYNC ENDPOINT.
    
    The React frontend polls this endpoint every 2 seconds.
    This endpoint actively fetches from the ESP32 IP, runs the AI model,
    and returns the merged result.
    """
    global latest_telemetry, latest_prediction, esp32_connected, last_esp32_timestamp
    try:
        # 1. Fetch real hardware data from ESP32 IP
        response = requests.get(ESP32_API_URL, timeout=2.0)
        response.raise_for_status()
        raw_data = response.json()
        
        # 2. Map payload for backend
        internal_data = TelemetryInput(
            voltage=raw_data.get('voltage', 0.0),
            current=raw_data.get('current', 0.0),
            temperature=raw_data.get('temperature', 0.0),
            battery_percentage=raw_data.get('battery_percentage', 0.0),
            humidity=raw_data.get('humidity', 0.0),
            cycle_num=raw_data.get('cycle_num', raw_data.get('cycle', 0)),
            capacity_ah=raw_data.get('capacity_ah', raw_data.get('capacity', 0.0)),
        )

        # 3. Run AI prediction
        prediction = run_prediction(internal_data)

        # 4. Update memory state
        esp32_connected = True
        last_esp32_timestamp = datetime.now().isoformat()
        
        latest_telemetry = {
            "voltage": internal_data.voltage,
            "current": internal_data.current,
            "temperature": internal_data.temperature,
            "battery_percentage": internal_data.battery_percentage,
            "humidity": internal_data.humidity,
            "cycle_num": internal_data.cycle_num,
            "capacity_ah": internal_data.capacity_ah,
            "timestamp": last_esp32_timestamp,
        }
        latest_prediction = prediction

        # 5. Append to history (keep last 50 entries)
        history_entry = {**latest_telemetry, **prediction, "time": datetime.now().strftime("%H:%M:%S")}
        telemetry_history.append(history_entry)
        if len(telemetry_history) > 50:
            telemetry_history.pop(0)

        logger.info(f"📤 /latest (ESP32 FETCH) → SOH={prediction['soh_prediction']}%, ESP32 connected")
        return {**latest_telemetry, **prediction}

    except Exception as e:
        logger.warning(f"❌ Could not fetch from ESP32: {e}")
        esp32_connected = False
        # Fall back to returning memory state if available, or status
        if latest_telemetry and latest_prediction:
            result = {**latest_telemetry, **latest_prediction}
            return result
        else:
            return {
                "status": "waiting_for_esp32",
                "message": f"No ESP32 telemetry received yet. Checked {ESP32_API_URL}.",
                "esp32_connected": False,
            }

# ── ENDPOINT 4: Full telemetry history ───────────────────────────

@app.get("/history", tags=["Live Sync"])
def get_history():
    """
    Returns the full telemetry history array.
    Used by the frontend to populate charts on initial load.
    """
    return {
        "history": telemetry_history,
        "count": len(telemetry_history),
        "esp32_connected": esp32_connected,
    }

# ─────────────────────────────────────────────────────────────────
# 8. LIVE DATA SIMULATION (when ESP32 hardware is not connected)
# ─────────────────────────────────────────────────────────────────

sim_state = {
    "voltage": 4.1,
    "current": 2.2,
    "temperature": 25.0,
    "battery_percentage": 100.0,
    "humidity": 45.0,
    "cycle_num": 10,
    "capacity_ah": 1.02,
}

@app.get("/live-data", tags=["Simulation"])
def get_live_data():
    """
    Simulates ESP32 telemetry when hardware is not connected.
    Used by frontend LIVE FEED mode for demo/testing.
    """
    global sim_state

    sim_state["voltage"] = max(3.0, min(4.2, sim_state["voltage"] - random.uniform(0.001, 0.01)))
    sim_state["current"] = max(0.5, min(8.0, sim_state["current"] + random.uniform(-0.5, 0.5)))
    sim_state["temperature"] = max(15.0, min(65.0, sim_state["temperature"] + random.uniform(-0.5, 0.8)))
    sim_state["battery_percentage"] = max(0.0, sim_state["battery_percentage"] - random.uniform(0.01, 0.15))
    sim_state["humidity"] = max(30.0, min(90.0, sim_state["humidity"] + random.uniform(-1.0, 1.0)))
    sim_state["cycle_num"] += 1
    sim_state["capacity_ah"] = max(0.5, sim_state["capacity_ah"] - random.uniform(0.0001, 0.001))

    input_data = TelemetryInput(
        voltage=round(sim_state["voltage"], 2),
        current=round(sim_state["current"], 2),
        temperature=round(sim_state["temperature"], 2),
        battery_percentage=round(sim_state["battery_percentage"], 1),
        humidity=round(sim_state["humidity"], 1),
        cycle_num=sim_state["cycle_num"],
        capacity_ah=round(sim_state["capacity_ah"], 4),
    )

    prediction = run_prediction(input_data)

    result = input_data.model_dump()
    result.update(prediction)

    return result
