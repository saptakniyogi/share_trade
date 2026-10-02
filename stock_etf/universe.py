from __future__ import annotations
import io, json, logging
from pathlib import Path
import pandas as pd
import requests

logger = logging.getLogger('stock_etf')

NSE_EQUITY_URL = 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'
NSE_ETF_URL = 'https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
    'Accept': 'text/csv,application/octet-stream,*/*',
    'Referer': 'https://www.nseindia.com/'
}


def _get_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content))


def _symbol_column(df: pd.DataFrame) -> str:
    for c in ('SYMBOL', 'Symbol', 'symbol'):
        if c in df.columns:
            return c
    raise ValueError(f'No symbol column found. Columns: {list(df.columns)}')


def refresh_nse_universe(cache_path: str = 'cache/nse_universe.json') -> list[dict]:
    """Fetch the current NSE equity and ETF security lists. No hardcoded universe is used."""
    stocks_df = _get_csv(NSE_EQUITY_URL)
    etf_df = _get_csv(NSE_ETF_URL)
    stock_col = _symbol_column(stocks_df)
    etf_col = _symbol_column(etf_df)

    rows = []
    for _, r in stocks_df.iterrows():
        symbol = str(r.get(stock_col, '')).strip().upper()
        if symbol and symbol != 'NAN':
            rows.append({'symbol': symbol, 'type': 'STOCK', 'exchange': 'NSE', 'name': str(r.get('NAME OF COMPANY', r.get('NAME', symbol))).strip()})
    for _, r in etf_df.iterrows():
        symbol = str(r.get(etf_col, '')).strip().upper()
        if symbol and symbol != 'NAN':
            rows.append({'symbol': symbol, 'type': 'ETF', 'exchange': 'NSE', 'name': str(r.get('NAME OF COMPANY', r.get('NAME', symbol))).strip()})

    # De-duplicate symbols, preferring ETF classification from the official ETF list.
    by_symbol = {}
    for row in rows:
        by_symbol[row['symbol']] = row
    rows = sorted(by_symbol.values(), key=lambda x: (x['type'], x['symbol']))
    if not rows:
        raise RuntimeError('NSE returned an empty instrument universe.')

    p = Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({'source': 'NSE', 'equity_url': NSE_EQUITY_URL, 'etf_url': NSE_ETF_URL, 'instruments': rows}, indent=2), encoding='utf-8')
    logger.info('NSE universe refreshed: %d instruments (%d stocks, %d ETFs).', len(rows), sum(x['type']=='STOCK' for x in rows), sum(x['type']=='ETF' for x in rows))
    return rows


def load_universe(path: str, cache_path: str = 'cache/nse_universe.json', refresh: bool = True) -> list[dict]:
    """Load a user-supplied universe or refresh from NSE. The bundled starter list is intentionally removed."""
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                data = data.get('instruments', [])
            if isinstance(data, list) and data:
                rows = [x if isinstance(x, dict) else {'symbol': str(x), 'type': 'STOCK', 'exchange': 'NSE'} for x in data]
                rows = [x for x in rows if str(x.get('symbol', '')).strip()]
                if rows:
                    logger.info('Using configured universe: %d instruments.', len(rows))
                    return rows
        except Exception as exc:
            logger.warning('Configured universe could not be read: %s', exc)

    if refresh:
        try:
            return refresh_nse_universe(cache_path)
        except Exception as exc:
            logger.error('NSE universe refresh failed: %s', exc)

    cp = Path(cache_path)
    if cp.exists():
        try:
            data = json.loads(cp.read_text(encoding='utf-8'))
            rows = data.get('instruments', []) if isinstance(data, dict) else data
            if rows:
                logger.warning('Using cached NSE universe from %s.', cp)
                return rows
        except Exception as exc:
            logger.error('Cached NSE universe could not be read: %s', exc)
    raise RuntimeError('No instrument universe available. Connect to NSE or provide stock_universe.json.')


def yf_symbol(row: dict) -> str:
    symbol = str(row.get('symbol', '')).strip().upper()
    exchange = str(row.get('exchange', 'NSE')).upper()
    if exchange == 'BSE':
        return f'{symbol}.BO'
    if symbol.startswith('^') or '.' in symbol:
        return symbol
    return f'{symbol}.NS'
