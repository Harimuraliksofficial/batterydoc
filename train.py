"""
╔══════════════════════════════════════════════════════════════════╗
║         EV Battery AI Training System — train.py                ║
║  Predicts: State of Health (SOH) & Degradation Risk             ║
║  Algorithm: Random Forest Regression                             ║
║  Dataset: NASA Battery Cycle-Level Data (CLEAN_FINAL.csv)       ║
╚══════════════════════════════════════════════════════════════════╝

HOW THIS SCRIPT WORKS (for beginners):
  1.  Load the CSV battery dataset into a pandas DataFrame
  2.  Automatically discover which columns are available
  3.  Select the best feature columns (voltage, temperature, etc.)
  4.  Engineer a "degradation_risk" target from the SOH column
  5.  Clean any missing / NaN values
  6.  Split data into training and testing sets (80 / 20)
  7.  Train two Random Forest models:
        Model A → predict SOH (State of Health, 0–1 scale)
        Model B → predict degradation_risk (0–1 scale)
  8.  Evaluate both models with MAE, RMSE, and R² score
  9.  Save both trained models to disk as .pkl files
  10. Print a friendly summary with a sample prediction
"""

# ─────────────────────────────────────────────────────────────────
# STEP 0 ▸ Import libraries
# ─────────────────────────────────────────────────────────────────
# pandas  → tabular data manipulation (like Excel in Python)
# numpy   → math / array operations
# sklearn → scikit-learn, the core machine-learning toolkit
# joblib  → fast model serialisation (.pkl files)
# pathlib → cross-platform file paths
# ─────────────────────────────────────────────────────────────────
import os
import sys
import pathlib

# ── Force UTF-8 output so emoji print correctly on Windows ─────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import numpy  as np
import pandas as pd
import joblib

from sklearn.ensemble        import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics         import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing   import MinMaxScaler

# ─────────────────────────────────────────────────────────────────
# STEP 1 ▸ Paths & configuration
# ─────────────────────────────────────────────────────────────────
# All paths are defined relative to this script's directory so the
# project is portable across machines.
BASE_DIR   = pathlib.Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
MODEL_DIR  = BASE_DIR          # save models next to train.py

# We search data/ for the first CSV file automatically.
# This means you can rename or swap the dataset without editing code.
CSV_FILES  = sorted(DATA_DIR.glob("*.csv"))
if not CSV_FILES:
    print("❌  No CSV files found in the 'data/' directory.")
    print(f"   Expected path: {DATA_DIR.resolve()}")
    sys.exit(1)

CSV_PATH = CSV_FILES[0]
print(f"\n📂  Dataset found : {CSV_PATH.name}")

# ─────────────────────────────────────────────────────────────────
# STEP 2 ▸ Load dataset into a pandas DataFrame
# ─────────────────────────────────────────────────────────────────
# A DataFrame is like a spreadsheet — rows are observations (one
# battery cycle each) and columns are measurements.
print("\n" + "─" * 60)
print("STEP 1 ▸  Loading dataset …")
print("─" * 60)

df = pd.read_csv(CSV_PATH)

print(f"   Rows  : {len(df):,}")
print(f"   Cols  : {len(df.columns)}")
print(f"   Columns detected: {list(df.columns)}")

# ─────────────────────────────────────────────────────────────────
# STEP 3 ▸ Automatically analyse available columns
# ─────────────────────────────────────────────────────────────────
# We look for columns whose names match known battery-sensor keywords.
# This makes the script resilient to minor column-name variations.
print("\n" + "─" * 60)
print("STEP 2 ▸  Analysing dataset columns …")
print("─" * 60)

# Keywords that map to physical meaning
FEATURE_KEYWORDS = {
    "voltage"     : ["voltage", "volt", "v_avg", "v_mean"],
    "temperature" : ["temperature", "temp", "celsius", "kelvin"],
    "current"     : ["current", "amp", "ampere", "i_avg"],
    "capacity"    : ["capacity", "cap", "charge"],
    "cycle"       : ["cycle", "cycles"],
    "rul"         : ["rul", "remaining_useful_life"],
}

