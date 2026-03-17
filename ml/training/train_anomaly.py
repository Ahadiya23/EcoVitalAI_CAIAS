from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "synthetic_training.csv"
MODEL_PATH = BASE / "models" / "anomaly_detector.pkl"


if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH)
    X = df.iloc[:, :18].values
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved anomaly detector to {MODEL_PATH}")
