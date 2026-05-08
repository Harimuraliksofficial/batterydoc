"""
╔══════════════════════════════════════════════════════════════════╗
║       EV Battery AI — FastAPI Inference Backend                  ║
║  Serves battery health predictions via REST API                  ║
║  Optimised for ESP32 real-time telemetry                         ║
╚══════════════════════════════════════════════════════════════════╝

HOW TO RUN:
    uvicorn server:app --reload --host 0.0.0.0 --port 8000

ENDPOINTS:
    GET  /           → health-check / welcome
    GET  /health     → server readiness probe
    POST /predict    → battery health prediction

ARCHITECTURE NOTES (for future scaling):
    • ESP32 Integration   → Receives raw telemetry (voltage, temp, humidity, etc.)
    • AI Inference        → Translates telemetry into aging indicators before feeding to AI
    • NMC Battery Scaling → Swap .pkl models trained on NMC chemistry data
    • Formula E Systems   → Adjust telemetry stress mapping for extreme performance
    • React Frontend      → Call /predict from fetch()/axios; CORS enabled
"""

# ─────────────────────────────────────────────────────────────────
# STEP 0 ▸ Imports
# ─────────────────────────────────────────────────────────────────
# FastAPI      → modern async web framework for building APIs
# Pydantic     → data validation (ensures correct JSON types)
# joblib       → loads the trained .pkl model files
# numpy        → numerical arrays the model expects
# CORSMiddleware → allows React / browser frontends to call the API
# ─────────────────────────────────────────────────────────────────
import pathlib
import random
from typing import List

import numpy as np
import joblib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────
# STEP 1 ▸ File paths
# ─────────────────────────────────────────────────────────────────
# All paths are relative to this file so the project is portable.
BASE = pathlib.Path(__file__).parent
SOH_MODEL_PATH  = BASE / "battery_model.pkl"
RISK_MODEL_PATH = BASE / "battery_risk_model.pkl"
META_PATH       = BASE / "battery_model_meta.pkl"

# ─────────────────────────────────────────────────────────────────
# STEP 2 ▸ Load trained models (once at startup)
# ─────────────────────────────────────────────────────────────────
# joblib.load() deserialises the trained RandomForestRegressor
# objects that were saved during training.
soh_model  = joblib.load(SOH_MODEL_PATH)
risk_model = joblib.load(RISK_MODEL_PATH)
meta       = joblib.load(META_PATH)

# Feature order the models were trained on:
#   ['voltage', 'temperature', 'capacity', 'cycle', 'rul']
FEATURE_NAMES = meta["feature_names"]
print(f"✅  Models loaded. Expected internal features: {FEATURE_NAMES}")

# ─────────────────────────────────────────────────────────────────
# STEP 3 ▸ Create FastAPI app
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="EV Battery AI API",
    description=(
        "Production-grade inference backend for EV battery health prediction. "
        "Accepts ESP32 sensor readings and returns SOH, degradation percentage, "
        "estimated cycle aging, RUL, alerts, and recommendations."
    ),
    version="2.0.0",
    docs_url="/docs",       # Swagger UI  → http://localhost:8000/docs
    redoc_url="/redoc",     # ReDoc       → http://localhost:8000/redoc
)

# ── CORS — allow any origin so React / ESP32 / mobile can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# STEP 4 ▸ Pydantic schemas (request / response validation)
# ─────────────────────────────────────────────────────────────────
# Pydantic automatically validates incoming JSON and returns clear
# errors if a field is missing or has the wrong type.

class BatteryInput(BaseModel):
    """JSON body the client (e.g. ESP32) sends to POST /predict."""
    voltage: float            = Field(..., ge=0, le=5,   description="Cell voltage in Volts (e.g. 3.55)")
    current: float            = Field(..., ge=0, le=50,  description="Current in Amps (e.g. 2.0)")
    temperature: float        = Field(..., ge=-20, le=80, description="Temperature in °C (e.g. 32)")
    battery_percentage: float = Field(..., ge=0, le=100, description="State-of-charge 0–100 %")
    humidity: float           = Field(..., ge=0, le=100, description="Relative humidity in % (e.g. 45)")

    # Example shown in Swagger UI
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "voltage": 3.55,
                    "current": 2.0,
                    "temperature": 32.0,
                    "battery_percentage": 75.0,
                    "humidity": 50.0,
                }
            ]
        }
    }


class AlertItem(BaseModel):
    """A single warning alert."""
    level: str      = Field(..., description="'warning' or 'critical'")
    message: str    = Field(..., description="Human-readable alert text")


class PredictionResponse(BaseModel):
    """Structured JSON returned by POST /predict."""
    soh_prediction: float                  = Field(..., description="Battery SOH as percentage (0–100)")
    degradation_percentage: float          = Field(..., description="Degradation risk as percentage (0–100)")
    estimated_cycle_aging: int             = Field(..., description="Estimated effective cycles based on wear")
    estimated_rul: int                     = Field(..., description="Estimated Remaining Useful Life indicator")
    battery_condition: str                 = Field(..., description="Healthy / Moderate / Critical")
    alerts: List[AlertItem]                = Field(default_factory=list, description="Warning alerts")
    recommendations: List[str]             = Field(default_factory=list, description="Smart recommendations")

