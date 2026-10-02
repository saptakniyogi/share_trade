from __future__ import annotations


def build_profile(age: int, capital_inr: float, horizon: str) -> dict:
    age = int(age)
    capital_inr = float(capital_inr)
    if not 18 <= age <= 100:
        raise ValueError('Age must be between 18 and 100.')
    if capital_inr <= 0:
        raise ValueError('Capital must be greater than zero.')

    # Age is shown as investor context. It does not override the quantitative ranking.
    # The horizon determines the amount of capital eligible for this dashboard's strategy.
    horizon_share = {'SHORT_TERM': 0.15, 'MID_TERM': 0.40, 'LONG_TERM': 0.70}.get(horizon, 0.40)
    strategy_capital = capital_inr * horizon_share
    return {
        'age': age,
        'capital_inr': round(capital_inr, 2),
        'horizon_capital_inr': round(strategy_capital, 2),
        'horizon_capital_share_pct': round(horizon_share * 100, 1),
        'note': 'Capital is used for position-sizing context. It does not guarantee returns or change the underlying market score.'
    }


def add_position_context(rows: list[dict], profile: dict) -> None:
    eligible = [r for r in rows if r.get('ranking_score') is not None]
    if not eligible:
        return
    weights = [max(0.0, float(r.get('ranking_score') or 0.0)) for r in eligible]
    total = sum(weights)
    for r in rows:
        score = max(0.0, float(r.get('ranking_score') or 0.0))
        weight = score / total if total else 0.0
        r['suggested_weight_pct'] = round(weight * 100, 2)
        r['capital_context_inr'] = round(profile['horizon_capital_inr'] * weight, 2)
