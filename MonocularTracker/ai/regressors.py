"""
Regressor wrappers: Polynomial regression & MLPRegressor for mapping (nx, ny) -> (x, y).
"""
from __future__ import annotations

from typing import List, Tuple

try:
    import numpy as np  # type: ignore
    from sklearn.neural_network import MLPRegressor  # type: ignore
    from sklearn.preprocessing import PolynomialFeatures  # type: ignore
    from sklearn.linear_model import LinearRegression  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore
    MLPRegressor = None  # type: ignore
    PolynomialFeatures = None  # type: ignore
    LinearRegression = None  # type: ignore


class PolyRegressor:
    def __init__(self, degree: int = 3):
        if PolynomialFeatures is None or LinearRegression is None:
            raise RuntimeError("scikit-learn not installed.")
        self.degree = degree
        self.poly = PolynomialFeatures(degree=self.degree, include_bias=False)
        self.lr = LinearRegression()

    def fit(self, X: List[Tuple[float, float]], y: List[Tuple[int, int]]):
        X_arr = np.array(X)
        Y_arr = np.array(y)
        X_poly = self.poly.fit_transform(X_arr)
        self.lr.fit(X_poly, Y_arr)

    def predict(self, X: List[Tuple[float, float]]):
        X_arr = np.array(X)
        X_poly = self.poly.transform(X_arr)
        pred = self.lr.predict(X_poly)
        return pred.tolist()


class MLPRegressorWrapper:
    def __init__(self, hidden_layer_sizes=(64, 64)):
        if MLPRegressor is None:
            raise RuntimeError("scikit-learn not installed.")
        self.model = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation="relu",
            solver="adam",
            max_iter=500,
            random_state=42,
        )

    def fit(self, X: List[Tuple[float, float]], y: List[Tuple[int, int]]):
        X_arr = np.array(X)
        Y_arr = np.array(y)
        self.model.fit(X_arr, Y_arr)

    def predict(self, X: List[Tuple[float, float]]):
        X_arr = np.array(X)
        pred = self.model.predict(X_arr)
        return pred.tolist()
