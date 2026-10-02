import logging, os
from pathlib import Path
from datetime import datetime
from stock_etf.config import Settings
from stock_etf.engine import run
from stock_etf.profile_store import load_profile

if __name__ == '__main__':
    settings = Settings()
    log_dir = Path(settings.cache_dir).parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logfile = log_dir / f'stock_etf_{stamp}.log'
    latest = log_dir / 'stock_etf_engine_latest.log'
    handlers = [logging.StreamHandler(), logging.FileHandler(logfile, encoding='utf-8'), logging.FileHandler(latest, mode='w', encoding='utf-8')]
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=handlers, force=True)
    horizon = os.getenv('STOCK_HORIZON', 'LONG_TERM').upper()
    profile = load_profile(settings.profile_path, int(os.getenv('INVESTOR_AGE', '38')), float(os.getenv('INVESTMENT_CAPITAL_INR', '1000000')))
    logging.getLogger('stock_etf').info('Backend profile loaded: age=%s capital=₹%.2f updated=%s', profile['age'], profile['capital_inr'], profile.get('updated_at_utc'))
    run(horizon, settings, age=profile['age'], capital_inr=profile['capital_inr'])
