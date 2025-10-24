
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from .data import fetch_returns

def compute_beta(ticker: str, market: str = "^GSPC", lookback_years: int = 5, freq: str = "M") -> Tuple[float, float]:
    """Estimate beta via OLS of asset returns on market returns.
    Returns (beta, alpha) using simple regression without intercept constraints.
    """
    r_i = fetch_returns(ticker, lookback_years=lookback_years, freq=freq)
    r_m = fetch_returns(market, lookback_years=lookback_years, freq=freq)
    df = pd.concat([r_i, r_m], axis=1, join="inner").dropna()
    df.columns = ["ri", "rm"]
    if len(df) < 12:
        return (np.nan, np.nan)
    x = np.c_[np.ones(len(df)), df["rm"].values]
    y = df["ri"].values
    # OLS: beta_hat = (X'X)^{-1} X'y
    xtx = x.T @ x
    xty = x.T @ y
    coef = np.linalg.inv(xtx) @ xty
    alpha, beta = coef[0], coef[1]
    return float(beta), float(alpha)

def expected_return_capm(beta: float, rf: float, erp: Optional[float] = None, market: str = "^GSPC", lookback_years: int = 5, freq: str = "M") -> float:
    """CAPM expected return. If erp not provided, estimate from history."""
    if erp is None:
        r_m = fetch_returns(market, lookback_years=lookback_years, freq=freq).mean() * (12 if freq.upper() == "M" else 252 if freq.upper() == "D" else 52)
        erp = r_m - rf
    return rf + beta * erp

def wacc(equity_weight: float, re: float, rd: float, tax_rate: float) -> float:
    equity_weight = np.clip(equity_weight, 0.0, 1.0)
    debt_weight = 1.0 - equity_weight
    return equity_weight * re + debt_weight * rd * (1 - tax_rate)
