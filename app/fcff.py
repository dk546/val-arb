
from dataclasses import dataclass
from typing import List, Dict
import numpy as np
import pandas as pd

@dataclass
class ForecastInputs:
    revenue_start: float
    revenue_growth: float  # annual growth rate for explicit period
    years: int
    ebit_margin: float
    tax_rate: float
    sales_to_capital: float  # how much revenue added per 1 unit of capital (higher => less reinvestment)
    wc_pct_sales: float      # working capital as % of sales
    da_pct_sales: float      # D&A as % of sales (proxy)
    capex_pct_sales: float   # Capex as % of sales (if using % of sales instead of sales_to_capital)

def project_drivers(inp: ForecastInputs) -> pd.DataFrame:
    years = list(range(1, inp.years + 1))
    revenues = [inp.revenue_start * ((1 + inp.revenue_growth) ** t) for t in years]
    ebit = [rev * inp.ebit_margin for rev in revenues]
    nopat = [e * (1 - inp.tax_rate) for e in ebit]
    da = [rev * inp.da_pct_sales for rev in revenues]

    # Reinvestment using sales-to-capital ratio: Reinv = ΔRevenue / Sales-to-Capital
    reinvestment = []
    prev_rev = inp.revenue_start
    for rev in revenues:
        delta_rev = rev - prev_rev
        reinv = (delta_rev / inp.sales_to_capital) if inp.sales_to_capital > 0 else rev * inp.capex_pct_sales
        reinvestment.append(max(0.0, reinv))
        prev_rev = rev

    # ΔNWC based on wc_pct_sales
    nwc = [rev * inp.wc_pct_sales for rev in revenues]
    delta_nwc = [nwc[0] - inp.revenue_start * inp.wc_pct_sales] + [nwc[t] - nwc[t-1] for t in range(1, len(nwc))]

    fcff = [nopat[t] + da[t] - reinvestment[t] - delta_nwc[t] for t in range(len(years))]

    df = pd.DataFrame({
        "Year": years,
        "Revenue": revenues,
        "EBIT": ebit,
        "NOPAT": nopat,
        "D&A": da,
        "Reinvestment": reinvestment,
        "ΔNWC": delta_nwc,
        "FCFF": fcff
    })
    return df