TARGET_KEYWORDS = {
    "soh"         : ["soh", "state_of_health", "health"],
}

def find_column(df_cols: list, keywords: list) -> str | None:
    """Return the first column name that matches any keyword (case-insensitive)."""
    df_cols_lower = [c.lower() for c in df_cols]
    for kw in keywords:
        for i, col_l in enumerate(df_cols_lower):
            if kw in col_l:
                return df_cols[i]
    return None

col_map = {}   # maps logical name → actual column name

# Detect feature columns
for logical, keywords in FEATURE_KEYWORDS.items():
    found = find_column(list(df.columns), keywords)
    col_map[logical] = found
    status = f"✅  {found}" if found else "⚠️   not found (will skip)"
    print(f"   [{logical:<12}] → {status}")

# Detect target column (SOH)
for logical, keywords in TARGET_KEYWORDS.items():
    found = find_column(list(df.columns), keywords)
    col_map[logical] = found
    status = f"✅  {found}" if found else "❌  REQUIRED — not found"
    print(f"   [{logical:<12}] → {status}")

if col_map.get("soh") is None:
    print("\n❌  Cannot proceed: SOH column is required but was not found.")
    sys.exit(1)

SOH_COL = col_map["soh"]

# Build the list of available feature columns (only those found)
AVAILABLE_FEATURES = [
    col_map[k]
    for k in FEATURE_KEYWORDS
    if col_map.get(k) is not None
]

print(f"\n   Feature columns to be used : {AVAILABLE_FEATURES}")
print(f"   Target column (SOH)         : {SOH_COL}")

# ─────────────────────────────────────────────────────────────────
# STEP 4 ▸ Engineer "degradation_risk" target
# ─────────────────────────────────────────────────────────────────
# SOH ranges from ~1.0 (healthy) down to ~0.7 (end-of-life).
# Degradation Risk = 1 − SOH (normalised 0–1).
# A battery with SOH = 0.70 has degradation_risk = 0.30
# A battery with SOH = 1.00 has degradation_risk = 0.00  (brand new)
print("\n" + "─" * 60)
print("STEP 3 ▸  Engineering 'degradation_risk' target …")
print("─" * 60)

df["degradation_risk"] = 1.0 - df[SOH_COL].clip(upper=1.0)
RISK_COL = "degradation_risk"
print(f"   degradation_risk range: "
      f"{df[RISK_COL].min():.4f}  →  {df[RISK_COL].max():.4f}")

# ─────────────────────────────────────────────────────────────────
# STEP 5 ▸ Clean missing values
# ─────────────────────────────────────────────────────────────────
# NaN (Not-a-Number) values break most ML algorithms.
# We drop rows where any of our chosen columns has NaN.
print("\n" + "─" * 60)
print("STEP 4 ▸  Cleaning missing values …")
print("─" * 60)

ALL_COLS = AVAILABLE_FEATURES + [SOH_COL, RISK_COL]
before   = len(df)
df       = df[ALL_COLS].dropna()
after    = len(df)

print(f"   Rows before cleaning : {before:,}")
print(f"   Rows after  cleaning : {after:,}")
print(f"   Rows dropped         : {before - after:,}")

if after < 50:
    print("⚠️   Very few rows remain after cleaning. Results may be unreliable.")

# ─────────────────────────────────────────────────────────────────
# STEP 6 ▸ Prepare features (X) and targets (y_soh, y_risk)
# ─────────────────────────────────────────────────────────────────
# X is the input matrix — what the model "sees"
# y is the output vector — what the model "learns to predict"
print("\n" + "─" * 60)
print("STEP 5 ▸  Preparing features and targets …")
print("─" * 60)

X      = df[AVAILABLE_FEATURES].values   # shape: (n_samples, n_features)
y_soh  = df[SOH_COL].values              # shape: (n_samples,)
y_risk = df[RISK_COL].values             # shape: (n_samples,)

