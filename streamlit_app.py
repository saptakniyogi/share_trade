from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
import pandas as pd
import streamlit as st
from stock_etf.profile_store import load_profile, save_profile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / os.getenv('STOCK_ETF_OUTPUT_PATH', 'stock_etf_analysis.json')
LOGDIR = ROOT / 'logs'; LOGDIR.mkdir(exist_ok=True)
HORIZONS = {'SHORT_TERM':'1–2 Weeks','MID_TERM':'1–12 Months','LONG_TERM':'3–10+ Years'}
PROFILE_PATH = ROOT / os.getenv('INVESTOR_PROFILE_PATH', 'backend_state/investor_profile.json')


def sync_profile():
    profile = save_profile(PROFILE_PATH, st.session_state.age, st.session_state.capital)
    st.session_state.profile_sync_message = f"Backend profile synced · {profile['updated_at_utc']}"



def clean_html_text(value):
    """Convert provider HTML fragments to safe plain text for Streamlit rendering."""
    import html as _html
    import re as _re
    if value is None:
        return ""
    text = str(value)
    text = _re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=_re.I|_re.S)
    text = _re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=_re.I|_re.S)
    text = _re.sub(r"<br\s*/?>", "\n", text, flags=_re.I)
    text = _re.sub(r"</p>|</div>|</li>|</h[1-6]>", "\n", text, flags=_re.I)
    text = _re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    text = _re.sub(r"[ \t]+", " ", text)
    text = _re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()


def load():
    if not OUT.exists(): return None
    try: return json.loads(OUT.read_text())
    except Exception: return None


