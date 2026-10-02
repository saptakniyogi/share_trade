from __future__ import annotations
import json, logging
from pathlib import Path
from datetime import datetime, timezone
from .config import Settings
from .universe import load_universe
from .market import build_market_data, liquidity_screen
from .scoring import add_scores
from .ranking import rank, diversify
from .news import fetch_news, search_links
from .retrieval import retrieve_news
from .llm import review
from .review import local_challenge
from .investor import build_profile, add_position_context
from .profile_store import load_profile
logger=logging.getLogger('stock_etf')

def run(horizon='LONG_TERM',settings=None,age=38,capital_inr=1000000):
    settings=settings or Settings(); stored_profile=load_profile(settings.profile_path,age,capital_inr); age=stored_profile['age']; capital_inr=stored_profile['capital_inr']
    universe=load_universe(settings.universe_path,settings.nse_universe_cache,refresh=True); discovered=len(universe)
    if settings.analysis_universe_limit>0 and len(universe)>settings.analysis_universe_limit:universe=liquidity_screen(universe,settings.analysis_universe_limit,settings.max_workers)
    logger.info('Universe: %d instruments (%d stocks, %d ETFs).',len(universe),sum(x.get('type')=='STOCK' for x in universe),sum(x.get('type')=='ETF' for x in universe))
    profile=build_profile(age,capital_inr,horizon); records=build_market_data(universe,settings.history_period,settings.max_workers,settings.cache_dir); add_scores(records,horizon); ranked=rank(records,settings.ranking_limit); shortlist=diversify(ranked,min(25,settings.vector_limit*2)); add_position_context(ranked,profile); add_position_context(shortlist,profile)
    symbols=[x['symbol'] for x in shortlist]; news,news_errors=fetch_news(shortlist,max(50,settings.vector_limit*3)); news_query=' '.join([str(x.get('symbol',''))+' '+str(x.get('name',''))+' '+str(x.get('sector',''))+' '+str(x.get('industry','')) for x in shortlist]); relevant=retrieve_news(news,news_query,settings.vector_limit,settings.vector_store_dir) if news else []
    candidates=shortlist[:settings.vector_limit]; deterministic_reviews=local_challenge(candidates,horizon); llm_reviews,tokens,llm_status=review(candidates,horizon,relevant) if settings.enable_llm else ([],0,'disabled')
    review_map={str(x.get('symbol','')).upper():x for x in deterministic_reviews}
    for x in llm_reviews:review_map.setdefault(str(x.get('symbol','')).upper(),{})['llm']=x
    for x in records:
        if x.get('symbol') in review_map:x['review']=review_map[x['symbol']]
    result={'metadata':{'engine_version':'stock-etf-v8','run_at_utc':datetime.now(timezone.utc).isoformat(),'horizon':horizon,'discovered_universe_count':discovered,'universe_count':len(universe),'universe_source':'NSE current security lists unless stock_universe.json is explicitly populated','price_source':'Yahoo Finance latest available quote/history; not licensed exchange tick data','analysis_universe_limit':settings.analysis_universe_limit,'selection_method':'liquidity-screened dynamic NSE universe','profile_backend_path':settings.profile_path},'investor_profile':profile,'market':{'relevant_news':relevant,'news_found':len(news),'news_errors':news_errors[-20:],'news_search_links':search_links(shortlist)},'evaluated_instruments':records,'local_ranking':{'ranked':ranked,'shortlist':shortlist,'llm_candidates':candidates},'reviews':{'deterministic':deterministic_reviews,'llm':llm_reviews,'llm_status':llm_status,'prompt_tokens':tokens}}
    Path(settings.output_path).parent.mkdir(parents=True,exist_ok=True); Path(settings.output_path).write_text(json.dumps(result,indent=2,default=str),encoding='utf-8'); logger.info('Analysis written to %s',settings.output_path); logger.info('News: %d fetched, %d relevant. Deterministic reviews: %d. LLM reviews: %d (%s).',len(news),len(relevant),len(deterministic_reviews),len(llm_reviews),llm_status); return result
