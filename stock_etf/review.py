from __future__ import annotations


def local_challenge(rows, horizon):
    """Always-on deterministic challenge so the review panel is useful without an LLM key."""
    out = []
    for r in rows:
        issues = []
        positives = []
        score = r.get('ranking_score')
        conf = r.get('data_confidence') or 0
        if score is None:
            issues.append('Insufficient quantitative data.')
        if conf < 70:
            issues.append(f'Data confidence is only {conf:.0f}%.')
        if horizon == 'SHORT_TERM':
            if r.get('rsi14') is not None and r['rsi14'] > 70: issues.append('RSI indicates an overbought condition.')
            if r.get('distance_sma20_pct') is not None and r['distance_sma20_pct'] > 8: issues.append('Price is extended above the 20-day average.')
            if r.get('volume_ratio_20d') is not None and r['volume_ratio_20d'] >= 1.3: positives.append('Recent participation is above its 20-day average.')
        elif horizon == 'MID_TERM':
            if r.get('pe') is not None and r['pe'] > 40: issues.append('Valuation multiple is elevated relative to the scoring range.')
            if r.get('earnings_growth_pct') is not None and r['earnings_growth_pct'] > 10: positives.append('Earnings growth supports the mid-term score.')
        else:
            if r.get('debt_to_equity') is not None and r['debt_to_equity'] > 120: issues.append('Leverage is relatively high.')
            if r.get('free_cashflow') is not None and r['free_cashflow'] > 0: positives.append('Positive free cash flow supports the long-term case.')
        if not issues: issues.append('No major deterministic contradiction was detected from the available metrics.')
        out.append({'symbol': r.get('symbol'), 'review_type': 'deterministic_challenge', 'positives': positives, 'risks': issues, 'data_gaps': [] if conf >= 70 else ['Some market/fundamental fields are missing.']})
    return out
