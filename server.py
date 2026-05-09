import os
import time
import logging
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ─────────────────────────────────────────────────────────────────
# 1. SETUP & CONFIGURATION
# ─────────────────────────────────────────────────────────────────

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("batterydock")

# Initialize FastAPI App
app = FastAPI(
    title="BatteryDock AI Backend",
    description="Production-grade AI backend using trained LiPo Random Forest models.",
    version="3.0.0"
)

# Enable CORS for React Frontend compatibility
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

logger.info("Initializing BatteryDock AI Engine...")

try:
    # Load the new trained LiPo models
    soh_model = joblib.load("soh_model.pkl")
    degradation_model = joblib.load("degradation_model.pkl")
    rul_model = joblib.load("rul_model.pkl")
    logger.info("✅ Successfully loaded soh_model.pkl, degradation_model.pkl, rul_model.pkl")
except Exception as e:
    logger.error(f"❌ CRITICAL ERROR: Failed to load models. {e}")
    # We do not crash the app, but log the error. The endpoints have try/except.
    soh_model, degradation_model, rul_model = None, None, None

# ─────────────────────────────────────────────────────────────────
# 3. PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────

class TelemetryInput(BaseModel):
    """Incoming telemetry data from the React frontend."""
    voltage: float
    current: float
    temperature: float
    battery_percentage: float
    humidity: float
    cycle_num: int
    capacity_ah: float

class PredictionResponse(BaseModel):
    """Outgoing JSON response back to the React frontend."""
    soh_prediction: float
    degradation_percentage: float
    estimated_rul: int
    battery_condition: str
    alerts: List[str]
    recommendations: List[str]

# ─────────────────────────────────────────────────────────────────
# 4. BUSINESS LOGIC & RULES
# ─────────────────────────────────────────────────────────────────

def evaluate_condition(soh: float) -> str:
    """Determine battery condition based on SOH rules."""
    if soh > 85:
        return "Healthy"
    elif soh >= 70:
        return "Moderate"
    else:
        return "Critical"

def generate_alerts(data: TelemetryInput, deg: float) -> List[str]:
    """Generate system alerts based on sensor telemetry thresholds."""
    alerts = []
    if data.temperature > 45:
        alerts.append("OVERHEATING warning: Thermal runaway risk detected.")
    if data.humidity > 80:
        alerts.append("MOISTURE RISK warning: High humidity environment.")
    if data.voltage < 3.2:
        alerts.append("LOW VOLTAGE warning: Potential cell damage occurring.")
    if deg > 30:
        alerts.append("HIGH DEGRADATION warning: Battery requires service or replacement.")
    return alerts

def generate_recommendations(data: TelemetryInput) -> List[str]:
    """Generate dynamic recommendations based on telemetry behavior."""
    recs = []
    if data.temperature > 35:
        recs.append("Reduce thermal stress. Ensure proper cooling.")
    if data.current > 5:
        recs.append("Reduce sustained high current discharge.")
    if data.battery_percentage < 20:
        recs.append("Avoid deep discharge. Charge battery soon.")
    if data.humidity > 70:
        recs.append("Avoid moisture exposure. Inspect cooling/sealing system.")
    
    if not recs:
        recs.append("Maintain 20–80% charging window for maximum lifespan.")
    return recs

# ─────────────────────────────────────────────────────────────────
# 5. API ROUTES
# ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Root health check endpoint."""
    return {"status": "BatteryDock AI Backend Online", "version": "3.0"}

