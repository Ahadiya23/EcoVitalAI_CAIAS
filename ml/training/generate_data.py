from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "synthetic_training.csv"


def generate(n_samples: int = 50_000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = pd.DataFrame(
        {
            "aqi": rng.uniform(0, 500, n_samples),
            "pm25": rng.uniform(0, 300, n_samples),
            "pm10": rng.uniform(0, 200, n_samples),
            "o3": rng.uniform(0, 200, n_samples),
            "no2": rng.uniform(0, 200, n_samples),
            "temperature": rng.uniform(-10, 50, n_samples),
            "humidity": rng.uniform(0, 100, n_samples),
            "uv_index": rng.uniform(0, 11, n_samples),
            "tree_pollen": rng.uniform(0, 100, n_samples),
            "grass_pollen": rng.uniform(0, 100, n_samples),
            "weed_pollen": rng.uniform(0, 100, n_samples),
            "wind_speed": rng.uniform(0, 20, n_samples),
            "user_age": rng.integers(5, 91, n_samples),
            "has_asthma": rng.integers(0, 2, n_samples),
            "has_cardiac": rng.integers(0, 2, n_samples),
            "has_allergies": rng.integers(0, 2, n_samples),
            "hour_of_day": rng.integers(0, 24, n_samples),
            "day_of_week": rng.integers(0, 7, n_samples),
        }
    )
    asthma = ((data["aqi"] > 150) | (data["pm25"] > 75)) & (data["has_asthma"] == 1)
    heat = (data["temperature"] > 38) & ((data["user_age"] > 60) | (data["humidity"] > 80))
    allergy = ((data["tree_pollen"] > 60) | (data["grass_pollen"] > 50)) & (
        data["has_allergies"] == 1
    )
    cardiac = ((data["aqi"] > 200) | (data["temperature"] > 40)) & (data["has_cardiac"] == 1)
    data["asthma_risk"] = asthma.astype(int)
    data["heat_risk"] = heat.astype(int)
    data["allergy_risk"] = allergy.astype(int)
    data["cardiac_risk"] = cardiac.astype(int)
    score = (
        (data["asthma_risk"] * 30 + data["heat_risk"] * 25 + data["allergy_risk"] * 20 + data["cardiac_risk"] * 35) / 2
        + np.minimum(data["aqi"] / 5, 20)
        + rng.normal(0, 5, n_samples)
    )
    data["overall_risk_score"] = np.clip(score, 0, 100)
    return data


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} samples to {OUTPUT}")
