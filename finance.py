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

@dataclass(frozen=True)
class PairInputs:
    beta_u: float
    tax: float
    debt_share: float
    erp: float
    us_yield: float
    yield1: float
    yield2: float
    usd_spread: float
    spread1: float | None = None
    spread2: float | None = None
    tax1: float | None = None
    tax2: float | None = None


def compare(p: PairInputs) -> dict:
    """Use shared project tax by default; explicit side taxes model locations."""
    result = {'debt_equity': p.debt_share/(1-p.debt_share) if p.debt_share != 1 else float('inf')}
    for side, rate, spread in [(1, p.yield1, p.spread1), (2, p.yield2, p.spread2)]:
        tax = getattr(p, f"tax{side}")
        tax = p.tax if tax is None else tax
        r = calculate(Inputs(p.beta_u, tax, p.debt_share, p.erp,
                             p.us_yield, rate, p.usd_spread, spread))
        result[f'country{side}_tax'] = tax
        result[f'country{side}_beta_e'] = r['beta_e']
        result[f'country{side}_usd_reference_equity'] = r['usd_equity']
        result[f'country{side}_usd_reference_wacc'] = r['usd_wacc']
        if side == 1 and p.tax1 is None and p.tax2 is None:
            result.update({k: v for k, v in r.items() if k.startswith('usd_') or k in ['beta_e', 'debt_equity']})
        for metric in ['equity', 'debt', 'aftertax_debt', 'wacc']:
            result[f'country{side}_{metric}'] = r['foreign_'+metric]
        result[f'country{side}_factor'] = r['conversion_factor']
        result[f'country{side}_auto_spread'] = r['auto_foreign_spread']
        result[f'country{side}_spread'] = r['effective_foreign_spread']
    return result
