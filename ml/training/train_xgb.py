from pathlib import Path

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from xgboost import XGBClassifier

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "synthetic_training.csv"
MODEL_PATH = BASE / "models" / "risk_classifier.pkl"
LABELS = ["asthma_risk", "heat_risk", "allergy_risk", "cardiac_risk"]


def load_data():
    df = pd.read_csv(DATA_PATH)
    X = df.iloc[:, :18].values
    y = df[LABELS].values
    return train_test_split(X, y, test_size=0.2, random_state=42)


def objective(trial: optuna.Trial, X_train, X_test, y_train, y_test):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "eval_metric": "logloss",
        "tree_method": "hist",
    }
    model = MultiOutputClassifier(XGBClassifier(**params))
    model.fit(X_train, y_train)
    probs = np.column_stack([est.predict_proba(X_test)[:, 1] for est in model.estimators_])
    aucs = [roc_auc_score(y_test[:, i], probs[:, i]) for i in range(y_test.shape[1])]
    return float(np.mean(aucs))


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = load_data()
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, X_train, X_test, y_train, y_test), n_trials=30)

    best = study.best_params | {"eval_metric": "logloss", "tree_method": "hist"}
    model = MultiOutputClassifier(XGBClassifier(**best))
    model.fit(X_train, y_train)
    probs = np.column_stack([est.predict_proba(X_test)[:, 1] for est in model.estimators_])
    aucs = [roc_auc_score(y_test[:, i], probs[:, i]) for i in range(y_test.shape[1])]
    print("ROC-AUC per label:", dict(zip(LABELS, aucs)))
    print("Macro ROC-AUC:", float(np.mean(aucs)))

    names = [
        "aqi", "pm25", "pm10", "o3", "no2", "temperature", "humidity",
        "uv_index", "tree_pollen", "grass_pollen", "weed_pollen", "wind_speed",
        "user_age", "has_asthma", "has_cardiac", "has_allergies", "hour_of_day", "day_of_week",
    ]
    for idx, est in enumerate(model.estimators_):
        importances = est.feature_importances_
        top_idx = np.argsort(importances)[-5:][::-1]
        print(f"Top 5 features for {LABELS[idx]}:", [(names[i], float(importances[i])) for i in top_idx])

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved classifier to {MODEL_PATH}")
