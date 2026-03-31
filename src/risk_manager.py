import time
from typing import TYPE_CHECKING

from .arbitrage import ArbitrageOpportunity
from .logger import get_logger

if TYPE_CHECKING:
    from .portfolio import Portfolio

logger = get_logger(__name__)


class RiskManager:
    """
    Validates arbitrage opportunities against risk parameters before execution.

    Checks:
    - Max position size per market
    - Max total portfolio exposure
    - Trade cooldown (avoid hammering the same market)
    - Max consecutive errors (circuit breaker)
    """

    def __init__(
        self,
        max_position_size: float = 200.0,
        max_total_exposure: float = 1000.0,
        stop_loss_pct: float = 0.15,
        trade_cooldown: float = 60.0,
        max_consecutive_errors: int = 5,
    ):
        self._max_position_size = max_position_size
        self._max_total_exposure = max_total_exposure
        self._stop_loss_pct = stop_loss_pct
        self._trade_cooldown = trade_cooldown
        self._max_consecutive_errors = max_consecutive_errors

        # condition_id -> last trade timestamp
        self._last_trade_time: dict[str, float] = {}
        # consecutive error counter
        self._consecutive_errors: int = 0

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def can_trade(
        self,
        opportunity: ArbitrageOpportunity,
        portfolio: "Portfolio",
    ) -> tuple[bool, str]:
        """
        Returns (allowed, reason).
        If allowed is False, reason explains why the trade was blocked.
        """
        # Circuit breaker
        if self._consecutive_errors >= self._max_consecutive_errors:
            return False, f"Circuit breaker: {self._consecutive_errors} consecutive errors"

        # Cooldown check
        last = self._last_trade_time.get(opportunity.condition_id, 0)
        elapsed = time.time() - last
        if elapsed < self._trade_cooldown:
            remaining = self._trade_cooldown - elapsed
            return False, f"Cooldown active ({remaining:.0f}s remaining)"

        # Per-market position limit
        current_exposure = portfolio.get_market_exposure(opportunity.condition_id)
        if current_exposure + opportunity.order_size > self._max_position_size:
            return False, (
                f"Position limit: current=${current_exposure:.2f} "
                f"+ order=${opportunity.order_size:.2f} > max=${self._max_position_size:.2f}"
            )

        # Total portfolio exposure
        total_exposure = portfolio.get_total_exposure()
        if total_exposure + opportunity.order_size * 2 > self._max_total_exposure:
            return False, (
                f"Total exposure limit: current=${total_exposure:.2f} "
                f"+ order=${opportunity.order_size * 2:.2f} > max=${self._max_total_exposure:.2f}"
            )

        return True, "OK"

    def record_trade(self, condition_id: str) -> None:
        """Call after a trade is successfully executed."""
        self._last_trade_time[condition_id] = time.time()
        self._consecutive_errors = 0

    def record_error(self) -> None:
        """Call when a trade attempt fails."""
        self._consecutive_errors += 1
        if self._consecutive_errors >= self._max_consecutive_errors:
            logger.warning(
                f"Circuit breaker triggered after {self._consecutive_errors} consecutive errors"
            )

    def reset_errors(self) -> None:
        self._consecutive_errors = 0
        logger.info("Error counter reset")

    def should_stop_loss(self, cost_basis: float, current_value: float) -> bool:
        """Return True if unrealized loss exceeds stop_loss_pct."""
        if cost_basis <= 0:
            return False
        loss_pct = (cost_basis - current_value) / cost_basis
        return loss_pct >= self._stop_loss_pct

    def get_status(self) -> dict:
        return {
            "consecutive_errors": self._consecutive_errors,
            "circuit_breaker_active": self._consecutive_errors >= self._max_consecutive_errors,
            "max_position_size": self._max_position_size,
            "max_total_exposure": self._max_total_exposure,
            "stop_loss_pct": self._stop_loss_pct,
            "trade_cooldown": self._trade_cooldown,
        }