print(f"   Feature matrix shape : {X.shape}")
print(f"   SOH target shape     : {y_soh.shape}")
print(f"   Risk target shape    : {y_risk.shape}")
print(f"\n   Feature statistics:")
for i, col in enumerate(AVAILABLE_FEATURES):
    print(f"     {col:<18} min={X[:, i].min():.4f}  "
          f"max={X[:, i].max():.4f}  mean={X[:, i].mean():.4f}")

# ─────────────────────────────────────────────────────────────────
# STEP 7 ▸ Split into train and test sets (80 / 20)
# ─────────────────────────────────────────────────────────────────
# train_test_split shuffles and splits the data.
# 80 % of rows → training    (the model learns from this)
# 20 % of rows → testing     (we evaluate on unseen data)
# random_state=42 → reproducible results every time you run
print("\n" + "─" * 60)
print("STEP 6 ▸  Splitting dataset (80% train / 20% test) …")
print("─" * 60)

(X_train, X_test,
 y_soh_train,  y_soh_test,
 y_risk_train, y_risk_test) = train_test_split(
    X, y_soh, y_risk,
    test_size=0.2,
    random_state=42,
)

print(f"   Training samples : {len(X_train):,}")
print(f"   Testing  samples : {len(X_test):,}")

# ─────────────────────────────────────────────────────────────────
# STEP 8 ▸ Train Model A — SOH predictor
# ─────────────────────────────────────────────────────────────────
# RandomForestRegressor builds many decision trees (n_estimators)
# and averages their predictions — this reduces overfitting.
#
# Key hyperparameters:
#   n_estimators  → number of trees (more = slower but more accurate)
#   max_depth     → how deep each tree grows (prevents overfitting)
#   random_state  → seed for reproducibility
#   n_jobs=-1     → use ALL CPU cores for speed
print("\n" + "─" * 60)
print("STEP 7 ▸  Training Model A — State of Health (SOH) …")
print("─" * 60)

model_soh = RandomForestRegressor(
    n_estimators = 200,     # 200 decision trees
    max_depth    = 20,      # each tree can be up to 20 levels deep
    min_samples_split = 4,  # need at least 4 samples to split a node
    min_samples_leaf  = 2,  # each leaf must have ≥ 2 samples
    random_state = 42,
    n_jobs       = -1,      # parallel training on all CPU cores
)

model_soh.fit(X_train, y_soh_train)
print("   ✅  Model A training complete.")

# ─────────────────────────────────────────────────────────────────
# STEP 9 ▸ Train Model B — Degradation Risk predictor
# ─────────────────────────────────────────────────────────────────
print("\n" + "─" * 60)
print("STEP 8 ▸  Training Model B — Degradation Risk …")
print("─" * 60)

model_risk = RandomForestRegressor(
    n_estimators = 200,
    max_depth    = 20,
    min_samples_split = 4,
    min_samples_leaf  = 2,
    random_state = 42,
    n_jobs       = -1,
)

model_risk.fit(X_train, y_risk_train)
print("   ✅  Model B training complete.")

# ─────────────────────────────────────────────────────────────────
# STEP 10 ▸ Evaluate both models
# ─────────────────────────────────────────────────────────────────
# MAE  → Mean Absolute Error   (avg error, same units as target)
# RMSE → Root Mean Squared Error (penalises large errors more)
# R²   → R-squared score (1.0 = perfect, 0.0 = as bad as guessing)
print("\n" + "─" * 60)
print("STEP 9 ▸  Evaluating models on the test set …")
print("─" * 60)

