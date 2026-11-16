# Parity · Capital lens

A Streamlit app for the international cost of capital assignment. It compares equity costs, pretax and after-tax debt costs, and WACC in USD and a selected country's currency. The existing Parity RER app is separate and unchanged.

## Run

Python 3.12 recommended.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

Create a new GitHub repository and upload this folder's contents, including `.streamlit/config.toml` and `data/snapshot.json`. Keep `app.py`, `requirements.txt`, and `README.md` at repository root. In Streamlit Community Cloud choose the repository, branch `main`, entrypoint `app.py`, and Python 3.12. No API key or secrets are required.

## Defaults and controls

Software (System & Application); United States; U.S. project tax; ERP 6.5%; debt share 30%. Choose any country. Where source coverage is missing, enter the missing yield/tax manually; no missing value is inferred. Overrides are scoped by industry/country and turning them off restores fetched values. The two government yields can be overridden independently, even for a U.S.–U.S. scenario.

## Economics

Rates below are decimals, not percentages.

```
D/E = d / (1-d)
beta_E = beta_U * [1 + (1-tax)*D/E]
Re_USD = Rf_USD + beta_E*ERP
Rd_USD = Rf_USD + spread_USD
F = (1+Rf_foreign)/(1+Rf_USD)
Re_foreign = (1+Re_USD)*F - 1
spread_foreign_auto = spread_USD*F
Rd_foreign = Rf_foreign + spread_foreign_effective
WACC_currency = (1-d)*Re_currency + d*Rd_currency*(1-tax)
```

A foreign spread override affects only foreign debt and WACC. WACC is built separately by currency, not converted directly as a gross rate. Government yields are risk-free proxies; no extra country equity premium is added. The model assumes zero debt beta, fully usable interest deductions, equal real rates and relative PPP. Match cash-flow and discount-rate currencies.

Class authority: Sergio Rebelo, CasePacket2026-part9, slides 564–587. The Colombia example gives USD WACC 8.5265% and COP WACC 16.0670%.

## Sources and resilience

- Damodaran U.S. industry workbook: `Industry Averages`, exact **Unlevered beta** column (not the cash-corrected beta). The workbook's own update date is preserved.
- Damodaran ratings table: **Baa2/BBB**, first table, large nonfinancial firms; percentage spread converted to decimal.
- OECD DSD_TAX_CIT / DF_CIT 2.0: combined statutory corporate rate, standard targeting, general government, percentage income tax, nonapplicable dividend/rate-structure/tax-base dimensions. Latest nonmissing observation per country, no future-year data. This updates the assignment's older 2024 report.
- Trading Economics: public country-list government-bond-10y table. Its main `/bonds` page is dynamically loaded; the country-list table exposes the same indicator without a key. The source reference may only contain month/year. Do not interpret the retrieval timestamp as an exact market observation date.

Initial page load attempts all sources (one-hour cache). Refresh fetches all four concurrently. If one fails, its last successful value and date remain, accompanied by a warning; successful sources still update. The committed snapshot permits operation during source outages. Run `python sources.py` to update that snapshot, with all-source validation before replacement. Live Streamlit refreshes remain in session memory.

All-industry comparisons retain each source beta even when the selected project's beta is overridden. CSV/JSON exports retain precision and assumptions. Displayed rates use two decimal places; beta uses four. Percentage input controls may follow browser locale.

## Verification

```sh
CAPITAL_OFFLINE=1 python -m unittest test_app
```

On Windows PowerShell set `$env:CAPITAL_OFFLINE='1'` first. Eleven tests cover the independent decimal calculation, class benchmark, equal yields, zero debt, override isolation, invalid/nonfinite inputs, negative yields, failed-refresh preservation, parser rejection, defaults and missing-data interaction. Desktop/mobile screenshots and submission materials live outside the repository in the assignment's `Verification` and `Submission` folders.

## Layout

- `app.py`: responsive interface and exports
- `finance.py`: pure calculation engine
- `sources.py`: validated live importers and snapshot refresh
- `data/snapshot.json`: public-source fallback and provenance
- `test_app.py`: economic and interaction checks
- `.streamlit/config.toml`: white/teal theme consistent with Parity RER
- `PROMPTS.md`: AI collaboration record
