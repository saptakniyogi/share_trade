from __future__ import annotations

def rank(records, limit=50):
    rows=[r for r in records if r.get('ranking_score') is not None]
    rows.sort(key=lambda r:(-float(r['ranking_score']),-float(r.get('data_confidence') or 0),str(r.get('symbol',''))))
    for i,r in enumerate(rows[:limit],1): r['local_rank']=i
    return rows[:limit]

def diversify(rows, limit=20):
    out=[]; sectors={}; types={}
    for r in rows:
        key=r.get('sector') or r.get('category') or 'Unknown'; typ=r.get('instrument_type','STOCK')
        if sectors.get(key,0)>=4: continue
        if typ=='ETF' and types.get('ETF',0)>=8: continue
        out.append(r); sectors[key]=sectors.get(key,0)+1; types[typ]=types.get(typ,0)+1
        if len(out)>=limit: break
    if len(out)<limit:
        seen={r['symbol'] for r in out}
        for r in rows:
            if r['symbol'] not in seen: out.append(r)
            if len(out)>=limit: break
    return out
