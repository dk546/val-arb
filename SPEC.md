# Val-Arb DCF Sandbox — Agent Spec (v0)

Purpose
- Define a minimal, reliable DCF sandbox implemented as an importable Python package with a Streamlit UI.
- Focus on a clean, testable codebase that runs locally without API keys and handles sparse/missing data sensibly.

Goals (summary)
- Data: yfinance for price/returns + fundamentals
- Rates: simple regression for beta, CAPM, WACC
- FCFF: driver-based forecast (revenue → margins → NWC → capex)
- DCF: explicit forecast PV + Gordon terminal value; derive EV → Equity → per-share
- Streamlit: sidebar inputs, primary metrics, FCFF table, sensitivity grid

Non-Goals (v0)
- Peer multiples, plotting/charts, caching, auth, DB, API keys

Project layout (importable package)
- valarb/
    - __init__.py
    - data/
        - fetch.py            # yfinance wrappers, sane defaults
        - clean.py            # cleaning + imputation utilities
    - finance/
        - rates.py            # beta regression, CAPM, WACC
        - fcff.py             # FCFF drivers & forecast
        - dcf.py              # PV, terminal value, EV→Equity
    - ui/
        - streamlit_app/
            - home.py           # entrypoint for streamlit run
    - types.py              # common public datatypes (TypedDict / dataclasses)
    - utils.py              # small helpers, validation, warnings
- tests/
    - test_fetch.py
    - test_rates.py
    - test_fcff.py
    - test_dcf.py
- README.md
- requirements.txt
- pyproject.toml / setup.cfg

Minimal requirements (requirements.txt)
- streamlit
- yfinance
- pandas
- numpy
- scipy
- python-dotenv (optional, but not for API keys)
- dev: pytest, black, mypy, isort
(Keep dependencies minimal; prefer numpy/pandas + scipy over heavy libs.)

Public API surface (examples with types)
- data.fetch.fetch_ticker_history(ticker: str, period: str = "5y") -> pandas.DataFrame
- data.fetch.fetch_fundamentals(ticker: str) -> dict
- data.clean.sanitize_prices(prices: pd.DataFrame) -> pd.DataFrame
- finance.rates.estimate_beta(returns_i: pd.Series, returns_m: pd.Series) -> float
- finance.rates.capm_cost_of_equity(rf: float, beta: float, rm: float) -> float
- finance.rates.compute_wacc(equity_value: float, debt_value: float, re: float, rd: float, tax_rate: float) -> float
- finance.fcff.forecast_fcff(base: dict, drivers: dict, years: int = 5) -> pd.DataFrame
- finance.dcf.discount_cashflows(fcff_df: pd.DataFrame, wacc: float) -> dict
- ui.streamlit_app.launch() -> None (called by streamlit run)

Key behavior rules
- No hard-coded file paths; use resources relative to package and user-provided paths
- Handle sparse data:
    - If fundamentals missing, warn in UI and fall back to conservative defaults (e.g., long-term revenue growth 2–3%, margin = median sector or 5%)
    - If price history < 2 years, warn and use available history but widen confidence / use default beta = 1.0
    - Document all defaults in README and show them in the UI sidebar
- Regression for beta:
    - Use log returns or arithmetic returns consistently (document choice). Default: arithmetic daily returns aggregated to monthly.
    - Use numpy.polyfit / OLS from scipy for minimal deps; return beta and R^2
- WACC:
    - Compute market equity from latest price * shares outstanding (if shares missing, require user input)
    - Debt from balance sheet (short+long), use interest expense to derive rd if not directly available; default rd = 4%
- FCFF drivers:
    - Revenue growth drivers: explicit for years 1..N then fade to terminal growth
    - Margins (EBIT margin), tax rate, capex as % revenue, change in NWC as % revenue
    - Allow user override for all driver inputs in Streamlit sidebar
