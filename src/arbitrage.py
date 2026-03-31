from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

from .market_monitor import MarketMonitor, MarketSnapshot
from .logger import get_logger

logger = get_logger(__name__)


class ArbType(str, Enum):
    INTRAMARKET = "intramarket"   # YES + NO < 1 on same market
    INTERMARKET = "intermarket"   # related markets mispriced relative to each other


@dataclass
class ArbitrageOpportunity:
    arb_type: ArbType
    condition_id: str
    question: str

    # For intramarket: buy YES + buy NO
    yes_token_id: str
    no_token_id: str
    yes_ask: float
    no_ask: float

    # Order sizes (USD value to trade per leg)
    order_size: float

    # Net profit after fees (as a fraction of capital)
    gross_profit: float     # 1 - (yes_ask + no_ask)
    fee_cost: float         # fees on both legs
    net_profit: float       # gross_profit - fee_cost

    # Available liquidity on each side
    yes_liquidity: float
    no_liquidity: float

    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return (
            f"[{self.arb_type.value.upper()}] {self.question[:60]} | "
            f"YES={self.yes_ask:.4f} NO={self.no_ask:.4f} "
            f"sum={self.yes_ask + self.no_ask:.4f} "
            f"net_profit={self.net_profit:.2%} "
            f"size=${self.order_size:.2f}"
        )


class ArbitrageDetector:
    """
    Scans market snapshots and identifies arbitrage opportunities.

    Intra-market arbitrage:
        If YES_ask + NO_ask < 1.0, buying both tokens guarantees a $1 payout
        at a cost of (YES_ask + NO_ask), yielding a risk-free profit.

    Inter-market arbitrage (future extension):
        Detect price inconsistencies across correlated markets.
    """

    def __init__(
        self,
        monitor: MarketMonitor,
        min_profit_threshold: float = 0.02,
        max_order_size: float = 100.0,
        fee_rate: float = 0.005,
        min_liquidity: float = 10.0,
    ):
        self._monitor = monitor
        self._min_profit = min_profit_threshold
        self._max_order_size = max_order_size
        self._fee_rate = fee_rate
        self._min_liquidity = min_liquidity

    def scan(self) -> list[ArbitrageOpportunity]:
        """Scan all tracked markets and return valid opportunities."""
        opportunities: list[ArbitrageOpportunity] = []
        snapshots = self._monitor.get_all_snapshots()

        for snap in snapshots:
            opp = self._detect_intramarket(snap)
            if opp is not None:
                opportunities.append(opp)

        if opportunities:
            logger.info(f"Found {len(opportunities)} arbitrage opportunity/ies")
            for opp in opportunities:
                logger.info(str(opp))

        return opportunities

    # ------------------------------------------------------------------
    # Intra-market arbitrage
    # ------------------------------------------------------------------

    def _detect_intramarket(self, snap: MarketSnapshot) -> Optional[ArbitrageOpportunity]:
        """
        YES_ask + NO_ask < 1.0 → buying both guarantees a $1 payout.
        Net profit = 1 - YES_ask - NO_ask - fees.
        """
        if snap.yes_book is None or snap.no_book is None:
            return None

        yes_ask = snap.yes_book.best_ask
        no_ask = snap.no_book.best_ask

        if yes_ask is None or no_ask is None:
            return None

        # Liquidity check: enough size available on each side?
        yes_liq = snap.yes_book.ask_liquidity
        no_liq = snap.no_book.ask_liquidity

        if yes_liq < self._min_liquidity or no_liq < self._min_liquidity:
            return None

        total_cost = yes_ask + no_ask
        if total_cost >= 1.0:
            return None  # No opportunity

        gross_profit = 1.0 - total_cost
        # Fee on buying YES + buying NO (taker fee on each leg)
        fee_cost = (yes_ask + no_ask) * self._fee_rate * 2
        net_profit = gross_profit - fee_cost

        if net_profit < self._min_profit:
            return None

        # Size the trade by the limiting side liquidity
        max_size_by_liquidity = min(yes_liq, no_liq)
        order_size = min(self._max_order_size, max_size_by_liquidity)

        return ArbitrageOpportunity(
            arb_type=ArbType.INTRAMARKET,
            condition_id=snap.condition_id,
            question=snap.question,
            yes_token_id=snap.yes_token_id,
            no_token_id=snap.no_token_id,
            yes_ask=yes_ask,
            no_ask=no_ask,
            order_size=order_size,
            gross_profit=gross_profit,
            fee_cost=fee_cost,
            net_profit=net_profit,
            yes_liquidity=yes_liq,
            no_liquidity=no_liq,
        )
