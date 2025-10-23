
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Optional
import yfinance as yf

def fetch_price_history(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d") -> pd.DataFrame:
    """Download price history for a ticker using yfinance.
    Returns a DataFrame with Date index and columns: Open, High, Low, Close, Adj Close, Volume.
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")
    if start is None:
        start = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        # In case yfinance returns multi-index columns for multiple tickers
        df = df.xs(ticker, axis=1, level=1, drop_level=True)
    df = df.rename_axis("Date").sort_index()
    return df

def fetch_returns(ticker: str, lookback_years: int = 5, freq: str = "M") -> pd.Series:
    """Compute periodic returns for ticker over lookback window. freq: 'D', 'W', 'M' (uses resampled Adj Close)."""
    end = datetime.today()
    start = end - timedelta(days=365*lookback_years + 30)
    px = fetch_price_history(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    if px.empty:
        return pd.Series(dtype=float, name=ticker)
    adj = px.get("Adj Close", px["Close"]).dropna()
    if freq.upper() == "D":
        series = adj
    else:
        series = adj.resample(freq.upper()).last()
    rets = series.pct_change().dropna()
    rets.name = ticker
    return rets

def fetch_fundamentals(ticker: str) -> dict:
    """Fetch basic fundamentals via yfinance: shares outstanding, net debt, tax rate (approx), last FY revenue, EBIT margin.
    Note: yfinance coverage varies; functions handle missing keys gracefully.
    """
    t = yf.Ticker(ticker)
    info = t.info if hasattr(t, "info") else {}
    shares_out = info.get("sharesOutstanding")
    # Balance sheet: totalDebt, cash
    bs = t.balance_sheet
    cash = None
    debt = None
    if isinstance(bs, pd.DataFrame) and not bs.empty:
        # yfinance columns are periods; rows are line items
        cash = bs.loc[bs.index.str.lower().str.contains("cash"), :].sum().max()
        short_debt = bs.loc[bs.index.str.lower().str.contains("short"), :].sum().max() if "short" in "".join(bs.index.str.lower()) else None
        long_debt = bs.loc[bs.index.str.lower().str.contains("long"), :].sum().max() if "long" in "".join(bs.index.str.lower()) else None
        if pd.notna(short_debt) or pd.notna(long_debt):
            debt = (0 if pd.isna(short_debt) else short_debt) + (0 if pd.isna(long_debt) else long_debt)
    if debt is None:
        debt = info.get("totalDebt")
    if cash is None:
        cash = info.get("totalCash")
    net_debt = None
    if debt is not None and cash is not None:
        net_debt = float(debt) - float(cash)

    # Income statement for revenue and EBIT margin
    fin = t.financials
    revenue = None
    ebit = None
    if isinstance(fin, pd.DataFrame) and not fin.empty:
        if any(fin.index.str.lower().str.contains("total revenue")):
            revenue = fin.loc[fin.index.str.lower().str.contains("total revenue")].iloc[0, 0]
        if any(fin.index.str.lower().str.contains("ebit")):
            ebit = fin.loc[fin.index.str.lower().str.contains("ebit")].iloc[0, 0]
    if revenue is None:
        revenue = info.get("totalRevenue")
    if ebit is None:
        # fallback: operating income
        if isinstance(fin, pd.DataFrame) and not fin.empty and any(fin.index.str.lower().str.contains("operating income")):
            ebit = fin.loc[fin.index.str.lower().str.contains("operating income")].iloc[0, 0]

    ebit_margin = None
    if ebit is not None and revenue:
        try:
            ebit_margin = float(ebit) / float(revenue)
        except Exception:
            ebit_margin = None

    # Tax rate approximation: last year's income tax / EBT
    tax_rate = None
    if isinstance(fin, pd.DataFrame) and not fin.empty:
        tax_row = fin.loc[fin.index.str.lower().str.contains("income tax"), :]
        ebt_row = fin.loc[fin.index.str.lower().str.contains("pretax"), :]
        if not tax_row.empty and not ebt_row.empty:
            tax = tax_row.iloc[0, 0]
            ebt = ebt_row.iloc[0, 0]
            if ebt and ebt != 0:
                tax_rate = max(0.0, min(0.35, float(tax) / float(ebt)))  # clip to [0, 35%]
    if tax_rate is None:
        tax_rate = 0.21  # US default

    return {
        "shares_outstanding": shares_out,
        "net_debt": net_debt,
        "revenue_last_fy": revenue,
        "ebit_margin_last_fy": ebit_margin,
        "tax_rate_est": tax_rate,
        "info": info,
    }
