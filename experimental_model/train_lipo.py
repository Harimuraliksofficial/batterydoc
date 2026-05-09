import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Ensure graphs directory exists
os.makedirs('graphs', exist_ok=True)

def load_data():
    """Load the primary battery aging dataset safely."""
    print("Loading datasets...")
    try:
        # We focus on the primary dataset which contains the cycle vs capacity data
        df = pd.read_csv('cycle_vs_capacity.csv')
        df = df.dropna() # Clean NaN values
        # Normalize column names
        df.columns = [col.strip().lower() for col in df.columns]
        
        # We rename to standard names if needed, but cycle_number and capacity_ah are already good
        if 'cycle_num' in df.columns and 'cycle_number' not in df.columns:
            df.rename(columns={'cycle_num': 'cycle_number'}, inplace=True)
            
        print(f"Data loaded successfully. Rows: {len(df)}")
        return df
    except FileNotFoundError:
        print("Error: Primary dataset 'cycle_vs_capacity.csv' not found.")
        return None
    except Exception as e:
        print(f"Unexpected error loading data: {e}")
        return None

def engineer_features(df):
    """Calculate SOH, degradation, RUL, and engineer additional features."""
    print("Engineering features and calculating SOH...")
    
    # Calculate Initial Capacity per battery to define 100% SOH
    initial_caps = df[df['cycle_number'] == 0].set_index('battery_id')['capacity_ah'].to_dict()
    
    # 1. Calculate SOH mathematically
    df['initial_capacity'] = df['battery_id'].map(initial_caps)
    # Handle cases where cycle 0 might be missing by using the max capacity of that battery
    if df['initial_capacity'].isnull().any():
        max_caps = df.groupby('battery_id')['capacity_ah'].max().to_dict()
        df['initial_capacity'] = df['initial_capacity'].fillna(df['battery_id'].map(max_caps))
        
    df['soh'] = (df['capacity_ah'] / df['initial_capacity']) * 100.0
    
    # 2. Calculate degradation percentage
    df['degradation_percentage'] = 100.0 - df['soh']
    
    # 3. Estimate RUL
    # Assume End-of-life SOH = 70%, Maximum expected cycles = 500
    df['rul'] = df['cycle_number'].apply(lambda x: max(0, 500 - x))
    
    # Additional feature engineering (rolling average, normalized capacity)
    df['normalized_capacity'] = df['capacity_ah'] / df['initial_capacity']
    
    # Calculate degradation slope (change in SOH per cycle)
    df['degradation_slope'] = df.groupby('battery_id')['soh'].diff() / df.groupby('battery_id')['cycle_number'].diff()
    df['degradation_slope'] = df['degradation_slope'].fillna(0) # Fill first row NaNs
    
    return df

