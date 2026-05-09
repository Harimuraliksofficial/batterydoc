import os
import joblib
import pandas as pd

def load_trained_models():
    """Load the saved trained models."""
    try:
        soh_model = joblib.load('soh_model.pkl')
        deg_model = joblib.load('degradation_model.pkl')
        rul_model = joblib.load('rul_model.pkl')
        return soh_model, deg_model, rul_model
    except FileNotFoundError as e:
        print(f"Error loading models: {e}. Please run train_lipo.py first.")
        return None, None, None

def determine_condition(soh):
    """Determine the battery condition based on engineering rules."""
    if soh > 85.0:
        return "Healthy"
    elif soh >= 70.0:
        return "Moderate"
    else:
        return "Critical"

def main():
    print("="*50)
    print("LiPo Battery AI — Telemetry Testing Inference")
    print("="*50)
    
    soh_model, deg_model, rul_model = load_trained_models()
    if not soh_model:
        return
        
    # Sample telemetry data representing 3 different battery states
    # Features required by the models: ['cycle_number', 'capacity_ah', 'normalized_capacity']
    # Normally, normalized_capacity is capacity_ah / initial_capacity
    
    sample_data = [
        {"scenario": "New Battery", "cycle_number": 10, "capacity_ah": 1.02, "normalized_capacity": 0.99},
        {"scenario": "Mid-Life Battery", "cycle_number": 180, "capacity_ah": 0.85, "normalized_capacity": 0.83},
        {"scenario": "Degraded Battery", "cycle_number": 450, "capacity_ah": 0.68, "normalized_capacity": 0.65}
    ]
    
    print("Running predictions on simulated telemetry...\n")
    
    for item in sample_data:
        scenario = item.pop("scenario")
        
        # Convert dictionary to DataFrame to feed into model
        df_input = pd.DataFrame([item])
        
        try:
            # Predict values
            pred_soh = soh_model.predict(df_input)[0]
            pred_deg = deg_model.predict(df_input)[0]
            pred_rul = rul_model.predict(df_input)[0]
            
            condition = determine_condition(pred_soh)
            
            print(f"--- Scenario: {scenario} ---")
            print(f"Input Telemetry : Cycles: {item['cycle_number']}, Capacity: {item['capacity_ah']} Ah")
            print(f"Predicted SOH   : {pred_soh:.2f} %")
            print(f"Degradation %   : {pred_deg:.2f} %")
            print(f"Estimated RUL   : {int(pred_rul)} cycles")
            print(f"Condition       : {condition}\n")
            
        except Exception as e:
            print(f"Error making prediction for {scenario}: {e}")
            
    print("="*50)
    print("Testing Completed Successfully.")
    print("="*50)

if __name__ == "__main__":
    main()