@app.post("/predict", response_model=PredictionResponse, tags=["AI Inference"])
def predict_health(data: TelemetryInput):
    """
    Main AI prediction pipeline.
    Never crashes. Returns JSON.
    Uses 'cycle_num' and 'capacity_ah' for prediction.
    Uses other sensors for alerts and recommendations.
    """
    try:
        logger.info(f"Received telemetry: Cycle {data.cycle_num}, Capacity {data.capacity_ah}Ah, Temp {data.temperature}°C")
        
        # 1. Feature Engineering for the ML Model
        # The trained model expects exactly: ['cycle_number', 'capacity_ah', 'normalized_capacity']
        # We compute normalized_capacity assuming nominal capacity is roughly ~1.0 Ah based on training.
        normalized_cap = data.capacity_ah / 1.0 
        
        feature_df = pd.DataFrame([{
            "cycle_number": data.cycle_num,
            "capacity_ah": data.capacity_ah,
            "normalized_capacity": normalized_cap
        }])
        
        # 2. Run AI Inference safely
        if soh_model and degradation_model and rul_model:
            base_soh = float(soh_model.predict(feature_df)[0])
            base_deg = float(degradation_model.predict(feature_df)[0])
            rul = int(rul_model.predict(feature_df)[0])

            # Apply real-time engineering physics to make SOH reactive to all telemetry sliders
            temp_stress = max(0, (data.temperature - 25) * 0.12)
            current_stress = data.current * 0.25
            voltage_dip = (4.2 - data.voltage) * 1.5

            soh = max(0.0, min(100.0, base_soh - temp_stress - current_stress - voltage_dip))
            deg = max(0.0, min(100.0, base_deg + temp_stress + current_stress + voltage_dip))
        else:
            # Fallback if models failed to load at startup
            logger.warning("Models not loaded. Using fallback calculation.")
            soh = 100.0 - (data.cycle_num * 0.1)
            deg = 100.0 - soh
            rul = max(0, 500 - data.cycle_num)

        # Ensure bounds
        soh = max(0.0, min(100.0, round(soh, 2)))
        deg = max(0.0, min(100.0, round(deg, 2)))
        rul = max(0, rul)

        # 3. Generate conditions and notifications
        condition = evaluate_condition(soh)
        alerts = generate_alerts(data, deg)
        recs = generate_recommendations(data)

        # 4. Construct JSON Response
        response = {
            "soh_prediction": soh,
            "degradation_percentage": deg,
            "estimated_rul": rul,
            "battery_condition": condition,
            "alerts": alerts,
            "recommendations": recs
        }
        
        logger.info(f"Predicted SOH: {soh}%, Deg: {deg}%, Condition: {condition}")
        return response

    except Exception as e:
        # 5. NEVER crash. Catch all errors and return a safe fallback JSON response.
        logger.error(f"❌ Prediction Error: {e}")
        
        # Safe fallback response ensuring 200 OK
        return {
            "soh_prediction": 0.0,
            "degradation_percentage": 100.0,
            "estimated_rul": 0,
            "battery_condition": "Critical",
            "alerts": ["SYSTEM ERROR: Inference failed. Fallback engaged."],
            "recommendations": ["Check backend server logs."]
        }

# Global state for simulated live data
sim_state = {
    "voltage": 4.1,
    "current": 2.2,
    "temperature": 25.0,
    "battery_percentage": 100.0,
    "humidity": 45.0,
    "cycle_num": 10,
    "capacity_ah": 1.02
}

import random

@app.get("/live-data", tags=["Simulation"])
def get_live_data():
    """
    Simulates a live ESP32 telemetry feed for the frontend.
    Returns realistic drifting telemetry combined with AI predictions.
    """
    global sim_state
    
    # Simulate realistic fluctuations
    sim_state["voltage"] = max(3.0, min(4.2, sim_state["voltage"] - random.uniform(0.001, 0.01)))
    sim_state["current"] = max(1.0, min(15.0, sim_state["current"] + random.uniform(-1.5, 1.5)))
    sim_state["temperature"] = max(15.0, min(65.0, sim_state["temperature"] + (sim_state["current"] * 0.05)))
    sim_state["battery_percentage"] = max(0.0, sim_state["battery_percentage"] - random.uniform(0.01, 0.1))
    sim_state["humidity"] = max(30.0, min(90.0, sim_state["humidity"] + random.uniform(-1.0, 1.0)))
    
    # Gradually degrade battery over time in simulation
    sim_state["cycle_num"] += 1
    sim_state["capacity_ah"] = max(0.5, sim_state["capacity_ah"] - random.uniform(0.0001, 0.001))
    
    input_data = TelemetryInput(
        voltage=round(sim_state["voltage"], 2),
        current=round(sim_state["current"], 2),
        temperature=round(sim_state["temperature"], 2),
        battery_percentage=round(sim_state["battery_percentage"], 1),
        humidity=round(sim_state["humidity"], 1),
        cycle_num=sim_state["cycle_num"],
        capacity_ah=round(sim_state["capacity_ah"], 4)
    )
    
    # Run prediction internally
    prediction = predict_health(input_data)
    
    # Merge telemetry and prediction for the frontend
    result = input_data.model_dump()
    result.update(prediction)
    
    return result
