from __future__ import annotations

import json
import tempfile
from pathlib import Path

from stock_etf.investor import (
    add_position_context,
    build_profile,
)
from stock_etf.portfolio import (
    apply_portfolio_context,
    load_holdings,
    portfolio_summary,
)
from stock_etf.review import local_challenge
from stock_etf.scoring import add_scores


rows = [
    {
        "symbol": "TEST1",
        "instrument_type": "STOCK",
        "sector": "Technology",
        "return_1w_pct": 2,
        "return_1m_pct": 5,
        "return_3m_pct": 10,
        "return_6m_pct": 15,
        "return_1y_pct": 20,
        "cagr_3y_pct": 12,
        "distance_sma20_pct": 3,
        "distance_sma50_pct": 5,
        "distance_sma200_pct": 8,
        "volume_ratio_20d": 1.2,
        "rsi14": 55,
        "earnings_growth_pct": 15,
        "roe_pct": 18,
        "pe": 20,
        "revenue_growth_pct": 12,
        "profit_margin_pct": 15,
        "debt_to_equity": 40,
        "free_cashflow": 100000000,
        "data_confidence": 100,
    },
    {
        "symbol": "TESTETF",
        "instrument_type": "ETF",
        "sector": "Diversified",
        "return_1w_pct": 1,
        "return_1m_pct": 3,
        "return_3m_pct": 7,
        "return_6m_pct": 10,
        "return_1y_pct": 15,
        "cagr_3y_pct": 10,
        "distance_sma20_pct": 2,
        "distance_sma50_pct": 4,
        "distance_sma200_pct": 6,
        "volume_ratio_20d": 1.1,
        "rsi14": 54,
        "volatility_pct": 18,
        "max_drawdown_pct": -15,
        "data_confidence": 100,
    },
]


# ----------------------------------------------------------------------
# Existing scoring tests
# ----------------------------------------------------------------------

for horizon in (
    "SHORT_TERM",
    "MID_TERM",
    "LONG_TERM",
):
    add_scores(
        rows,
        horizon,
    )

    assert any(
        row.get(
            "ranking_score"
        )
        is not None
        for row in rows
    ), horizon


# ----------------------------------------------------------------------
# Investor profile / allocation tests
# ----------------------------------------------------------------------

profile = build_profile(
    38,
    1_000_000,
    "LONG_TERM",
)

add_position_context(
    rows,
    profile,
)

assert all(
    "capital_context_inr" in row
    for row in rows
)

assert all(
    "suggested_weight_pct" in row
    for row in rows
)


# ----------------------------------------------------------------------
# Portfolio summary tests
# ----------------------------------------------------------------------

holdings = {
    "TEST1": {
        "symbol": "TEST1",
        "exchange": "NSE",
        "quantity": 100,
        "average_price": 100,
        "last_price": 120,
        "invested_value": 10_000,
        "current_value": 12_000,
        "pnl": 2_000,
        "pnl_pct": 20,
    },
    "OTHER": {
        "symbol": "OTHER",
        "exchange": "NSE",
        "quantity": 50,
        "average_price": 200,
        "last_price": 180,
        "invested_value": 10_000,
        "current_value": 9_000,
        "pnl": -1_000,
        "pnl_pct": -10,
    },
}

summary = portfolio_summary(
    holdings
)

assert summary[
    "holdings_count"
] == 2

assert summary[
    "invested_value"
] == 20_000

assert summary[
    "current_value"
] == 21_000

assert summary[
    "pnl"
] == 1_000

assert round(
    summary["pnl_pct"],
    2,
) == 5.0


# ----------------------------------------------------------------------
# Portfolio-aware ranking tests
# ----------------------------------------------------------------------

portfolio_rows = [
    {
        "symbol": "TEST1",
        "sector": "Technology",
        "ranking_score": 90,
    },
    {
        "symbol": "TEST2",
        "sector": "Technology",
        "ranking_score": 85,
    },
    {
        "symbol": "TEST3",
        "sector": "Financials",
        "ranking_score": 80,
    },
]

portfolio_holdings = {
    "TEST1": {
        "symbol": "TEST1",
        "current_value": 30_000,
        "invested_value": 25_000,
        "pnl": 5_000,
        "pnl_pct": 20,
    },
    "TEST2": {
        "symbol": "TEST2",
        "current_value": 10_000,
        "invested_value": 10_000,
        "pnl": 0,
        "pnl_pct": 0,
    },
    "TEST3": {
        "symbol": "TEST3",
        "current_value": 5_000,
        "invested_value": 5_000,
        "pnl": 0,
        "pnl_pct": 0,
    },
}

apply_portfolio_context(
    portfolio_rows,
    portfolio_holdings,
)

# Original score must remain available.
assert (
    portfolio_rows[0][
        "market_ranking_score"
    ]
    == 90
)

# Portfolio-aware score must be present.
assert (
    portfolio_rows[0][
        "portfolio_adjusted_score"
    ]
    is not None
)

# ranking_score should now represent the
# portfolio-adjusted score.
assert (
    portfolio_rows[0][
        "ranking_score"
    ]
    == portfolio_rows[0][
        "portfolio_adjusted_score"
    ]
)

# Existing holding should be detected.
assert (
    portfolio_rows[0][
        "already_owned"
    ]
    is True
)

assert (
    portfolio_rows[0][
        "portfolio_context"
    ]
    in {
        "EXISTING_POSITION",
        "HIGH_EXISTING_POSITION",
        "EXISTING_HIGH_SECTOR_EXPOSURE",
    }
)

# Position and sector exposure fields must exist.
assert (
    "portfolio_position_pct"
    in portfolio_rows[0]
)

assert (
    "portfolio_sector_exposure_pct"
    in portfolio_rows[0]
)


# ----------------------------------------------------------------------
# No-portfolio behavior
# ----------------------------------------------------------------------

no_portfolio_rows = [
    {
        "symbol": "NEWSTOCK",
        "sector": "Technology",
        "ranking_score": 75,
    }
]

apply_portfolio_context(
    no_portfolio_rows,
    {},
)

assert (
    no_portfolio_rows[0][
        "market_ranking_score"
    ]
    == 75
)

assert (
    no_portfolio_rows[0][
        "portfolio_adjusted_score"
    ]
    == 75
)

assert (
    no_portfolio_rows[0][
        "ranking_score"
    ]
    == 75
)

assert (
    no_portfolio_rows[0][
        "already_owned"
    ]
    is False
)

assert (
    no_portfolio_rows[0][
        "portfolio_context"
    ]
    == "NO_PORTFOLIO"
)


# ----------------------------------------------------------------------
# Holdings file loading test
# ----------------------------------------------------------------------

with tempfile.TemporaryDirectory() as temp_dir:

    holdings_path = (
        Path(temp_dir)
        / "zerodha_holdings.json"
    )

    holdings_path.write_text(
        json.dumps(
            {
                "source": "zerodha_kite_connect",
                "holdings": [
                    {
                        "symbol": "INFY",
                        "exchange": "NSE",
                        "quantity": 10,
                        "average_price": 1_500,
                        "last_price": 1_600,
                        "invested_value": 15_000,
                        "current_value": 16_000,
                        "pnl": 1_000,
                        "pnl_pct": 6.6667,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_holdings(
        holdings_path
    )

    assert "INFY" in loaded

    assert loaded[
        "INFY"
    ]["quantity"] == 10


# ----------------------------------------------------------------------
# Existing deterministic review test
# ----------------------------------------------------------------------

assert local_challenge(
    rows,
    "LONG_TERM",
)


print(
    "portfolio-aware smoke tests ok"
)