def generate_graphs(df, soh_pred=None, y_test_soh=None):
    """Generate and save battery health trend graphs."""
    print("Generating graphs...")
    
    # 1. SOH vs Cycle graph
    plt.figure(figsize=(10, 6))
    for bat_id in df['battery_id'].unique():
        bat_data = df[df['battery_id'] == bat_id]
        plt.plot(bat_data['cycle_number'], bat_data['soh'], marker='o', label=f'Battery {bat_id}')
    plt.axhline(y=70, color='r', linestyle='--', label='End of Life (70% SOH)')
    plt.title('State of Health (SOH) vs Cycle Number')
    plt.xlabel('Cycle Number')
    plt.ylabel('SOH (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('graphs/soh_vs_cycle.png')
    plt.close()

    # 2. Capacity fade graph
    plt.figure(figsize=(10, 6))
    for bat_id in df['battery_id'].unique():
        bat_data = df[df['battery_id'] == bat_id]
        plt.plot(bat_data['cycle_number'], bat_data['capacity_ah'], marker='s')
    plt.title('Capacity Fade Over Cycles')
    plt.xlabel('Cycle Number')
    plt.ylabel('Capacity (Ah)')
    plt.grid(True, alpha=0.3)
    plt.savefig('graphs/capacity_fade.png')
    plt.close()

    # 3. Degradation trend graph
    plt.figure(figsize=(10, 6))
    for bat_id in df['battery_id'].unique():
        bat_data = df[df['battery_id'] == bat_id]
        plt.plot(bat_data['cycle_number'], bat_data['degradation_percentage'], marker='^')
    plt.title('Battery Degradation Trend')
    plt.xlabel('Cycle Number')
    plt.ylabel('Degradation (%)')
    plt.grid(True, alpha=0.3)
    plt.savefig('graphs/degradation_trend.png')
    plt.close()

    # 4. Prediction comparison graph
    if soh_pred is not None and y_test_soh is not None:
        plt.figure(figsize=(10, 6))
        plt.scatter(y_test_soh, soh_pred, alpha=0.7, color='b')
        plt.plot([y_test_soh.min(), y_test_soh.max()], [y_test_soh.min(), y_test_soh.max()], 'r--')
        plt.title('SOH Prediction Accuracy')
        plt.xlabel('Actual SOH (%)')
        plt.ylabel('Predicted SOH (%)')
        plt.grid(True, alpha=0.3)
        plt.savefig('graphs/prediction_comparison.png')
        plt.close()

def evaluate_model(name, y_true, y_pred):
    """Print evaluation metrics for a model."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    print(f"--- {name} Evaluation ---")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²:   {r2:.4f}\n")

def train_models(df):
    """Train RandomForest models for SOH, Degradation, and RUL."""
    print("Preparing data for training...")
    # Features chosen for training
    features = ['cycle_number', 'capacity_ah', 'normalized_capacity']
    
    X = df[features]
    y_soh = df['soh']
    y_deg = df['degradation_percentage']
    y_rul = df['rul']
    
    # Split data (80% train, 20% test)
    X_train, X_test, y_soh_train, y_soh_test = train_test_split(X, y_soh, test_size=0.2, random_state=42)
    _, _, y_deg_train, y_deg_test = train_test_split(X, y_deg, test_size=0.2, random_state=42)
    _, _, y_rul_train, y_rul_test = train_test_split(X, y_rul, test_size=0.2, random_state=42)
    
    print("Training SOH Model...")
    soh_model = RandomForestRegressor(n_estimators=100, random_state=42)
    soh_model.fit(X_train, y_soh_train)
    soh_pred = soh_model.predict(X_test)
    evaluate_model("SOH Model", y_soh_test, soh_pred)
    
    print("Training Degradation Model...")
    deg_model = RandomForestRegressor(n_estimators=100, random_state=42)
    deg_model.fit(X_train, y_deg_train)
    deg_pred = deg_model.predict(X_test)
    evaluate_model("Degradation Model", y_deg_test, deg_pred)
    
    print("Training RUL Model...")
    rul_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rul_model.fit(X_train, y_rul_train)
    rul_pred = rul_model.predict(X_test)
    evaluate_model("RUL Model", y_rul_test, rul_pred)
    
    # Save models
    save_models(soh_model, deg_model, rul_model)
    
    # Generate graphs including prediction comparison
    generate_graphs(df, soh_pred, y_soh_test)

def save_models(soh_model, deg_model, rul_model):
    """Save trained models to disk."""
    print("Saving models to disk...")
    try:
        joblib.dump(soh_model, 'soh_model.pkl')
        joblib.dump(deg_model, 'degradation_model.pkl')
        joblib.dump(rul_model, 'rul_model.pkl')
        print("Models successfully saved as .pkl files.")
    except Exception as e:
        print(f"Error saving models: {e}")

def main():
    print("="*50)
    print("LiPo Battery Aging AI Pipeline — Training Started")
    print("="*50)
    
    # 1. Load Data
    df = load_data()
    if df is None:
        return
        
    # 2. Preprocess & Engineer Features
    df = engineer_features(df)
    
    # 3. Train Models, Evaluate, and Generate Graphs
    train_models(df)
    
    print("="*50)
    print("Pipeline Execution Completed Successfully.")
    print("="*50)

if __name__ == "__main__":
    main()
