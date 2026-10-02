from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


def save_profile(path: str | Path, age: int, capital_inr: float) -> dict:
    age = int(age)
    capital_inr = float(capital_inr)
    if not 18 <= age <= 100:
        raise ValueError('Age must be between 18 and 100.')
    if capital_inr <= 0:
        raise ValueError('Capital must be greater than zero.')
    profile = {
        'age': age,
        'capital_inr': round(capital_inr, 2),
        'updated_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(profile, indent=2), encoding='utf-8')
    tmp.replace(p)
    return profile


def load_profile(path: str | Path, default_age: int = 38, default_capital: float = 1000000) -> dict:
    p = Path(path)
    if not p.exists():
        return save_profile(p, default_age, default_capital)
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return save_profile(p, int(data['age']), float(data['capital_inr'])) | {
            'updated_at_utc': data.get('updated_at_utc')
        }
    except Exception:
        return save_profile(p, default_age, default_capital)