def evaluate(model, X_t, y_t, label: str) -> dict:
    """Run predictions and print MAE / RMSE / R² for one model."""
    y_pred = model.predict(X_t)

    mae  = mean_absolute_error(y_t, y_pred)
    rmse = np.sqrt(mean_squared_error(y_t, y_pred))
    r2   = r2_score(y_t, y_pred)

    print(f"\n   📊  {label}")
    print(f"       MAE  (Mean Absolute Error)      : {mae:.6f}")
    print(f"       RMSE (Root Mean Squared Error)  : {rmse:.6f}")
    print(f"       R²   (Coefficient of Determination): {r2:.6f}")

    if r2 >= 0.95:
        grade = "🏆 Excellent"
    elif r2 >= 0.85:
        grade = "✅ Good"
    elif r2 >= 0.70:
        grade = "⚠️  Fair"
    else:
        grade = "❌ Needs improvement"
    print(f"       Model grade: {grade}")

    return {"mae": mae, "rmse": rmse, "r2": r2, "predictions": y_pred}

metrics_soh  = evaluate(model_soh,  X_test, y_soh_test,  "SOH  Predictor")
metrics_risk = evaluate(model_risk, X_test, y_risk_test, "Degradation Risk Predictor")

# ─────────────────────────────────────────────────────────────────
# STEP 11 ▸ Feature importance
# ─────────────────────────────────────────────────────────────────
# Which input features mattered most for the SOH prediction?
print("\n" + "─" * 60)
print("STEP 10 ▸  Feature Importance (SOH model) …")
print("─" * 60)

importances = model_soh.feature_importances_
importance_pairs = sorted(
    zip(AVAILABLE_FEATURES, importances),
    key=lambda x: x[1],
    reverse=True,
)
print("   Feature Name         Importance")
print("   " + "-" * 38)
for feat, imp in importance_pairs:
    bar = "█" * int(imp * 40)
    print(f"   {feat:<20} {imp:.4f}  {bar}")

# ─────────────────────────────────────────────────────────────────
# STEP 12 ▸ Save models to disk
# ─────────────────────────────────────────────────────────────────
# joblib.dump() serialises (pickles) the trained model object to a
# binary file.  joblib.load() later restores the model for inference
# without retraining.
#
# We save:
#   battery_model.pkl      → SOH predictor   (primary model)
#   battery_risk_model.pkl → Degradation Risk predictor
#   battery_model_meta.pkl → metadata for FastAPI integration
print("\n" + "─" * 60)
print("STEP 11 ▸  Saving trained models …")
print("─" * 60)

SOH_MODEL_PATH  = MODEL_DIR / "battery_model.pkl"
RISK_MODEL_PATH = MODEL_DIR / "battery_risk_model.pkl"
META_PATH       = MODEL_DIR / "battery_model_meta.pkl"

# Primary model (SOH)
joblib.dump(model_soh,  SOH_MODEL_PATH)
print(f"   ✅  SOH model saved  → {SOH_MODEL_PATH.name}")

# Risk model
joblib.dump(model_risk, RISK_MODEL_PATH)
print(f"   ✅  Risk model saved → {RISK_MODEL_PATH.name}")

# Metadata dict — useful when building a FastAPI backend later
model_meta = {
    "feature_names"      : AVAILABLE_FEATURES,
    "soh_model_path"     : str(SOH_MODEL_PATH),
    "risk_model_path"    : str(RISK_MODEL_PATH),
    "soh_col"            : SOH_COL,
    "risk_col"           : RISK_COL,
    "train_rows"         : len(X_train),
    "test_rows"          : len(X_test),
    "metrics_soh"        : {k: v for k, v in metrics_soh.items()  if k != "predictions"},
    "metrics_risk"       : {k: v for k, v in metrics_risk.items() if k != "predictions"},
    "feature_importance" : dict(zip(AVAILABLE_FEATURES, importances.tolist())),
}
joblib.dump(model_meta, META_PATH)
print(f"   ✅  Metadata saved   → {META_PATH.name}")

# ─────────────────────────────────────────────────────────────────
# STEP 13 ▸ Sample prediction — see the model in action
# ─────────────────────────────────────────────────────────────────
# We reload the saved model (as a FastAPI endpoint would) and run
# a prediction on the first 5 rows of the test set.
print("\n" + "─" * 60)
print("STEP 12 ▸  Sample predictions from saved model …")
print("─" * 60)

