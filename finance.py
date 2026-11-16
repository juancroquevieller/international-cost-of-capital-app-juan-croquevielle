from __future__ import annotations
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class Inputs:
    beta_u: float
    tax: float
    debt_share: float
    erp: float
    us_yield: float
    foreign_yield: float
    usd_spread: float
    foreign_spread: float | None = None

def calculate(p: Inputs) -> dict:
    values = asdict(p)
    if any(not math.isfinite(v) for v in values.values() if v is not None):
        raise ValueError('All inputs must be finite numbers.')
    if not 0 <= p.debt_share < 1:
        raise ValueError('Debt share must be at least 0% and below 100%.')
    if not 0 <= p.tax <= 1 or p.beta_u < 0 or p.erp < 0 or p.usd_spread < 0:
        raise ValueError('Tax must be 0–100%; beta, ERP and spread cannot be negative.')
    if min(p.us_yield, p.foreign_yield) <= -1:
        raise ValueError('Government yields must exceed -100%.')
    if p.foreign_spread is not None and p.foreign_spread < 0:
        raise ValueError('The foreign spread cannot be negative.')
    de = p.debt_share / (1-p.debt_share)
    beta = p.beta_u * (1+(1-p.tax)*de)
    factor = (1+p.foreign_yield)/(1+p.us_yield)
    equity = p.us_yield + beta*p.erp
    debt = p.us_yield+p.usd_spread
    auto_spread = p.usd_spread*factor
    spread = auto_spread if p.foreign_spread is None else p.foreign_spread
    foreign_equity = (1+equity)*factor-1
    foreign_debt = p.foreign_yield+spread
    return dict(beta_e=beta, debt_equity=de, conversion_factor=factor,
        auto_foreign_spread=auto_spread, effective_foreign_spread=spread,
        usd_equity=equity, foreign_equity=foreign_equity,
        usd_debt=debt, foreign_debt=foreign_debt,
        usd_aftertax_debt=debt*(1-p.tax), foreign_aftertax_debt=foreign_debt*(1-p.tax),
        usd_wacc=(1-p.debt_share)*equity+p.debt_share*debt*(1-p.tax),
        foreign_wacc=(1-p.debt_share)*foreign_equity+p.debt_share*foreign_debt*(1-p.tax))
