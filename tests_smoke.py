from stock_etf.investor import build_profile, add_position_context
from stock_etf.review import local_challenge
from stock_etf.scoring import add_scores

rows=[
    {'symbol':'TEST1','instrument_type':'STOCK','return_1w_pct':2,'return_1m_pct':5,'return_3m_pct':10,'return_6m_pct':15,'return_1y_pct':20,'cagr_3y_pct':12,'distance_sma20_pct':3,'distance_sma50_pct':5,'distance_sma200_pct':8,'volume_ratio_20d':1.2,'rsi14':55,'earnings_growth_pct':15,'roe_pct':18,'pe':20,'revenue_growth_pct':12,'profit_margin_pct':15,'debt_to_equity':40,'free_cashflow':100000000,'data_confidence':100},
    {'symbol':'TESTETF','instrument_type':'ETF','return_1w_pct':1,'return_1m_pct':3,'return_3m_pct':7,'return_6m_pct':10,'return_1y_pct':15,'cagr_3y_pct':10,'distance_sma20_pct':2,'distance_sma50_pct':4,'distance_sma200_pct':6,'volume_ratio_20d':1.1,'rsi14':54,'volatility_pct':18,'max_drawdown_pct':-15,'data_confidence':100},
]
for horizon in ('SHORT_TERM','MID_TERM','LONG_TERM'):
    add_scores(rows,horizon)
    assert any(r.get('ranking_score') is not None for r in rows), horizon
profile=build_profile(38,1000000,'LONG_TERM')
add_position_context(rows,profile)
assert all('capital_context_inr' in r for r in rows)
assert local_challenge(rows,'LONG_TERM')
print('smoke ok')
