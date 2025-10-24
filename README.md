# val-arb — Company Valuation (DCF + Multiples) with Streamlit

A practical valuation tool that fetches data (Yahoo Finance), estimates discount rates (CAPM / beta regression), builds FCFF-based DCFs, and shows implied multiples — all in a friendly Streamlit UI.

##  Live Demo
 **[View on Render](https://val-arb-dcf.onrender.com)**


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
````markdown
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

## Troubleshooting

If you see "ModuleNotFoundError: No module named 'app'" when running the Streamlit app, ensure you're running from the repository root. Either set PYTHONPATH to the repo root or run Streamlit via python -m so package import paths resolve:

```powershell
# from the repo root
$env:PYTHONPATH = (Get-Location)
streamlit run streamlit_app/home.py

# or
python -m streamlit run streamlit_app/home.py
```

````