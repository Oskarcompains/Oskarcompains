import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from .client import PolymarketClient
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrderBookSnapshot:
    token_id: str
    bids: list[dict]   # [{"price": float, "size": float}, ...]
    asks: list[dict]
    timestamp: float = field(default_factory=time.time)

    @property
    def best_bid(self) -> Optional[float]:
        if not self.bids:
            return None
        return max(float(b["price"]) for b in self.bids)

    @property
    def best_ask(self) -> Optional[float]:
        if not self.asks:
            return None
        return min(float(a["price"]) for a in self.asks)

    @property
    def bid_liquidity(self) -> float:
        """Total USD available on the bid side."""
        return sum(float(b["price"]) * float(b["size"]) for b in self.bids)

    @property
    def ask_liquidity(self) -> float:
        """Total USD available on the ask side."""
        return sum(float(a["price"]) * float(a["size"]) for a in self.asks)


@dataclass
class MarketSnapshot:
    """Snapshot of a binary market (YES + NO tokens)."""
    condition_id: str
    question: str
    yes_token_id: str
    no_token_id: str
    yes_book: Optional[OrderBookSnapshot] = None
    no_book: Optional[OrderBookSnapshot] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def yes_best_ask(self) -> Optional[float]:
        return self.yes_book.best_ask if self.yes_book else None

    @property
    def no_best_ask(self) -> Optional[float]:
        return self.no_book.best_ask if self.no_book else None

    @property
    def total_ask_cost(self) -> Optional[float]:
        """YES ask + NO ask. If < 1.0, intra-market arbitrage exists."""
        if self.yes_best_ask is not None and self.no_best_ask is not None:
            return self.yes_best_ask + self.no_best_ask
        return None


class MarketMonitor:
    """Polls Polymarket for price/orderbook data and maintains a live cache."""

    def __init__(
        self,
        client: PolymarketClient,
        poll_interval: float = 5.0,
        markets_to_monitor: Optional[list[str]] = None,
    ):
        self._client = client
        self._poll_interval = poll_interval
        self._markets_to_monitor = markets_to_monitor or []
        self._snapshots: dict[str, MarketSnapshot] = {}  # condition_id -> snapshot
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        logger.info("MarketMonitor started")
        # Initial load of market list
        await self._refresh_market_list()
        while self._running:
            try:
                await self._poll_orderbooks()
            except Exception as e:
                logger.error(f"Error polling orderbooks: {e}")
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
        logger.info("MarketMonitor stopped")

    def get_all_snapshots(self) -> list[MarketSnapshot]:
        return list(self._snapshots.values())

    def get_snapshot(self, condition_id: str) -> Optional[MarketSnapshot]:
        return self._snapshots.get(condition_id)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    async def _refresh_market_list(self) -> None:
        """Fetch market list and build initial snapshot stubs."""
        try:
            markets = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_all_markets
            )
        except Exception as e:
            logger.error(f"Failed to fetch market list: {e}")
            return

        count = 0
        for market in markets:
            condition_id = market.get("condition_id", "")
            if not condition_id:
                continue
            # Filter if specific markets were configured
            if self._markets_to_monitor and condition_id not in self._markets_to_monitor:
                continue

            tokens = market.get("tokens", [])
            yes_token = next((t for t in tokens if t.get("outcome") == "Yes"), None)
            no_token = next((t for t in tokens if t.get("outcome") == "No"), None)

            if not yes_token or not no_token:
                continue

            if condition_id not in self._snapshots:
                self._snapshots[condition_id] = MarketSnapshot(
                    condition_id=condition_id,
                    question=market.get("question", ""),
                    yes_token_id=yes_token["token_id"],
                    no_token_id=no_token["token_id"],
                )
                count += 1

        logger.info(f"Tracking {len(self._snapshots)} markets ({count} new)")

    async def _poll_orderbooks(self) -> None:
        """Fetch fresh orderbooks for all tracked markets."""
        if not self._snapshots:
            await self._refresh_market_list()
            return

        # Collect all token IDs (YES + NO for each market)
        token_to_market: dict[str, tuple[str, str]] = {}  # token_id -> (condition_id, side)
        token_ids: list[str] = []

        for cid, snap in self._snapshots.items():
            token_to_market[snap.yes_token_id] = (cid, "yes")
            token_to_market[snap.no_token_id] = (cid, "no")
            token_ids.extend([snap.yes_token_id, snap.no_token_id])

        # Fetch in batches to respect rate limits
        batch_size = 20
        for i in range(0, len(token_ids), batch_size):
            batch = token_ids[i : i + batch_size]
            try:
                books = await asyncio.get_event_loop().run_in_executor(
                    None, lambda b=batch: self._client.get_orderbooks(b)
                )
                self._apply_orderbooks(books, token_to_market)
            except Exception as e:
                logger.warning(f"Failed to fetch orderbook batch: {e}")
            # Small sleep between batches to avoid rate limits
            if i + batch_size < len(token_ids):
                await asyncio.sleep(0.5)

    def _apply_orderbooks(
        self,
        books: list,
        token_to_market: dict[str, tuple[str, str]],
    ) -> None:
        for book in books:
            if book is None:
                continue
            token_id = getattr(book, "asset_id", None) or getattr(book, "token_id", None)
            if token_id not in token_to_market:
                continue

            condition_id, side = token_to_market[token_id]
            snap = self._snapshots.get(condition_id)
            if snap is None:
                continue

            bids = [{"price": str(b.price), "size": str(b.size)} for b in (book.bids or [])]
            asks = [{"price": str(a.price), "size": str(a.size)} for a in (book.asks or [])]

            ob_snap = OrderBookSnapshot(token_id=token_id, bids=bids, asks=asks)

            if side == "yes":
                snap.yes_book = ob_snap
            else:
                snap.no_book = ob_snap

        snap.timestamp = time.time()
