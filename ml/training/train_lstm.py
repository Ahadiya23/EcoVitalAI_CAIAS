from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "synthetic_training.csv"
MODEL_PATH = BASE / "models" / "lstm_forecaster.pt"


class LSTMForecaster(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=18,
            hidden_size=128,
            num_layers=2,
            dropout=0.2,
            batch_first=True,
        )
        self.linear = nn.Linear(128, 24)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.linear(out[:, -1, :])


def build_sequences(features: np.ndarray, target: np.ndarray):
    X, y = [], []
    for i in range(6, len(features) - 24):
        X.append(features[i - 6 : i])
        y.append(target[i : i + 24])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH)
    features = df.iloc[:, :18].values
    target = df["overall_risk_score"].values
    X, y = build_sequences(features, target)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=256,
        shuffle=True,
    )
    model = LSTMForecaster()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)

    model.train()
    for epoch in range(100):
        running = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            preds = model(xb)
            loss = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            running += float(loss.item())
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch + 1}/100 loss={running/len(train_loader):.4f}")

    model.eval()
    with torch.no_grad():
        preds = model(torch.from_numpy(X_test)).numpy()
    mae = float(np.mean(np.abs(preds - y_test)))
    rmse = float(np.sqrt(np.mean((preds - y_test) ** 2)))
    print("MAE:", mae)
    print("RMSE:", rmse)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Saved LSTM to {MODEL_PATH}")
