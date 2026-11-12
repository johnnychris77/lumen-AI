"""A tiny, deterministic pure-Python one-vs-rest logistic-regression classifier.

Used only as the research head over frozen embeddings (and over the baseline
Pillow features for a fair comparison). Deterministic: zero-initialised weights +
full-batch gradient descent, no randomness — so a given dataset reproduces
identical weights. This is intentionally minimal; it is not a clinical model.
"""
from __future__ import annotations

import math


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


class ResearchClassifier:
    def __init__(self, classes: list[str], *, epochs: int = 200, lr: float = 0.5):
        self.classes = list(dict.fromkeys(classes))
        self.epochs = epochs
        self.lr = lr
        self.weights: dict[str, list[float]] = {}
        self.bias: dict[str, float] = {}
        self.dim = 0

    def fit(self, X: list[list[float]], y: list[str]) -> "ResearchClassifier":
        if not X:
            raise ValueError("No training rows.")
        self.dim = len(X[0])
        for cls in self.classes:
            w = [0.0] * self.dim
            b = 0.0
            targets = [1.0 if label == cls else 0.0 for label in y]
            n = len(X)
            for _ in range(self.epochs):
                gw = [0.0] * self.dim
                gb = 0.0
                for xi, ti in zip(X, targets):
                    pred = _sigmoid(sum(w[j] * xi[j] for j in range(self.dim)) + b)
                    err = pred - ti
                    for j in range(self.dim):
                        gw[j] += err * xi[j]
                    gb += err
                for j in range(self.dim):
                    w[j] -= self.lr * gw[j] / n
                b -= self.lr * gb / n
            self.weights[cls] = w
            self.bias[cls] = b
        return self

    def _scores(self, x: list[float]) -> dict[str, float]:
        return {
            cls: _sigmoid(sum(self.weights[cls][j] * x[j] for j in range(self.dim)) + self.bias[cls])
            for cls in self.classes
        }

    def predict(self, X: list[list[float]]) -> list[str]:
        preds = []
        for x in X:
            scores = self._scores(x)
            preds.append(max(scores, key=scores.get))
        return preds


def accuracy(y_true: list[str], y_pred: list[str]) -> float | None:
    if not y_true:
        return None
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return round(correct / len(y_true), 4)
