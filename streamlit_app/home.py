import os
import sys

# Minimal defensive PYTHONPATH fallback so `from app.* import ...` works when
# running via the VS Code debugger or Streamlit launcher without PYTHONPATH set.
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import numpy as np
from app.data import fetch_returns, fetch_fundamentals
from app.rates import compute_beta, expected_return_capm, wacc
from app.fcff import ForecastInputs, project_drivers
from app.dcf import enterprise_value, equity_value, per_share, sensitivity_table

st.set_page_config(page_title="Val-Arb: DCF Sandbox", layout="wide")

st.title("Val-Arb: DCF Sandbox")
with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker", value="AAPL")
    market = st.text_input("Market Index", value="^GSPC")
    lookback = st.slider("Beta Lookback (years)", 2, 10, 5)
    freq = st.selectbox("Return Frequency", ["M","W","D"], index=0)
    rf = st.number_input("Risk-free rate (annual, decimal)", value=0.04, step=0.005, format="%.3f")
    erp_manual = st.number_input("Equity risk premium (if blank, estimate)", value=0.05, step=0.005, format="%.3f")
    use_manual_erp = st.checkbox("Use manual ERP", value=True)

    st.markdown("---")
    st.subheader("Forecast")
    years = st.slider("Horizon (years)", 3, 10, 5)
    revenue_start = st.number_input("Starting Revenue (last FY)", value=400_000_000_000.0, step=1e9, format="%.0f")
    growth = st.number_input("Revenue Growth (explicit period)", value=0.05, step=0.01, format="%.2f")
    ebit_margin = st.number_input("EBIT Margin", value=0.25, step=0.01, format="%.2f")
    tax_rate = st.number_input("Tax Rate", value=0.21, step=0.01, format="%.2f")
    st.caption("Reinvestment via Sales-to-Capital OR Capex%: choose one realistically (sales-to-capital preferred).")
    st_cols = st.columns(2)
    with st_cols[0]:
        s2c = st.number_input("Sales-to-Capital", value=2.5, step=0.1, format="%.1f")
        wc_pct = st.number_input("Working Capital % of Sales", value=0.05, step=0.01, format="%.2f")
    with st_cols[1]:
        da_pct = st.number_input("D&A % of Sales", value=0.03, step=0.005, format="%.3f")
        capex_pct = st.number_input("Capex % of Sales (fallback)", value=0.03, step=0.005, format="%.3f")

    st.markdown("---")
    st.subheader("Capital Structure")
    equity_weight = st.slider("Equity Weight", 0.0, 1.0, 0.8, step=0.05)
    rd = st.number_input("Pre-tax Cost of Debt", value=0.05, step=0.005, format="%.3f")

    st.markdown("---")
    st.subheader("Terminal / Output")
    g = st.number_input("Terminal Growth (Gordon)", value=0.02, step=0.005, format="%.3f")

run = st.button("Run DCF")

if run:
    with st.spinner("Fetching data & computing..."):
        # Beta & expected return
        beta, alpha = compute_beta(ticker, market=market, lookback_years=lookback, freq=freq)
        if beta is None or (isinstance(beta, float) and np.isnan(beta)):
            st.warning("Not enough return history to estimate beta. Using beta=1.0 as placeholder.")
            beta = 1.0


        erp = erp_manual if use_manual_erp else None
        re = expected_return_capm(beta, rf=rf, erp=erp, market=market, lookback_years=lookback, freq=freq)

        # Fundamentals
        fundamentals = fetch_fundamentals(ticker)
        shares = fundamentals.get("shares_outstanding", None)
        net_debt = fundamentals.get("net_debt", 0.0)

        # warn if fundamentals are incomplete
        missing_fundamentals = []
        if shares is None:
            missing_fundamentals.append("shares_outstanding")
        if net_debt is None:
            missing_fundamentals.append("net_debt")
        if fundamentals.get("revenue_last_fy") is None:
            missing_fundamentals.append("revenue_last_fy")
        if len(missing_fundamentals) > 0:
            st.warning(f"Missing fundamentals: {', '.join(missing_fundamentals)} — defaults/imputations will be used.")

        st.subheader("Rates & Structure")
        col = st.columns(4)
        col[0].metric("Beta", f"{beta:.2f}")
        col[1].metric("Cost of Equity (Re)", f"{re*100:.2f}%")
        col[2].metric("Pre-tax Cost of Debt (Rd)", f"{rd*100:.2f}%")
        w = wacc(equity_weight, re, rd, tax_rate)
        col[3].metric("WACC", f"{w*100:.2f}%")

        st.subheader("Forecast (FCFF)")
        finp = ForecastInputs(
            revenue_start=revenue_start,
            revenue_growth=growth,
            years=years,
            ebit_margin=ebit_margin,
            tax_rate=tax_rate,
            sales_to_capital=s2c,
            wc_pct_sales=wc_pct,
            da_pct_sales=da_pct,
            capex_pct_sales=capex_pct,
        )
        fcff_df = project_drivers(finp)
        st.dataframe(fcff_df.style.format({c: "{:,.0f}" for c in ["Revenue","EBIT","NOPAT","D&A","Reinvestment","ΔNWC","FCFF"]}))

        st.subheader("Valuation")
        ev = enterprise_value(fcff_df["FCFF"].tolist(), wacc_rate=w, tv_g=g, tv_method="gordon")
        eq = equity_value(ev, net_debt=net_debt)
        ps = per_share(eq, shares)

        cols2 = st.columns(3)
        cols2[0].metric("Enterprise Value", f"${ev:,.0f}")
        cols2[1].metric("Equity Value", f"${eq:,.0f}")
        cols2[2].metric("Per Share", f"${ps:,.2f}" if not np.isnan(ps) else "N/A")

        st.subheader("Sensitivity (EV)")
        # build ranges but allow NaN/fallbacks — ensure the table renders
        try:
            w_low = max(0.03, (w - 0.03) if (w is not None and not np.isnan(w)) else 0.06)
        except Exception:
            w_low = 0.03
        try:
            w_high = (w + 0.03) if (w is not None and not np.isnan(w)) else 0.09
        except Exception:
            w_high = 0.09

        try:
            g_low = max(0.0, (g - 0.01) if (g is not None and not np.isnan(g)) else 0.0)
        except Exception:
            g_low = 0.0
        try:
            g_high = (g + 0.01) if (g is not None and not np.isnan(g)) else 0.03
        except Exception:
            g_high = 0.03

        wacc_vals = np.round(np.linspace(w_low, w_high, 5), 4)
        g_vals = np.round(np.linspace(g_low, g_high, 5), 4)
        # sensitivity_table is resilient to NaNs in inputs; ensure we coerce to lists
        sens = sensitivity_table(fcff_df["FCFF"].tolist(), wacc_vals.tolist(), g_vals.tolist())
        # show table even if some values are NaN
        st.dataframe(sens.fillna("N/A").style.format("{:,.0f}"))

        st.caption("Note: Data via yfinance; fundamentals coverage can vary. This is an educational sandbox, not investment advice.")
else:
    st.info("Set your inputs and click **Run DCF**. Try AAPL, MSFT, NVDA, etc.")