from __future__ import annotations
import numpy as np

def simple_momentum_stats(close, holding_days=10, threshold=0.04):
    if close is None or len(close)<holding_days+30: return {'occurrences':0}
    c=close.dropna(); ret=c.pct_change(5); signal=(ret>threshold)
    fwd=c.shift(-holding_days)/c-1
    x=fwd[signal].dropna()
    if x.empty: return {'occurrences':0}
    return {'occurrences':int(len(x)),'win_rate_pct':round(float((x>0).mean()*100),1),'avg_forward_return_pct':round(float(x.mean()*100),2),'worst_forward_return_pct':round(float(x.min()*100),2),'best_forward_return_pct':round(float(x.max()*100),2)}
