import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from .logger import get_logger

logger = get_logger(__name__)

STATE_FILE = "logs/portfolio_state.json"


@dataclass
class Position:
    condition_id: str
    question: str
    yes_token_id: str
    no_token_id: str
    yes_cost: float         # USD paid for YES tokens
    no_cost: float          # USD paid for NO tokens
    yes_shares: float       # number of YES shares held
    no_shares: float        # number of NO shares held
    opened_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    realized_pnl: Optional[float] = None
    status: str = "open"    # open | closed

    @property
    def total_cost(self) -> float:
        return self.yes_cost + self.no_cost

    @property
    def payout_at_resolution(self) -> float:
        """Guaranteed payout: max(yes_shares, no_shares) since one side pays $1."""
        return max(self.yes_shares, self.no_shares)

    @property
    def unrealized_pnl(self) -> float:
        """For intra-market arb, payout is guaranteed regardless of outcome."""
        return self.payout_at_resolution - self.total_cost


class Portfolio:
    """
    Tracks open and closed positions and computes P&L.
    Persists state to disk so it survives restarts.
    """

    def __init__(self, state_file: str = STATE_FILE):
        self._state_file = state_file
        self._open_positions: dict[str, Position] = {}    # condition_id -> position
        self._closed_positions: list[Position] = []
        self._load_state()

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def open_position(
        self,
        condition_id: str,
        question: str,
        yes_token_id: str,
        no_token_id: str,
        yes_cost: float,
        no_cost: float,
        yes_shares: float,
        no_shares: float,
    ) -> Position:
        pos = Position(
            condition_id=condition_id,
            question=question,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            yes_cost=yes_cost,
            no_cost=no_cost,
            yes_shares=yes_shares,
            no_shares=no_shares,
        )
        # Accumulate if position already open (partial fills)
        if condition_id in self._open_positions:
            existing = self._open_positions[condition_id]
            existing.yes_cost += yes_cost
            existing.no_cost += no_cost
            existing.yes_shares += yes_shares
            existing.no_shares += no_shares
            self._save_state()
            return existing

        self._open_positions[condition_id] = pos
        self._save_state()
        logger.info(
            f"Position opened | {question[:50]} | cost=${pos.total_cost:.4f} "
            f"| expected PnL=${pos.unrealized_pnl:.4f}"
        )
        return pos

    def close_position(self, condition_id: str, payout: float) -> Optional[Position]:
        pos = self._open_positions.pop(condition_id, None)
        if pos is None:
            logger.warning(f"No open position for {condition_id}")
            return None

        pos.status = "closed"
        pos.closed_at = time.time()
        pos.realized_pnl = payout - pos.total_cost
        self._closed_positions.append(pos)
        self._save_state()
        logger.info(
            f"Position closed | {pos.question[:50]} | "
            f"payout=${payout:.4f} cost=${pos.total_cost:.4f} "
            f"PnL=${pos.realized_pnl:.4f}"
        )
        return pos

    # ------------------------------------------------------------------
    # Exposure tracking (used by RiskManager)
    # ------------------------------------------------------------------

    def get_market_exposure(self, condition_id: str) -> float:
        """USD currently deployed in a specific market."""
        pos = self._open_positions.get(condition_id)
        return pos.total_cost if pos else 0.0

    def get_total_exposure(self) -> float:
        """Total USD deployed across all open positions."""
        return sum(p.total_cost for p in self._open_positions.values())

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> dict:
        realized = sum(
            p.realized_pnl for p in self._closed_positions if p.realized_pnl is not None
        )
        unrealized = sum(p.unrealized_pnl for p in self._open_positions.values())
        total_exposure = self.get_total_exposure()

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "open_positions": len(self._open_positions),
            "closed_positions": len(self._closed_positions),
            "total_exposure_usd": round(total_exposure, 4),
            "realized_pnl_usd": round(realized, 4),
            "unrealized_pnl_usd": round(unrealized, 4),
            "total_pnl_usd": round(realized + unrealized, 4),
        }
        return report

    def print_report(self) -> None:
        report = self.generate_report()
        logger.info("=" * 60)
        logger.info("PORTFOLIO REPORT")
        logger.info("=" * 60)
        for key, value in report.items():
            logger.info(f"  {key}: {value}")
        if self._open_positions:
            logger.info("  Open positions:")
            for cid, pos in self._open_positions.items():
                logger.info(
                    f"    [{cid[:8]}] {pos.question[:40]} | "
                    f"cost=${pos.total_cost:.4f} | unrealized PnL=${pos.unrealized_pnl:.4f}"
                )
        logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        state = {
            "open_positions": {k: asdict(v) for k, v in self._open_positions.items()},
            "closed_positions": [asdict(p) for p in self._closed_positions],
        }
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file) as f:
                state = json.load(f)
            for k, v in state.get("open_positions", {}).items():
                self._open_positions[k] = Position(**v)
            for v in state.get("closed_positions", []):
                self._closed_positions.append(Position(**v))
            logger.info(
                f"Portfolio state loaded: {len(self._open_positions)} open, "
                f"{len(self._closed_positions)} closed positions"
            )
        except Exception as e:
            logger.error(f"Failed to load portfolio state: {e}")
