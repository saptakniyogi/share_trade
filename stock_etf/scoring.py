from __future__ import annotations
import math

def n(x, lo, hi, inverse=False):
    if x is None: return None
    try: x=float(x)
    except: return None
    z=max(0,min(1,(x-lo)/(hi-lo)))
    return round((1-z if inverse else z)*100,1)

def avg_known(parts):
    vals=[v for v in parts if v is not None]
    return round(sum(vals)/len(vals),1) if vals else None

def score_short(r):
    t=[n(r.get('return_1w_pct'),-8,8), n(r.get('return_1m_pct'),-15,15), n(r.get('distance_sma20_pct'),-8,8), n(r.get('distance_sma50_pct'),-15,15), n(r.get('volume_ratio_20d'),0.5,2.5), n(r.get('rsi14'),35,70)]
    return avg_known(t)

def score_mid(r):
    t=[n(r.get('return_3m_pct'),-20,30),n(r.get('return_6m_pct'),-30,50),n(r.get('distance_sma50_pct'),-20,30),n(r.get('distance_sma200_pct'),-30,50),n(r.get('earnings_growth_pct'),-30,40),n(r.get('roe_pct'),0,30),n(r.get('pe'),8,45,True)]
    return avg_known(t)

def score_long(r):
    t=[n(r.get('revenue_growth_pct'),-10,30),n(r.get('earnings_growth_pct'),-15,35),n(r.get('roe_pct'),0,35),n(r.get('profit_margin_pct'),0,35),n(r.get('debt_to_equity'),0,200,True),n(r.get('free_cashflow'),0,1_000_000_000,False),n(r.get('pe'),8,50,True),n(r.get('cagr_3y_pct'),-10,30)]
    return avg_known(t)

def score_etf(r, horizon):
    # ETF scoring is price/track/liquidity oriented because company fundamentals do not apply.
    if horizon=='SHORT_TERM':
        return avg_known([n(r.get('return_1w_pct'),-8,8),n(r.get('return_1m_pct'),-15,15),n(r.get('distance_sma20_pct'),-8,8),n(r.get('volume_ratio_20d'),0.4,2.5),n(r.get('rsi14'),35,70)])
    if horizon=='MID_TERM':
        return avg_known([n(r.get('return_3m_pct'),-20,30),n(r.get('return_6m_pct'),-30,50),n(r.get('distance_sma50_pct'),-20,30),n(r.get('distance_sma200_pct'),-30,50),n(r.get('volatility_pct'),8,45,True)])
    return avg_known([n(r.get('return_1y_pct'),-25,40),n(r.get('cagr_3y_pct'),-10,30),n(r.get('max_drawdown_pct'),-60,-5),n(r.get('volatility_pct'),8,45,True)])

def add_scores(records, horizon):
    for r in records:
        if r.get('error'): r['horizon_score']=None; continue
        if r.get('instrument_type')=='ETF': score=score_etf(r,horizon)
        elif horizon=='SHORT_TERM': score=score_short(r)
        elif horizon=='MID_TERM': score=score_mid(r)
        else: score=score_long(r)
        r['horizon_score']=score
        conf=float(r.get('data_confidence') or 0)
        r['ranking_score']=round(score*(0.65+0.35*conf/100),1) if score is not None else None
        if score is None: r['signal']='INSUFFICIENT_DATA'
        elif horizon=='SHORT_TERM': r['signal']='SETUP' if score>=75 else ('WATCH' if score>=60 else 'AVOID')
        elif horizon=='MID_TERM': r['signal']='ACCUMULATE' if score>=75 else ('WATCH' if score>=60 else 'AVOID')
        else: r['signal']='QUALITY_CANDIDATE' if score>=75 else ('WATCH' if score>=60 else 'AVOID')
    return records