# Reload to confirm the .pkl files work correctly
loaded_soh  = joblib.load(SOH_MODEL_PATH)
loaded_risk = joblib.load(RISK_MODEL_PATH)

sample_X   = X_test[:5]
pred_soh   = loaded_soh.predict(sample_X)
pred_risk  = loaded_risk.predict(sample_X)
actual_soh = y_soh_test[:5]
actual_risk = y_risk_test[:5]

header = f"   {'#':>3}  {'Actual SOH':>12}  {'Pred SOH':>12}  {'Actual Risk':>13}  {'Pred Risk':>12}"
print(header)
print("   " + "-" * (len(header) - 3))
for i in range(5):
    print(f"   {i+1:>3}  {actual_soh[i]:>12.4f}  {pred_soh[i]:>12.4f}  "
          f"{actual_risk[i]:>13.4f}  {pred_risk[i]:>12.4f}")

# ─────────────────────────────────────────────────────────────────
# STEP 14 ▸ FastAPI-ready inference helper (importable function)
# ─────────────────────────────────────────────────────────────────
# When you build a FastAPI backend you can do:
#
#   from train import predict_battery_health
#   result = predict_battery_health(voltage=3.55, temperature=32.5, ...)
#
def predict_battery_health(**sensor_readings) -> dict:
    """
    Inference helper compatible with a FastAPI endpoint.

    Parameters
    ----------
    **sensor_readings : keyword arguments matching AVAILABLE_FEATURES
        e.g. predict_battery_health(voltage=3.55, temperature=32.1, cycle=50)

    Returns
    -------
    dict with keys:
        soh             → predicted State of Health (0–1)
        degradation_risk → predicted degradation risk (0–1)
        health_status   → human-readable label
    """
    _soh_m  = joblib.load(SOH_MODEL_PATH)
    _risk_m = joblib.load(RISK_MODEL_PATH)

    row = [sensor_readings.get(f, np.nan) for f in AVAILABLE_FEATURES]
    if any(np.isnan(v) for v in row):
        missing = [f for f in AVAILABLE_FEATURES if np.isnan(sensor_readings.get(f, np.nan))]
        raise ValueError(f"Missing features: {missing}")

    X_in = np.array(row).reshape(1, -1)
    soh  = float(_soh_m.predict(X_in)[0])
    risk = float(_risk_m.predict(X_in)[0])

    if soh >= 0.90:
        status = "Excellent 🟢"
    elif soh >= 0.80:
        status = "Good 🟡"
    elif soh >= 0.70:
        status = "Fair 🟠"
    else:
        status = "Critical 🔴"

    return {
        "soh"              : round(soh,  4),
        "degradation_risk" : round(risk, 4),
        "health_status"    : status,
    }

# ─────────────────────────────────────────────────────────────────
# Final Summary
# ─────────────────────────────────────────────────────────────────
print("\n" + "═" * 60)
print("  🎉  TRAINING COMPLETE!")
print("═" * 60)
print(f"  Dataset     : {CSV_PATH.name}")
print(f"  Features    : {AVAILABLE_FEATURES}")
print(f"  Train rows  : {len(X_train):,}")
print(f"  Test rows   : {len(X_test):,}")
print(f"\n  SOH Model  → R² = {metrics_soh['r2']:.4f}  |  MAE = {metrics_soh['mae']:.4f}")
print(f"  Risk Model → R² = {metrics_risk['r2']:.4f}  |  MAE = {metrics_risk['mae']:.4f}")
print(f"\n  Saved files:")
print(f"    📦  battery_model.pkl       (SOH predictor)")
print(f"    📦  battery_risk_model.pkl  (Degradation Risk predictor)")
print(f"    📦  battery_model_meta.pkl  (Metadata for FastAPI)")
print("═" * 60 + "\n")
