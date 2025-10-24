
from typing import Dict, Literal, Optional
import numpy as np
import pandas as pd

def discount_cash_flows(cash_flows, rate):
    years = np.arange(1, len(cash_flows) + 1)
    return np.sum(np.array(cash_flows) / ((1 + rate) ** years))

def terminal_value(last_cash_flow: float, rate: float, g: float, method: Literal["gordon","exit_multiple"]="gordon", exit_multiple: Optional[float]=None) -> float:
    if method == "gordon":
        if rate <= g:
            raise ValueError("Discount rate must exceed terminal growth for Gordon model.")
        return last_cash_flow * (1 + g) / (rate - g)
    elif method == "exit_multiple":
        if exit_multiple is None:
            raise ValueError("exit_multiple must be provided for exit multiple method.")
        return last_cash_flow * exit_multiple
    else:
        raise ValueError("Unknown method")

def enterprise_value(fcff_series, wacc_rate, tv_g: Optional[float]=None, tv_method: str="gordon", exit_multiple: Optional[float]=None):
    pv_explicit = discount_cash_flows(fcff_series, wacc_rate)
    tv = 0.0
    if tv_method == "gordon" and tv_g is not None:
        tv = terminal_value(fcff_series[-1], wacc_rate, tv_g, method="gordon")
    elif tv_method == "exit_multiple" and exit_multiple is not None:
        tv = terminal_value(fcff_series[-1], wacc_rate, 0.0, method="exit_multiple", exit_multiple=exit_multiple)
    pv_tv = tv / ((1 + wacc_rate) ** len(fcff_series))
    return pv_explicit + pv_tv

def equity_value(ev: float, net_debt: Optional[float], minority_interest: float = 0.0, cash_adjustment: float = 0.0) -> float:
    if net_debt is None:
        net_debt = 0.0
    return ev - net_debt - minority_interest + cash_adjustment

def per_share(equity_val: float, shares_outstanding: Optional[float]) -> float:
    if not shares_outstanding or shares_outstanding <= 0:
        return np.nan
    return equity_val / shares_outstanding

def sensitivity_table(fcff_series, wacc_vals, g_vals):
    out = []
    for w in wacc_vals:
        row = {"WACC": w}
        for g in g_vals:
            try:
                ev = enterprise_value(fcff_series, w, tv_g=g, tv_method="gordon")
            except Exception:
                ev = np.nan
            row[g] = ev
        out.append(row)
    return pd.DataFrame(out).set_index("WACC")
