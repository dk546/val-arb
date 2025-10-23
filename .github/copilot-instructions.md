<!-- .github/copilot-instructions.md: guidance for AI coding agents working on val-arb -->
# val-arb — Copilot instructions (concise)

This file tells AI coding assistants how this repo is organized and what patterns to follow so generated changes are immediately useful and consistent.

High-level architecture
- Package: core code lives under `app/` (small importable package style). Key modules:
  - `app/data.py` — yfinance wrappers and fundamental fetchers (use these for any data retrieval).
  - `app/rates.py` — beta estimation, CAPM, WACC helpers (returns floats, simple OLS used).
  - `app/fcff.py` — driver-based FCFF forecast utilities and dataclass `ForecastInputs`.
  - `app/dcf.py` — discounting, terminal value, EV → equity → per-share helpers.
  - `streamlit_app/home.py` — Streamlit UI entrypoint; uses the above modules and demonstrates intended public API and UX patterns.

Why this structure
- Keep finance logic pure and testable in `app/*` and keep the UI thin in `streamlit_app/home.py`. When adding features, prefer extending `app/` and then wire UI controls in `home.py`.

Project-specific conventions
- Public functions return numpy/pandas-native types (floats, pd.DataFrame, pd.Series). Preserve these shapes when editing; tests expect them.
- Defaults and fallbacks are explicit and must be surfaced as UI warnings (see `streamlit_app/home.py` handling of missing beta/shares/net_debt).
- Minimal dependencies: prefer stdlib + pandas/numpy/scipy/yfinance/streamlit. Avoid adding heavy libs unless justified in SPEC.md.
- Numeric rates are decimals (e.g., 0.05 for 5%) across modules — keep units consistent.

Examples to follow (copyable patterns)
- Fetch returns (monthly): use `app.data.fetch_returns(ticker, lookback_years=5, freq='M')` and expect a pd.Series of pct changes.
- Estimate beta: call `app.rates.compute_beta(ticker, market='^GSPC', lookback_years=5, freq='M')` — handle NaN by falling back to beta=1 and emitting a warning.
- Forecast FCFF: construct `ForecastInputs` from `app.fcff` and call `project_drivers(...)` to get a `pd.DataFrame` with columns `['Year','Revenue','EBIT','NOPAT','D&A','Reinvestment','ΔNWC','FCFF']`.
- Discount & TV: use `app.dcf.enterprise_value(fcff_list, wacc_rate, tv_g=...)` and `app.dcf.per_share(equity, shares_outstanding)`; validate WACC > g.

Developer workflows & commands
- Run the Streamlit UI locally from the repo root:
  - streamlit run streamlit_app/home.py
- Create and activate a virtualenv, then install requirements:
  - python -m venv .venv ; .venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
- Tests (not present but expected): add pytest tests under `tests/` mirroring `app/` modules.

Code-style and quality
- Keep functions small and pure in `app/` so they are testable.
- Use logging for internal messages; surface user-friendly warnings in UI.
- Use clear unit shapes and document return types in docstrings (see functions in `app/` for examples).

What to avoid
- Don’t hard-code file paths; use inputs and return values. The spec explicitly forbids hard-coded paths.
- Don’t change the UI layout in `streamlit_app/home.py` without keeping the same sidebar/main split and existing control names (used by integration tests / manual QA).

When proposing changes in PRs
- Include a short rationale referencing SPEC.md or README.md if you change defaults (terminal g, default lookback, tax rate).
- Add/adjust a small unit test for any numerical change (core math in `app/`) showing the previous and new behavior.

If you need data examples for tests
- Use synthetic deterministic inputs (e.g., constant revenue growth and margins) and the `ForecastInputs`/`project_drivers` path to produce deterministic FCFFs.

If anything in this file is unclear, ask for which functions or UX element you should prioritize and include a suggested concrete patch.
