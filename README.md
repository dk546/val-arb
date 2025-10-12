# val-arb — Company Valuation (DCF + Multiples) with Streamlit

A practical valuation tool that fetches data (Yahoo Finance), estimates discount rates (CAPM / beta regression), builds FCFF-based DCFs, and shows implied multiples — all in a friendly Streamlit UI.

## Features (v0)
- Ticker input → data fetch via `yfinance`
- FCFF & WACC computation
- Simple DCF + terminal value
- EV → Equity → implied price
- Implied EV/EBITDA, EV/EBIT, P/E

## Roadmap
- [ ] Beta regression vs index
- [ ] Driver-based multi-year FCFF forecast
- [ ] r–g sensitivity table
- [ ] Peer-multiple comparison
- [ ] Export to Excel/CSV
- [ ] Caching & error handling

## Dev Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py   # after code is added
```