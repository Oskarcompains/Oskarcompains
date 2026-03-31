import time
from dataclasses import dataclass, field
from typing import Optional

from py_clob_client.clob_types import OrderType

from .arbitrage import ArbitrageOpportunity, ArbType
from .client import PolymarketClient
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradeRecord:
    """Record of an executed arbitrage trade."""
    opportunity_id: str         # condition_id + timestamp
    condition_id: str
    question: str
    arb_type: str

    yes_token_id: str
    no_token_id: str
    yes_order_id: Optional[str]
    no_order_id: Optional[str]

    yes_price: float
    no_price: float
    size: float                 # USD size per leg

    expected_profit: float      # net_profit * size
    actual_profit: Optional[float] = None

    status: str = "open"        # open | closed | partial | error
    timestamp: float = field(default_factory=time.time)
    closed_at: Optional[float] = None

    @property
    def opportunity_id_str(self) -> str:
        return f"{self.condition_id}_{int(self.timestamp)}"


class OrderManager:
    """
    Places and tracks orders for arbitrage opportunities.

    In dry_run mode, orders are simulated and logged only.
    """

    def __init__(self, client: PolymarketClient, dry_run: bool = True):
        self._client = client
        self._dry_run = dry_run
        self._open_trades: dict[str, TradeRecord] = {}   # opportunity_id -> record
        self._closed_trades: list[TradeRecord] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_intramarket_arb(self, opp: ArbitrageOpportunity) -> Optional[TradeRecord]:
        """
        For intra-market arbitrage: place BUY orders on both YES and NO tokens.
        Both legs are placed as FOK market orders to minimize execution risk.
        """
        size = opp.order_size

        if self._dry_run:
            return self._simulate_trade(opp, size)

        yes_order_id = None
        no_order_id = None

        try:
            # Leg 1: buy YES
            yes_resp = self._client.place_limit_order(
                token_id=opp.yes_token_id,
                price=opp.yes_ask,
                size=round(size / opp.yes_ask, 4),   # shares = USD / price
                side="BUY",
                order_type=OrderType.FOK,
            )
            yes_order_id = yes_resp.get("orderID")
        except Exception as e:
            logger.error(f"YES leg failed for {opp.condition_id[:8]}: {e}")
            return None

        try:
            # Leg 2: buy NO
            no_resp = self._client.place_limit_order(
                token_id=opp.no_token_id,
                price=opp.no_ask,
                size=round(size / opp.no_ask, 4),
                side="BUY",
                order_type=OrderType.FOK,
            )
            no_order_id = no_resp.get("orderID")
        except Exception as e:
            logger.error(f"NO leg failed for {opp.condition_id[:8]}: {e}")
            # Attempt to cancel the YES leg if it was placed
            if yes_order_id:
                try:
                    self._client.cancel_order(yes_order_id)
                    logger.warning(f"Cancelled YES leg {yes_order_id} after NO leg failure")
                except Exception as cancel_err:
                    logger.error(f"Could not cancel YES leg: {cancel_err}")
            return None

        record = TradeRecord(
            opportunity_id=f"{opp.condition_id}_{int(time.time())}",
            condition_id=opp.condition_id,
            question=opp.question,
            arb_type=opp.arb_type.value,
            yes_token_id=opp.yes_token_id,
            no_token_id=opp.no_token_id,
            yes_order_id=yes_order_id,
            no_order_id=no_order_id,
            yes_price=opp.yes_ask,
            no_price=opp.no_ask,
            size=size,
            expected_profit=opp.net_profit * size,
        )
        self._open_trades[record.opportunity_id] = record
        logger.info(
            f"Trade opened | {opp.condition_id[:8]} | "
            f"expected profit=${record.expected_profit:.4f}"
        )
        return record

    def cancel_all(self) -> None:
        """Cancel all open orders on the exchange."""
        try:
            self._client.cancel_all_orders()
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")

    def get_open_trades(self) -> list[TradeRecord]:
        return list(self._open_trades.values())

    def get_closed_trades(self) -> list[TradeRecord]:
        return list(self._closed_trades)

    def mark_trade_closed(self, opportunity_id: str, actual_profit: float) -> None:
        trade = self._open_trades.pop(opportunity_id, None)
        if trade:
            trade.status = "closed"
            trade.actual_profit = actual_profit
            trade.closed_at = time.time()
            self._closed_trades.append(trade)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _simulate_trade(self, opp: ArbitrageOpportunity, size: float) -> TradeRecord:
        record = TradeRecord(
            opportunity_id=f"{opp.condition_id}_{int(time.time())}",
            condition_id=opp.condition_id,
            question=opp.question,
            arb_type=opp.arb_type.value,
            yes_token_id=opp.yes_token_id,
            no_token_id=opp.no_token_id,
            yes_order_id="DRY_RUN_YES",
            no_order_id="DRY_RUN_NO",
            yes_price=opp.yes_ask,
            no_price=opp.no_ask,
            size=size,
            expected_profit=opp.net_profit * size,
            status="open",
        )
        self._open_trades[record.opportunity_id] = record
        logger.info(
            f"[DRY RUN] Trade simulated | {opp.question[:50]} | "
            f"YES={opp.yes_ask:.4f} NO={opp.no_ask:.4f} | "
            f"size=${size:.2f} | expected profit=${record.expected_profit:.4f}"
        )
        return record