# ─────────────────────────────────────────────────────────────────
# STEP 5 ▸ Helper — generate alerts
# ─────────────────────────────────────────────────────────────────

def generate_alerts(data: BatteryInput) -> List[AlertItem]:
    """Check sensor values against safe thresholds and emit alerts."""
    alerts: List[AlertItem] = []

    # Temperature alerts (overheating risk)
    if data.temperature > 45:
        alerts.append(AlertItem(
            level="critical",
            message=f"OVERHEATING — Temperature {data.temperature}°C exceeds safe limits. Risk of thermal runaway!"
        ))
    elif data.temperature > 38:
        alerts.append(AlertItem(
            level="warning",
            message=f"High temperature ({data.temperature}°C). Active cooling recommended."
        ))

    # Voltage alerts (low voltage / overvoltage risk)
    if data.voltage < 2.8:
        alerts.append(AlertItem(
            level="critical",
            message=f"LOW VOLTAGE — {data.voltage}V is below safe minimum. Irreversible cell damage possible."
        ))
    if data.voltage > 4.15:
        alerts.append(AlertItem(
            level="critical",
            message=f"OVERVOLTAGE — {data.voltage}V exceeds maximum threshold. Risk of cell stress."
        ))

    # Current alerts (excessive current draw)
    if data.current > 6.0:
        alerts.append(AlertItem(
            level="warning",
            message=f"Excessive current ({data.current}A). High draw accelerates electrode degradation."
        ))

    # Humidity alerts (high humidity risk)
    if data.humidity > 80:
        alerts.append(AlertItem(
            level="warning",
            message=f"High humidity ({data.humidity}%). Risk of condensation and short circuits."
        ))

    return alerts

# ─────────────────────────────────────────────────────────────────
# STEP 6 ▸ Helper — generate smart recommendations
# ─────────────────────────────────────────────────────────────────

def generate_suggestions(data: BatteryInput, risk_pct: float) -> List[str]:
    """Return context-aware recommendations based on current telemetry."""
    tips: List[str] = []

    if data.temperature > 35:
        tips.append(
            "🌡️ Avoid overheating — park in shade and ensure proper ventilation. "
            "High temperatures accelerate chemical degradation inside the cells."
        )
    if data.current > 4:
        tips.append(
            "⚡ Reduce fast-charging or extreme acceleration — high-current loads generate excess heat "
            "and stress the battery. Use Level 2 (AC) charging when possible."
        )
    if data.battery_percentage < 20:
        tips.append(
            "🪫 Avoid deep discharge — keeping the battery below 20% regularly "
            "increases internal resistance and shortens lifespan."
        )
    if data.battery_percentage > 90:
        tips.append(
            "🔋 Avoid staying at 100% — prolonged full charge stresses cells. "
            "Set a daily charge limit of 80%."
        )
    if data.battery_percentage < 20 or data.battery_percentage > 80:
        tips.append(
            "📐 Maintain optimal charge range (20%–80%) — this is the ideal operating window "
            "that minimises stress on lithium-ion cells."
        )
    if data.humidity > 70:
        tips.append(
            "💧 Avoid prolonged high humidity exposure — keep the battery in a dry environment "
            "to prevent corrosion and condensation-related issues."
        )
    if risk_pct > 25:
        tips.append(
            "🛡️ Elevated degradation risk — current operating conditions are "
            "accelerating wear. Review temperature and usage habits."
        )

    # Default positive message if no warnings
    if not tips:
        tips.append(
            "✅ Great job — your battery is operating within optimal parameters. "
            "Keep maintaining charge between 20%–80% for maximum longevity."
        )

    return tips