def run_engine(horizon, age, capital, enable_llm):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    env['STOCK_HORIZON'] = horizon
    env['INVESTOR_AGE'] = str(age)
    env['INVESTMENT_CAPITAL_INR'] = str(capital)
    env['ENABLE_LLM_REVIEW'] = 'true' if enable_llm else 'false'
    env['INVESTOR_PROFILE_PATH'] = str(PROFILE_PATH)
    env['PYTHONUNBUFFERED'] = '1'
    log = []
    with st.status(f'Running {HORIZONS[horizon]} research…', expanded=True) as status:
        p = subprocess.Popen([sys.executable, '-u', str(ROOT/'run_stock_etf_analysis.py')], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout or []:
            line = line.rstrip()
            if line:
                log.append(line); st.code('\n'.join(log[-100:]))
        rc = p.wait()
        stamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        (LOGDIR/f'ui_run_{stamp}.log').write_text('\n'.join(log)+'\n', encoding='utf-8')
        (LOGDIR/'stock_etf_latest.log').write_text('\n'.join(log)+'\n', encoding='utf-8')
        if rc:
            status.update(label='Analysis failed', state='error'); st.error('Engine failed. See logs/.'); return None
        status.update(label='Analysis complete', state='complete')
    return load()


def fmt(x, suffix=''):
    return '—' if x is None else f'{x:.1f}{suffix}' if isinstance(x,(int,float)) else str(x)


def main():
    st.set_page_config(page_title='Stock & ETF Research Dashboard', page_icon='📈', layout='wide')
    st.title('📈 Stock & ETF Research Dashboard')
    st.caption('Dynamic NSE universe → liquidity screen → market data → deterministic ranking → multi-source news → challenge review.')

    backend_profile = load_profile(PROFILE_PATH, 38, 1000000.0)
    if 'horizon' not in st.session_state: st.session_state.horizon='SHORT_TERM'
    if 'age' not in st.session_state: st.session_state.age=backend_profile['age']
    if 'capital' not in st.session_state: st.session_state.capital=backend_profile['capital_inr']
    if 'llm' not in st.session_state: st.session_state.llm=False
    if 'profile_sync_message' not in st.session_state: st.session_state.profile_sync_message = f"Backend profile loaded · {backend_profile.get('updated_at_utc','unknown')}"

    with st.sidebar:
        st.header('Investor profile')
        st.number_input('Age', min_value=18, max_value=100, step=1, key='age', on_change=sync_profile)
        st.number_input('Investment capital (₹)', min_value=1000.0, step=10000.0, format='%.0f', key='capital', on_change=sync_profile)
        st.caption('Changes are persisted to the backend immediately. Capital is used for allocation context and does not change the underlying market score.')
        st.success(st.session_state.profile_sync_message)
        st.divider()
        st.header('Research horizon')
        st.radio('Horizon', list(HORIZONS), format_func=lambda x:HORIZONS[x], key='horizon')
        st.toggle('Enable LLM challenge', value=st.session_state.llm, key='llm')
        if st.button('▶ Run analysis', type='primary', use_container_width=True):
            st.session_state.result = run_engine(st.session_state.horizon, st.session_state.age, st.session_state.capital, st.session_state.llm)
            st.rerun()
        if st.button('↻ Load latest', use_container_width=True):
            st.session_state.result = load(); st.rerun()
        st.divider()
        st.caption('Universe is refreshed from NSE current equity + ETF security lists. A populated stock_universe.json overrides this only when you explicitly provide one.')

    result = st.session_state.get('result') or load()
    if not result:
        st.info('Enter age and capital, choose a horizon, then click Run analysis.')
        st.stop()

    rows = result.get('evaluated_instruments', [])
    ranked = result.get('local_ranking', {}).get('ranked', [])
    shortlist = result.get('local_ranking', {}).get('llm_candidates', [])
    news = result.get('market', {}).get('relevant_news', [])
    profile = result.get('investor_profile', {})
    reviews = result.get('reviews', {})

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric('Universe', len(rows)); c2.metric('Ranked', len(ranked)); c3.metric('Candidates', len(shortlist)); c4.metric('News', len(news)); c5.metric('Reviews', len(reviews.get('deterministic', [])) + len(reviews.get('llm', [])))
    st.info(f"Profile: age {profile.get('age')} · capital ₹{profile.get('capital_inr',0):,.0f} · horizon capital context ₹{profile.get('horizon_capital_inr',0):,.0f}")

    tab1,tab2,tab3,tab4=st.tabs(['🏆 Opportunities','📊 Stock / ETF detail','📰 News & review','⚙ Diagnostics'])
    with tab1:
        st.subheader(f'Top candidates · {HORIZONS[result["metadata"]["horizon"]]}')
        filt=st.multiselect('Instrument type',['STOCK','ETF'],default=['STOCK','ETF'])
        data=[x for x in ranked if x.get('instrument_type') in filt]
        table=pd.DataFrame([{'Rank':x.get('local_rank'),'Symbol':x.get('symbol'),'Type':x.get('instrument_type'),'Score':x.get('ranking_score'),'Confidence':x.get('data_confidence'),'Signal':x.get('signal'),'Suggested weight %':x.get('suggested_weight_pct'),'Capital context ₹':x.get('capital_context_inr'),'1W %':x.get('return_1w_pct'),'1M %':x.get('return_1m_pct'),'3M %':x.get('return_3m_pct'),'1Y %':x.get('return_1y_pct'),'RSI':x.get('rsi14')} for x in data[:30]])
        st.dataframe(table,use_container_width=True,hide_index=True)
        st.caption('Suggested weight is a mathematical allocation context based on ranking scores, not a guaranteed or personalized investment recommendation.')

    with tab2:
        symbols=[x.get('symbol') for x in rows if x.get('price') is not None]
        if not symbols:
            st.warning('No instruments have usable market data. Check Diagnostics and logs/.')
        else:
            sym=st.selectbox('Instrument',symbols,index=0)
            r=next((x for x in rows if x.get('symbol')==sym),None)
            if r:
                st.subheader(f'{r.get("name",sym)} · {sym}')
                a,b,c,d,e=st.columns(5); a.metric('Latest price',fmt(r.get('price'))); b.metric('Score',fmt(r.get('ranking_score'))); c.metric('1W',fmt(r.get('return_1w_pct'),'%')); d.metric('1M',fmt(r.get('return_1m_pct'),'%')); e.metric('1Y',fmt(r.get('return_1y_pct'),'%'))
                st.write('**Signal:**',r.get('signal'),' · **Data confidence:**',fmt(r.get('data_confidence'),'%'))
                left,right=st.columns(2)
                with left:
                    st.markdown('### Technical'); st.json({k:r.get(k) for k in ['sma20','sma50','sma200','distance_sma20_pct','distance_sma50_pct','distance_sma200_pct','rsi14','atr_pct','volume_ratio_20d','volatility_pct','max_drawdown_pct']})
                with right:
                    st.markdown('### Fundamentals / ETF data'); st.json({k:r.get(k) for k in ['sector','industry','market_cap_inr','pe','forward_pe','pb','ev_ebitda','roe_pct','revenue_growth_pct','earnings_growth_pct','debt_to_equity','free_cashflow','expense_ratio','tracking_error','category']})
                if r.get('review'): st.markdown('### Challenge review'); st.json(r['review'])

    with tab3:
        if not news:
            errs=result.get('market', {}).get('news_errors', [])
            st.warning('No live articles were returned by the configured providers for this run.')
            if errs:
                st.error('News provider diagnostics:')
                st.code('\n'.join(errs[-10:]))
            links=result.get('market', {}).get('news_search_links', [])
            if links:
                st.markdown('### Live search fallback')
                st.caption('These links open current news searches directly when a news provider blocks the server.')
                for item in links:
                    if item.get("url", "").startswith(("http://", "https://")):
                        st.link_button(f'{item["symbol"]} news', item["url"], use_container_width=False)
        for n in news:
            title = clean_html_text(n.get("title", "")) or "Untitled article"
            source = clean_html_text(n.get("source", "")) or "Unknown source"
            published = clean_html_text(n.get("published", ""))
            summary = clean_html_text(n.get("summary", ""))
            similarity = n.get("vector_similarity", "—")
            with st.container(border=True):
                st.markdown(f"### {title}")
                meta = source
                if published:
                    meta += f" · {published}"
                if similarity != "—":
                    meta += f" · similarity {similarity}"
                st.caption(meta)
                if summary:
                    st.write(summary[:700])
                link = str(n.get("link", "")).strip()
                if link.startswith(("http://", "https://")):
                    st.link_button("Open article", link)
        st.divider(); st.subheader('Review status')
        st.write(reviews.get('llm_status','unknown'))
        st.json({'deterministic_reviews': reviews.get('deterministic', []), 'llm_reviews': reviews.get('llm', [])})

    with tab4:
        st.json(result.get('metadata',{})); st.write('Investor profile:',profile); st.write('Reviews:',reviews)
        st.write('Errors:',sum(bool(x.get('error')) for x in rows))
        errors=[x for x in rows if x.get('error')]
        if errors: st.dataframe(pd.DataFrame(errors)[['symbol','yf_symbol','error']],use_container_width=True,hide_index=True)
        st.write('Log directory:', str(LOGDIR))
        st.write('Data confidence distribution:',pd.Series([x.get('data_confidence',0) for x in rows]).describe())

if __name__=='__main__': main()
