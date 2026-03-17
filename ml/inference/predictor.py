import os
import pickle
import threading
import time
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.multioutput import MultiOutputClassifier

ROOT = Path(__file__).resolve().parents[2]
XGB_PATH = ROOT / "ml" / "models" / "risk_classifier.pkl"
ANOMALY_PATH = ROOT / "ml" / "models" / "anomaly_detector.pkl"
LSTM_PATH = ROOT / "ml" / "models" / "lstm_forecaster.pt"


class LSTMForecaster(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = torch.nn.LSTM(
            input_size=18,
            hidden_size=128,
            num_layers=2,
            dropout=0.2,
            batch_first=True,
        )
        self.linear = torch.nn.Linear(128, 24)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.linear(out[:, -1, :])


class RiskPredictor:
    def __init__(self):
        self.lock = threading.Lock()
        self.classifier = self._load_or_stub_classifier()
        self.anomaly = self._load_or_stub_anomaly()
        self.lstm = self._load_or_stub_lstm()

    def _load_or_stub_classifier(self):
        if XGB_PATH.exists():
            return joblib.load(XGB_PATH)
        return None

    def _load_or_stub_anomaly(self):
        if ANOMALY_PATH.exists():
            return joblib.load(ANOMALY_PATH)
        return None

    def _load_or_stub_lstm(self):
        model = LSTMForecaster()
        if LSTM_PATH.exists():
            model.load_state_dict(torch.load(LSTM_PATH, map_location="cpu"))
        model.eval()
        return model

    def predict(self, feature_vector: np.ndarray):
        with self.lock:
            x = feature_vector.reshape(1, -1)
            if isinstance(self.classifier, MultiOutputClassifier):
                probs = [est.predict_proba(x)[0, 1] for est in self.classifier.estimators_]
            else:
                # Heuristic fallback when no model is trained yet.
                probs = [
                    min(1.0, (x[0, 0] + x[0, 1]) / 600),
                    min(1.0, (x[0, 5] + x[0, 6]) / 150),
                    min(1.0, (x[0, 8] + x[0, 9]) / 200),
                    min(1.0, (x[0, 0] + x[0, 5]) / 700),
                ]
            component_scores = {
                "asthma_risk": float(probs[0]),
                "heat_risk": float(probs[1]),
                "allergy_risk": float(probs[2]),
                "cardiac_risk": float(probs[3]),
            }
            weighted = (
                component_scores["asthma_risk"] * 30
                + component_scores["heat_risk"] * 25
                + component_scores["allergy_risk"] * 20
                + component_scores["cardiac_risk"] * 35
            )
            overall = float(max(0, min(100, weighted)))
            if overall >= 80:
                severity = "critical"
            elif overall >= 60:
                severity = "high"
            elif overall >= 30:
                severity = "medium"
            else:
                severity = "low"
            anomaly_flag = False
            if self.anomaly is not None:
                anomaly_flag = int(self.anomaly.predict(x)[0]) == -1

            from app.models.schemas import RiskPrediction

            return RiskPrediction(
                overall_score=overall,
                component_scores=component_scores,
                severity=severity,
                confidence=float(np.mean(probs)),
                anomaly_flag=anomaly_flag,
                explanation="",
            )

    def forecast_24h(self, seq: np.ndarray) -> list[float]:
        with self.lock:
            x = torch.tensor(seq.reshape(1, 6, 18), dtype=torch.float32)
            with torch.no_grad():
                pred = self.lstm(x).numpy()[0]
        return [float(max(0, min(100, value))) for value in pred]


def model_card_report() -> None:
    predictor = RiskPredictor()
    rng = np.random.default_rng(7)
    samples = rng.random((1000, 18)).astype(np.float32) * 100
    latencies = []
    for sample in samples:
        t0 = time.perf_counter()
        predictor.predict(sample)
        latencies.append((time.perf_counter() - t0) * 1000)
    p50 = float(np.percentile(latencies, 50))
    p99 = float(np.percentile(latencies, 99))
    print("Inference latency p50(ms):", p50)
    print("Inference latency p99(ms):", p99)


if __name__ == "__main__":
    model_card_report()
