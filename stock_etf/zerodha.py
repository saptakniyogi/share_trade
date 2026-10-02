from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from kiteconnect import KiteConnect


load_dotenv()

logger = logging.getLogger("stock_etf")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required Zerodha configuration: {name}"
        )

    return value


def get_redirect_url() -> str:
    """
    Return the configured Zerodha OAuth redirect URL.

    Required environment variable:
        ZERODHA_REDIRECT_URL
    """

    return _required(
        "ZERODHA_REDIRECT_URL"
    )


def create_client(
    access_token: str | None = None,
) -> KiteConnect:
    """
    Create a Kite Connect client.

    Required environment variables:
        ZERODHA_API_KEY
        ZERODHA_API_SECRET
        ZERODHA_REDIRECT_URL
    """

    kite = KiteConnect(
        api_key=_required(
            "ZERODHA_API_KEY"
        )
    )

    if access_token:
        kite.set_access_token(
            access_token
        )

    return kite


def get_login_url() -> str:
    """
    Generate the Zerodha Kite Connect login URL.
    """

    kite = create_client()

    return kite.login_url()


def extract_request_token(
    redirect_url: str,
) -> str:
    """
    Extract request_token from the Zerodha
    redirect URL.

    The redirect URL should normally be the URL
    received after successful Zerodha authentication.
    """

    parsed = urlparse(
        redirect_url
    )

    token = parse_qs(
        parsed.query
    ).get(
        "request_token",
        [None],
    )[0]

    if not token:
        raise ValueError(
            "No request_token found in Zerodha redirect URL."
        )

    return token


def validate_redirect_url(
    redirect_url: str,
) -> bool:
    """
    Validate that the supplied redirect URL matches
    the redirect URL configured in .env.

    This prevents accidentally processing a redirect
    from an unexpected endpoint.
    """

    configured = get_redirect_url().rstrip("/")
    supplied = redirect_url.strip().rstrip("/")

    return (
        supplied == configured
        or supplied.startswith(
            configured + "?"
        )
        or supplied.startswith(
            configured + "#"
        )
    )


def generate_session(
    request_token: str,
) -> dict:
    """
    Exchange Zerodha request_token for an access token.
    """

    kite = create_client()

    return kite.generate_session(
        request_token,
        api_secret=_required(
            "ZERODHA_API_SECRET"
        ),
    )


def fetch_holdings(
    access_token: str,
) -> list[dict]:
    """
    Fetch current equity holdings from Zerodha.
    """

    kite = create_client(
        access_token
    )

    return kite.holdings() or []


def normalise_holdings(
    items: list[dict],
) -> list[dict]:
    """
    Convert Zerodha holdings into the internal
    portfolio format.
    """

    holdings = []

    for item in items:
        symbol = str(
            item.get(
                "tradingsymbol"
            )
            or ""
        ).strip().upper()

        if not symbol:
            continue

        quantity = float(
            item.get(
                "quantity"
            )
            or 0
        )

        average_price = float(
            item.get(
                "average_price"
            )
            or 0
        )

        last_price = float(
            item.get(
                "last_price"
            )
            or 0
        )

        invested_value = (
            average_price
            * quantity
        )

        current_value = (
            last_price
            * quantity
        )

        pnl = item.get(
            "pnl"
        )

        if pnl is None:
            pnl = (
                current_value
                - invested_value
            )

        pnl = float(
            pnl
        )

        pnl_pct = (
            pnl
            / invested_value
            * 100
            if invested_value
            else 0
        )

        holdings.append(
            {
                "symbol": symbol,

                "exchange": str(
                    item.get(
                        "exchange"
                    )
                    or "NSE"
                ).upper(),

                "quantity": quantity,

                "average_price": average_price,

                "last_price": last_price,

                "invested_value": round(
                    invested_value,
                    2,
                ),

                "current_value": round(
                    current_value,
                    2,
                ),

                "pnl": round(
                    pnl,
                    2,
                ),

                "pnl_pct": round(
                    pnl_pct,
                    4,
                ),

                "product": item.get(
                    "product"
                ),

                "isin": item.get(
                    "isin"
                ),

                "instrument_token": item.get(
                    "instrument_token"
                ),

                "authorised_quantity": item.get(
                    "authorised_quantity"
                ),

                "collateral_quantity": item.get(
                    "collateral_quantity"
                ),

                "day_change": item.get(
                    "day_change"
                ),

                "day_change_percentage": item.get(
                    "day_change_percentage"
                ),
            }
        )

    return holdings


def save_holdings(
    items: list[dict],
    path: str,
) -> dict:
    """
    Persist Zerodha holdings to disk.

    An empty broker response never overwrites
    an existing holdings file.
    """

    holdings = normalise_holdings(
        items
    )

    if not holdings:
        raise RuntimeError(
            "Zerodha returned zero equity holdings. "
            "Existing holdings were not overwritten."
        )

    payload = {
        "source": "zerodha_kite_connect",

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "holdings": holdings,
    }

    target = Path(
        path
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    logger.info(
        "Saved %d Zerodha equity holdings to %s",
        len(holdings),
        path,
    )

    return payload


def refresh_holdings(
    request_token: str,
    path: str,
) -> dict:
    """
    Complete Zerodha authentication and holdings
    refresh flow.

    The access token is returned to the caller but
    is never persisted to disk.
    """

    session = generate_session(
        request_token
    )

    access_token = session[
        "access_token"
    ]

    holdings = fetch_holdings(
        access_token
    )

    payload = save_holdings(
        holdings,
        path,
    )

    return {
        "user_id": session.get(
            "user_id"
        ),

        "user_name": session.get(
            "user_name"
        ),

        "holdings_count": len(
            payload[
                "holdings"
            ]
        ),

        "login_time": session.get(
            "login_time"
        ),

        "access_token": access_token,
    }