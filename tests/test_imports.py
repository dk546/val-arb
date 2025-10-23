import os
import sys
import pytest

import pandas as pd

# Ensure the repository root is on sys.path so `import app.*` resolves when tests
# are run from different CWDs / test runners.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _ensure_fake_yfinance():
    """If yfinance is not installed in the test environment, inject a minimal
    fake module into sys.modules that provides the small surface `app.data`
    expects (download, Ticker with info/balance_sheet/financials).
    """
    if "yfinance" in sys.modules:
        return
    try:
        import yfinance  # type: ignore
    except Exception:
        import types

        yf = types.ModuleType("yfinance")

        import pandas as _pd

        def download(ticker, start=None, end=None, interval=None, auto_adjust=False, progress=False):
            # return an empty DataFrame to simulate no data
            return _pd.DataFrame()

        class Ticker:
            def __init__(self, ticker):
                self.ticker = ticker
                self.info = {}
                self.balance_sheet = _pd.DataFrame()
                self.financials = _pd.DataFrame()

        yf.download = download
        yf.Ticker = Ticker
        sys.modules["yfinance"] = yf




def test_import_app_modules():
    # basic import smoke tests
    _ensure_fake_yfinance()
    import app.data as data
    import app.rates as rates
    import app.fcff as fcff
    import app.dcf as dcf

    # verify public symbols exist
    assert hasattr(data, "fetch_price_history")
    assert hasattr(data, "fetch_returns")
    assert hasattr(data, "fetch_fundamentals")
    assert hasattr(rates, "compute_beta")
    assert hasattr(rates, "expected_return_capm")
    assert hasattr(fcff, "ForecastInputs")
    assert hasattr(fcff, "project_drivers")
    assert hasattr(dcf, "enterprise_value")


def test_fetch_returns_no_network():
    """Call fetch_returns with a nonsense ticker that will not make network calls in this test environment.

    This test is conservative: if yfinance is present and attempts a network call,
    the test will be skipped to avoid flakiness.
    """
    import importlib

    data = importlib.import_module("app.data")

    # if yfinance is not installed, fetch_returns will still be importable and
    # return an empty Series for missing data; otherwise skip network behavior.
    try:
        import yfinance  # type: ignore
    except Exception:
        # safe to call the function — expecting empty Series
        s = data.fetch_returns("__NO_SUCH_TICKER__", lookback_years=1, freq="M")
        assert isinstance(s, pd.Series)
        return

    # if yfinance is installed, avoid making real network requests in CI
    pytest.skip("yfinance present — skipping network-dependent fetch_returns test")


def test_project_drivers_pure_function():
    import app.fcff as fcff

    # create a minimal ForecastInputs; uses deterministic numbers and should not require network
    fi = fcff.ForecastInputs(
        revenue_start=100.0,
        revenue_growth=0.05,
        years=3,
        ebit_margin=0.2,
        tax_rate=0.21,
        sales_to_capital=2.0,
        wc_pct_sales=0.05,
        da_pct_sales=0.02,
        capex_pct_sales=0.03,
    )
    df = fcff.project_drivers(fi)
    assert isinstance(df, pd.DataFrame)
    assert "FCFF" in df.columns


def test_dcf_pure_functions():
    import app.dcf as dcf

    # call enterprise_value on a small cashflow series
    fcff_series = [10.0, 11.0, 12.0]
    ev = dcf.enterprise_value(fcff_series, wacc_rate=0.08, tv_g=0.02, tv_method="gordon")
    assert isinstance(ev, float)
    eq = dcf.equity_value(ev, net_debt=0.0)
    assert isinstance(eq, float)
