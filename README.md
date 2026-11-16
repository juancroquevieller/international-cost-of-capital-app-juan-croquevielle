# Parity · Capital lens

[Live app](https://parity-capital-juan-croquevielle.streamlit.app/)

Compare project equity costs, debt costs and WACC in the currencies of any two selected countries. A **Total Market** option and a benchmark under each result provide a broad business-risk comparison. The separate Parity RER app is unchanged.

## Run and deploy

Python 3.12 recommended. Install with `python -m pip install -r requirements.txt`, then run `streamlit run app.py`. Streamlit Community Cloud uses branch `main`, entrypoint `app.py`; no API keys or secrets. Keep `.streamlit/config.toml` and `data/snapshot.json` in the repository.

## Defaults and controls

Software (System & Application), United States in both country selectors, U.S. project tax, 6.5% ERP, and 30% debt financing retain the assignment defaults. Either country can be changed. **Class method** (default) uses one project tax from the U.S. or either selected country in both columns. **Project location** uses each country’s own OECD tax rate, with independent manual overrides, for both relevering equity beta and calculating its interest tax shield. The industry beta, debt share, ERP and USD borrowing benchmark remain shared. Missing country taxes are never replaced by U.S. tax. Missing yields/taxes require manual entry.

The U.S. reference yield, USD BBB spread, beta and tax can be overridden. Each non-U.S. selected-country yield and each side's borrowing spread can be overridden independently. A selected United States always shares the U.S. reference yield. Spread overrides affect only their own side's debt cost and WACC. Turning an override off restores the source or automatic value.

## Class methodology and interpretation

The cost of capital is a project's required return/opportunity cost. The Colombia example in Sergio Rebelo's CasePacket2026-part9 is a **Colombian project valued in USD and COP**, using Colombia's 35% project tax in both financing scenarios (slides 578–585).

Slides 564–571 derive the currency conversion from the Fisher equation, equal real rates and relative PPP, relating it to expected depreciation. Slides 580 and 587 add no separate country equity premium. Slide 575 shows actual yield differences also include real-yield and sovereign-credit components; government yields are imperfect risk-free proxies. The app mechanically follows the class approximation and does not isolate those components.

Therefore these are useful currency-consistent hurdle rates. The WACC gap alone does not measure the extra risk of locating a project in another country. Location comparisons require location-specific revenues, costs, taxes, and operating risk; infrastructure, institutions and political risk are discussed in slides 548–563. Project location adds country-specific taxes to the controlled comparison; it does not estimate different cash flows, operating risks or country equity premia. A lower nominal WACC in a different currency does not establish a better investment.

Rates in the engine are decimals:

```
D/E = d/(1-d)
# tax = shared project tax (Class method), or country i tax (Project location)
beta_E = beta_U * [1 + (1-tax)*D/E]
Re_USD = Rf_USD + beta_E*ERP
Rd_USD = Rf_USD + spread_USD
F_i = (1+Rf_i)/(1+Rf_USD)
Re_i = (1+Re_USD)*F_i - 1
spread_i_auto = spread_USD*F_i
Rd_i = Rf_i + spread_i_effective
WACC_i = (1-d)*Re_i + d*Rd_i*(1-tax)
```

Each selected currency is converted independently from the USD benchmark (with a separate tax-adjusted equity beta in Project location), so choosing or swapping two non-U.S. countries does not change the underlying risk benchmark. The class Colombia example still gives USD 8.5265% and COP 16.0670%. WACC is computed by currency from its components, including the currency-specific tax shield. The model assumes zero debt beta, fully usable interest deductions and shared target leverage and ERP.

Countries sharing a currency may have different government yields. The app flags that such a gap is not an FX conversion and can reflect sovereign or other yield premia.

## Total Market

The UI label **Total Market** maps exactly to Damodaran's **Total Market (without financials)** row and its **Unlevered beta** column, not the cash-adjusted column. The publisher's aggregate is used directly; no simple average of industry betas and no beta=1 shortcut is used. Excluding financials aligns with the assignment's large-nonfinancial BBB borrowing spread.

Both the selectable Total Market project and the companion benchmark follow the active comparison mode and each side’s effective tax, leverage, ERP, yield and spread. The companion benchmark and comparison table always retain the source aggregate beta, even if the selected project's beta is manually overridden. It represents a broad U.S. business-risk benchmark under the selected financing assumptions, not a local stock-market expected return. The current snapshot contains 94 industries plus this aggregate (95 rows).

## Data and exports

- Damodaran U.S. beta workbook: `Industry Averages`, exact unlevered-beta column and workbook update date.
- Damodaran rating spread: Baa2/BBB for large nonfinancial firms.
- OECD DF_CIT 2.0: combined statutory rate, standard targeting, general government, latest nonmissing year per country.
- Trading Economics: public government-bond-10y country-list table. Month-only observation references remain month-only.

Initial load attempts all four sources with a one-hour cache. Refresh retries them concurrently; a failed source retains its last successful values/date and displays a warning. `python sources.py` replaces the committed snapshot only when all source checks pass.

Project CSV and JSON include country identities, currency labels, the USD reference, effective inputs, override flags, source provenance and benchmark values. Industry CSV repeats shared assumptions and provenance alongside each source beta and currency result. Project rates are decimals; industry columns marked (%) are percentages. All calculations/exports retain full precision. Input widgets may use browser-locale decimal formatting; result rates display two decimal places and betas four.

## Verification

Run `python -m unittest test_app`. The test file enables offline snapshots. Twenty-five tests cover the class benchmark, independent Decimal calculation, equal yields, zero debt, two-country swap symmetry, non-U.S. conversion ratios, override isolation, invalid inputs, negative yields, refresh failures, source rejection, Total Market provenance, defaults, missing data, benchmark independence from manual beta overrides, country-specific tax arithmetic, tax isolation, mode restoration, and missing-tax overrides.

App files are in this repository; submission documents and browser verification evidence stay in the assignment's separate Submission and Verification folders.

Project exports identify the comparison mode, each effective tax, its jurisdiction, source date and override flag, plus each relevered beta. Legacy shared USD fields appear only in Class method; location-specific USD references are explicitly named and are intermediate assumptions, not a full common-currency location valuation.
