
import logging
from typing import Dict, Optional, Any

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:
    yf = None
    logger.warning(
        "yfinance not available: network fetch functions will return empty results. Install with 'pip install yfinance'"
    )

def fetch_price_history(
    ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d"
) -> pd.DataFrame:
    """Download price history for a ticker using yfinance.

    Returns a DataFrame with Date index and columns: Open, High, Low, Close, Adj Close, Volume.
    If no data is returned by yfinance, an empty DataFrame is returned and a warning is logged.
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")
    if start is None:
        start = (datetime.today() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")

    if yf is None:
        logger.warning("fetch_price_history: yfinance not installed; returning empty DataFrame for %s", ticker)
        cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        return pd.DataFrame(columns=cols)

    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
    if isinstance(df, pd.DataFrame) and df.empty:
        logger.warning("fetch_price_history: no price history returned for %s", ticker)
        # return an empty dataframe with expected columns where possible
        cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        return pd.DataFrame(columns=cols)

    if isinstance(df.columns, pd.MultiIndex):
        # In case yfinance returns multi-index columns for multiple tickers
        try:
            df = df.xs(ticker, axis=1, level=1, drop_level=True)
        except Exception:
            # fallback: return empty dataframe and log
            logger.warning("fetch_price_history: multi-index unpack failed for %s", ticker)
            return pd.DataFrame()

    df = df.rename_axis("Date").sort_index()
    return df

def fetch_returns(ticker: str, lookback_years: int = 5, freq: str = "M") -> pd.Series:
    """Compute periodic returns for ticker over lookback window.

    freq: 'D', 'W', 'M' (uses resampled Adj Close).
    Returns an empty pd.Series if no price data is available.
    """
    end = datetime.today()
    start = end - timedelta(days=365 * lookback_years + 30)
    px = fetch_price_history(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    if px is None or px.empty:
        logger.warning("fetch_returns: no price history available for %s (lookback=%s years)", ticker, lookback_years)
        return pd.Series(dtype=float, name=ticker)

    # prefer 'Adj Close' when present, otherwise fallback to 'Close'
    adj = px.get("Adj Close") if "Adj Close" in px.columns else px.get("Close")
    if adj is None or adj.dropna().empty:
        logger.warning("fetch_returns: no adjusted/close prices for %s", ticker)
        return pd.Series(dtype=float, name=ticker)

    if freq.upper() == "D":
        series = adj.dropna()
    else:
        series = adj.resample(freq.upper()).last().dropna()

    rets = series.pct_change().dropna()
    rets.name = ticker
    return rets

def fetch_fundamentals(ticker: str) -> Dict[str, Any]:
    """Fetch basic fundamentals via yfinance.

    Returns a dict with keys: shares_outstanding, net_debt, revenue_last_fy,
    ebit_margin_last_fy, tax_rate_est, info. All lookups are guarded and
    missing values are returned as None. Warnings are logged when data is
    absent or incomplete.
    """
    if yf is None:
        logger.warning("fetch_fundamentals: yfinance not installed; returning empty fundamentals for %s", ticker)
        return {
            "shares_outstanding": None,
            "net_debt": None,
            "revenue_last_fy": None,
            "ebit_margin_last_fy": None,
            "tax_rate_est": 0.21,
            "info": {},
        }

    t = yf.Ticker(ticker)
    info: Dict[str, Any] = getattr(t, "info", {}) or {}
    shares_out = info.get("sharesOutstanding")

    # Balance sheet: totalDebt, cash
    bs = getattr(t, "balance_sheet", None)
    cash: Optional[float] = None
    debt: Optional[float] = None

    if isinstance(bs, pd.DataFrame) and not bs.empty:
        # normalize index to strings for safe matching
        try:
            idx = bs.index.to_series().astype(str).str.lower()
            # look for rows containing 'cash'
            cash_rows = bs.loc[idx.str.contains("cash"), :]
            if not cash_rows.empty:
                cash = float(cash_rows.sum(axis=1).max())

            # short/long debt heuristics
            short_rows = bs.loc[idx.str.contains("short"), :] if idx.str.contains("short").any() else pd.DataFrame()
            long_rows = bs.loc[idx.str.contains("long"), :] if idx.str.contains("long").any() else pd.DataFrame()
            short_debt = float(short_rows.sum(axis=1).max()) if not short_rows.empty else None
            long_debt = float(long_rows.sum(axis=1).max()) if not long_rows.empty else None
            if short_debt is not None or long_debt is not None:
                debt = (0.0 if short_debt is None else short_debt) + (0.0 if long_debt is None else long_debt)
        except Exception:
            logger.debug("fetch_fundamentals: balance_sheet parsing failed for %s", ticker)

    if debt is None:
        debt = info.get("totalDebt")
    if cash is None:
        cash = info.get("totalCash")

    net_debt: Optional[float] = None
    if debt is not None and cash is not None:
        try:
            net_debt = float(debt) - float(cash)
        except Exception:
            net_debt = None

    # Income statement for revenue and EBIT margin
    fin = getattr(t, "financials", None)
    revenue: Optional[float] = None
    ebit: Optional[float] = None
    if isinstance(fin, pd.DataFrame) and not fin.empty:
        try:
            fidx = fin.index.to_series().astype(str).str.lower()
            if fidx.str.contains("total revenue").any():
                revenue = fin.loc[fidx.str.contains("total revenue")].iloc[0, 0]
            if fidx.str.contains("ebit").any():
                ebit = fin.loc[fidx.str.contains("ebit")].iloc[0, 0]
        except Exception:
            logger.debug("fetch_fundamentals: financials parsing failed for %s", ticker)

    if revenue is None:
        revenue = info.get("totalRevenue")
    if ebit is None:
        # fallback: operating income
        try:
            if isinstance(fin, pd.DataFrame) and not fin.empty:
                fidx = fin.index.to_series().astype(str).str.lower()
                if fidx.str.contains("operating income").any():
                    ebit = fin.loc[fidx.str.contains("operating income")].iloc[0, 0]
        except Exception:
            pass

    ebit_margin: Optional[float] = None
    if ebit is not None and revenue:
        try:
            ebit_margin = float(ebit) / float(revenue)
        except Exception:
            ebit_margin = None

    # Tax rate approximation: last year's income tax / EBT
    tax_rate: Optional[float] = None
    if isinstance(fin, pd.DataFrame) and not fin.empty:
        try:
            fidx = fin.index.to_series().astype(str).str.lower()
            tax_row = fin.loc[fidx.str.contains("income tax"), :]
            ebt_row = fin.loc[fidx.str.contains("pretax"), :]
            if not tax_row.empty and not ebt_row.empty:
                tax = tax_row.iloc[0, 0]
                ebt = ebt_row.iloc[0, 0]
                if ebt and ebt != 0:
                    tax_rate = max(0.0, min(0.35, float(tax) / float(ebt)))  # clip to [0, 35%]
        except Exception:
            logger.debug("fetch_fundamentals: tax rate parsing failed for %s", ticker)

    if tax_rate is None:
        tax_rate = 0.21  # US default

    result: Dict[str, Any] = {
        "shares_outstanding": shares_out,
        "net_debt": net_debt,
        "revenue_last_fy": revenue,
        "ebit_margin_last_fy": ebit_margin,
        "tax_rate_est": tax_rate,
        "info": info,
    }

    # Log if most key fields are missing
    if shares_out is None and net_debt is None and revenue is None:
        logger.warning("fetch_fundamentals: limited fundamentals for %s; results may be incomplete", ticker)

    return result