# ─────────────────────────────────────────────────────────────────
# STEP 7 ▸ Routes
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Welcome / health-check endpoint."""
    return {
        "service": "EV Battery AI Telemetry API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Readiness probe — confirms models are loaded."""
    return {
        "status": "healthy",
        "models_loaded": True,
        "internal_feature_names": FEATURE_NAMES,
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict_battery(data: BatteryInput):
    """
    Main inference endpoint for ESP32 telemetry.

    **Telemetry Mapping Workflow:**
    The AI model expects: [voltage, temperature, capacity, cycle, rul].
    However, the ESP32 sends: [voltage, current, temperature, battery_percentage, humidity].

    Instead of directly counting cycles, we approximate cycle-related degradation
    behavior using the real-time telemetry inputs (temperature, humidity, voltage stress).
    This creates an "Effective Cycle Aging" indicator.
    """

    # 1. Feature Approximation / Telemetry Mapping
    # -------------------------------------------------------------
    # Approximate capacity based on state-of-charge (nominal 2.0 Ah battery)
    estimated_capacity = round((data.battery_percentage / 100.0) * 2.0, 4)

    # Estimate "Effective Cycle Aging"
    # A battery operating at high temperature or high humidity experiences
    # chemical aging equivalent to more physical charge cycles.
    base_cycles = max(1, 100 - data.battery_percentage) 
    temp_stress = max(0, data.temperature - 25) * 1.5   # Extra wear above 25°C
    humid_stress = max(0, data.humidity - 50) * 0.5     # Extra wear above 50% RH
    current_stress = max(0, data.current - 2.0) * 2.0   # Extra wear from high current

    estimated_cycle_aging = int(base_cycles + temp_stress + humid_stress + current_stress)

    # Estimate RUL (Remaining Useful Life) in pseudo-units (max ~168 based on training data)
    estimated_rul = max(0, 168 - estimated_cycle_aging)

    # 2. Build model input vector
    # -------------------------------------------------------------
    feature_vector = np.array([[
        data.voltage,
        data.temperature,
        estimated_capacity,
        estimated_cycle_aging,
        estimated_rul,
    ]])

    # 3. AI Inference
    # -------------------------------------------------------------
    soh_raw  = float(soh_model.predict(feature_vector)[0])
    risk_raw = float(risk_model.predict(feature_vector)[0])

    health_pct = round(max(0, min(soh_raw * 100, 100)), 2)
    risk_pct   = round(max(0, min(risk_raw * 100, 100)), 2)

    # 4. Battery condition categorisation
    # -------------------------------------------------------------
    if health_pct >= 80:
        status = "Healthy"
    elif health_pct >= 60:
        status = "Moderate"
    else:
        status = "Critical"

    # 5. Return structured JSON
    # -------------------------------------------------------------
    return PredictionResponse(
        soh_prediction=health_pct,
        degradation_percentage=risk_pct,
        estimated_cycle_aging=estimated_cycle_aging,
        estimated_rul=estimated_rul,
        battery_condition=status,
        alerts=generate_alerts(data),
        recommendations=generate_suggestions(data, risk_pct),
    )

# ─────────────────────────────────────────────────────────────────
# STEP 8 ▸ Live Telemetry Simulation
# ─────────────────────────────────────────────────────────────────
# We use a simple global dictionary to maintain realistic battery 
# state across multiple API calls, simulating a draining EV battery.
sim_state = {
    "voltage": 4.1,               # Starts fully charged
    "current": 2.5,               # Base driving current
    "temperature": 28.0,          # Ambient starting temp
    "battery_percentage": 100.0,  # 100% charged
    "humidity": 45.0              # Normal humidity
}

@app.get("/live-data", tags=["Simulation"])
def get_live_data():
    """
    Simulates a live ESP32 telemetry feed.
    Each call slightly drains the battery and fluctuates sensors,
    then runs the AI inference internally to return a combined payload.
    This allows a frontend dashboard to poll this endpoint for real-time updates.
    """
    global sim_state
    
    # 1. Simulate realistic fluctuations
    # Voltage drops slightly as battery drains (but keeps random noise)
    sim_state["voltage"] = max(3.0, min(4.2, sim_state["voltage"] - random.uniform(0.001, 0.01)))
    
    # Current fluctuates based on simulated driving load
    sim_state["current"] = max(1.0, min(15.0, sim_state["current"] + random.uniform(-1.5, 1.5)))
    
    # Temperature rises slightly with current draw and slowly returns to ambient
    temp_increase = (sim_state["current"] * 0.05) + random.uniform(-0.5, 0.5)
    sim_state["temperature"] = max(15.0, min(65.0, sim_state["temperature"] + temp_increase))
    
    # Battery drains faster if current is high
    drain_rate = (sim_state["current"] * 0.05) + random.uniform(0.01, 0.1)
    sim_state["battery_percentage"] = max(0.0, sim_state["battery_percentage"] - drain_rate)
    
    # Humidity fluctuates naturally
    sim_state["humidity"] = max(30.0, min(90.0, sim_state["humidity"] + random.uniform(-2.0, 2.0)))
    
    # 2. Build input for inference
    input_data = BatteryInput(
        voltage=round(sim_state["voltage"], 2),
        current=round(sim_state["current"], 2),
        temperature=round(sim_state["temperature"], 2),
        battery_percentage=round(sim_state["battery_percentage"], 1),
        humidity=round(sim_state["humidity"], 1)
    )
    
    # 3. Run internal AI inference using our existing function
    prediction = predict_battery(input_data)
    
    # 4. Return combined JSON
    return {
        "voltage": input_data.voltage,
        "current": input_data.current,
        "temperature": input_data.temperature,
        "battery_percentage": input_data.battery_percentage,
        "humidity": input_data.humidity,
        "soh_prediction": prediction.soh_prediction,
        "degradation_percentage": prediction.degradation_percentage,
        "estimated_cycle_aging": prediction.estimated_cycle_aging,
        "estimated_rul": prediction.estimated_rul,
        "battery_condition": prediction.battery_condition,
        "alerts": prediction.alerts,
        "recommendations": prediction.recommendations,
    }