- DCF:
    - Discount explicit FCFF by WACC (or user-selected discount rate)
    - Terminal value: Gordon growth (TV = FCFF_last * (1+g) / (WACC - g)), validate WACC > g + small epsilon
    - Enterprise value = PV(FCFF) + PV(TV)
    - Equity value = EV - Net Debt
    - Per-share = Equity value / shares_outstanding (require/share prompt if missing)

Streamlit UI (home.py) — essential elements
- Sidebar:
    - Ticker input
    - History period selector
    - Forecast horizon (3–10 years)
    - Terminal g (%)
    - Discount rate override / compute via CAPM+WACC toggle
    - Driver overrides: revenue growth per year or single driver + fade, margins, capex %, NWC %
    - Shares outstanding (auto-populate or manual)
    - Run / Reset buttons
- Main area:
    - Top line: ticker summary (price, market cap, shares, net debt)
    - Warnings banner for sparse or imputed data
    - Key outputs: per-share valuation, EV, Equity, implied growth/margins
    - FCFF table (years, revenue, ebit, tax, capex, change NWC, FCFF, discount factor, PV)
    - Sensitivity grid: per-share value as function of terminal g (rows) vs WACC/COE (cols) — downloadable CSV
    - Download buttons: CSV of FCFF table, JSON of model inputs

Testing & Quality
- Minimal unit tests cover:
    - fetch functions with mocked yfinance
    - beta estimation on synthetic data
    - FCFF generation given deterministic drivers
    - DCF math invariants (PV sums to expected)
- Linting:
    - Black default, type hints on public functions, mypy in CI
- Acceptance:
    - streamlit run streamlit_app/home.py runs without import errors
    - Project importable as valarb and public functions testable
    - README Quickstart demonstrates running streamlit locally

Error handling & messaging
- Prefer non-fatal warnings in the UI when falling back to defaults
- Explicit error messages for fatal conditions:
    - Missing shares_outstanding when required for per-share valuation
    - WACC <= terminal growth (with guidance to change inputs)
- Log internal warnings via python logging; surface user-friendly messages in Streamlit

Documentation (README.md quickstart)
- Install: python -m venv .venv; pip install -r requirements.txt
- Run: streamlit run valarb/ui/streamlit_app/home.py (or streamlit run streamlit_app/home.py when working dir is package root)
- Short explanation of defaults and where to change inputs
- Notes on data freshness and limitations

Developer notes
- Keep functions small, pure where possible, and well-typed
- Avoid heavy external ML/stat packages unless necessary
- Design for easy extension (peer multiples, charts, caching) in v1

Checklist to ship v0
- [ ] Package module structure implemented
- [ ] streamlit_app/home.py loads without import errors
- [ ] Basic end-to-end: fetch ticker → compute beta → FCFF → DCF → per-share
- [ ] UI shows warnings and allows driver overrides
- [ ] Unit tests for core math and data handling
- [ ] README Quickstart and requirements.txt added
- [ ] Black formatting and minimal type hints applied

Notes on sensible defaults (examples)
- Default history: 5y daily
- Minimum data length for regression: 24 monthly observations; else set beta = 1 and warn
- Default terminal g: 2.5%
- Default tax rate: 21% (US) unless fundamentals provide statutory rate
- Default rd: 4% if interest data absent

Accepted function signatures (copyable)
- def fetch_ticker_history(ticker: str, period: str = "5y") -> "pd.DataFrame": ...
- def estimate_beta(returns_i: "pd.Series", returns_m: "pd.Series") -> tuple[float, float]: ...
- def forecast_fcff(base: dict, drivers: dict, years: int = 5) -> "pd.DataFrame": ...
- def discount_cashflows(fcff_df: "pd.DataFrame", discount_rate: float) -> dict: ...

This spec is intentionally minimal and prescriptive on critical behaviors (defaults, warnings, importability, Streamlit UI) while leaving implementation details open for developer discretion.