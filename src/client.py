import os
from typing import Any, Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds,
    OpenOrderParams,
    OrderArgs,
    OrderType,
    MarketOrderArgs,
)
from py_clob_client.order_builder.constants import BUY, SELL

from .logger import get_logger

logger = get_logger(__name__)

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137


class PolymarketClient:
    """Authenticated wrapper around ClobClient."""

    def __init__(
        self,
        private_key: Optional[str] = None,
        funder: Optional[str] = None,
        chain_id: int = CHAIN_ID,
        signature_type: int = 1,
    ):
        private_key = private_key or os.environ["POLYMARKET_PRIVATE_KEY"]
        funder = funder or os.environ.get("POLYMARKET_FUNDER")
        chain_id = int(os.environ.get("POLYMARKET_CHAIN_ID", chain_id))

        self._client = ClobClient(
            host=HOST,
            key=private_key,
            chain_id=chain_id,
            signature_type=signature_type,
            funder=funder,
        )
        self._authenticated = False

    def authenticate(self) -> None:
        """Derive or create API credentials and set them on the client."""
        try:
            creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(creds)
            self._authenticated = True
            logger.info("Polymarket authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_markets(self, next_cursor: str = "") -> dict:
        """Return a page of simplified markets."""
        return self._client.get_simplified_markets(next_cursor=next_cursor)

    def get_all_markets(self) -> list[dict]:
        """Fetch all active markets by paginating through results."""
        markets: list[dict] = []
        cursor = ""
        while True:
            response = self.get_markets(next_cursor=cursor)
            data = response.get("data", [])
            markets.extend(data)
            cursor = response.get("next_cursor", "")
            if not cursor or cursor == "LTE=":
                break
        logger.debug(f"Fetched {len(markets)} markets total")
        return markets

    def get_orderbook(self, token_id: str) -> Any:
        """Return the order book for a single token."""
        return self._client.get_order_book(token_id=token_id)

    def get_orderbooks(self, token_ids: list[str]) -> list[Any]:
        """Return order books for multiple tokens in one call."""
        return self._client.get_order_books(params=[{"token_id": t} for t in token_ids])

    def get_midpoint(self, token_id: str) -> float:
        result = self._client.get_midpoint(token_id=token_id)
        return float(result.get("mid", 0))

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        result = self._client.get_price(token_id=token_id, side=side)
        return float(result.get("price", 0))

    def get_last_trade_price(self, token_id: str) -> float:
        result = self._client.get_last_trade_price(token_id=token_id)
        return float(result.get("price", 0))

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def place_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: OrderType = OrderType.GTC,
    ) -> dict:
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=BUY if side.upper() == "BUY" else SELL,
        )
        signed = self._client.create_order(order_args)
        response = self._client.post_order(signed, order_type)
        logger.info(
            f"Limit order placed | {side} {size} @ {price} | token={token_id[:8]}... | id={response.get('orderID', 'N/A')}"
        )
        return response

    def place_market_order(
        self,
        token_id: str,
        amount: float,
        side: str,
    ) -> dict:
        market_order = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=BUY if side.upper() == "BUY" else SELL,
        )
        signed = self._client.create_market_order(market_order)
        response = self._client.post_order(signed, OrderType.FOK)
        logger.info(
            f"Market order placed | {side} ${amount} | token={token_id[:8]}... | id={response.get('orderID', 'N/A')}"
        )
        return response

    def cancel_order(self, order_id: str) -> dict:
        response = self._client.cancel(order_id=order_id)
        logger.info(f"Order cancelled | id={order_id}")
        return response

    def cancel_all_orders(self) -> dict:
        response = self._client.cancel_all()
        logger.info("All open orders cancelled")
        return response

    def get_open_orders(self) -> list[dict]:
        return self._client.get_orders(OpenOrderParams()) or []

    def get_trades(self, token_id: Optional[str] = None) -> list[dict]:
        if token_id:
            return self._client.get_trades(token_id=token_id) or []
        return self._client.get_trades() or []

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_balance(self) -> dict:
        return self._client.get_balance()

    def get_portfolio(self) -> list[dict]:
        return self._client.get_portfolio() or []
