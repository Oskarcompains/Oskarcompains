"""
Polymarket Arbitrage Trading Bot
=================================
Entry point. Supports three modes:

  python main.py                  → run the full bot loop
  python main.py --test-connection → verify API auth and connectivity
  python main.py --scan-once      → single scan, print opportunities, then exit
  python main.py --report         → print current portfolio report and exit
"""

import argparse
import asyncio
import os
import signal
import sys
import time

import yaml
from dotenv import load_dotenv

from src.arbitrage import ArbitrageDetector
from src.client import PolymarketClient
from src.logger import get_logger, setup_logger
from src.market_monitor import MarketMonitor
from src.order_manager import OrderManager
from src.portfolio import Portfolio
from src.risk_manager import RiskManager

load_dotenv()


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_components(cfg: dict):
    bot_cfg = cfg.get("bot", {})
    arb_cfg = cfg.get("arbitrage", {})
    risk_cfg = cfg.get("risk", {})
    log_cfg = cfg.get("logging", {})

    # Logger
    setup_logger(
        name="root",
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("log_file", "logs/bot.log"),
        max_file_size_mb=log_cfg.get("max_file_size_mb", 10),
        backup_count=log_cfg.get("backup_count", 5),
    )

    # Client
    client = PolymarketClient()
    client.authenticate()

    # Core components
    monitor = MarketMonitor(
        client=client,
        poll_interval=bot_cfg.get("poll_interval", 5),
        markets_to_monitor=bot_cfg.get("markets_to_monitor") or [],
    )
    detector = ArbitrageDetector(
        monitor=monitor,
        min_profit_threshold=arb_cfg.get("min_profit_threshold", 0.02),
        max_order_size=arb_cfg.get("max_order_size", 100.0),
        fee_rate=arb_cfg.get("fee_rate", 0.005),
        min_liquidity=arb_cfg.get("min_liquidity", 10.0),
    )
    portfolio = Portfolio()
    risk = RiskManager(
        max_position_size=risk_cfg.get("max_position_size", 200.0),
        max_total_exposure=risk_cfg.get("max_total_exposure", 1000.0),
        stop_loss_pct=risk_cfg.get("stop_loss_pct", 0.15),
        trade_cooldown=risk_cfg.get("trade_cooldown", 60.0),
        max_consecutive_errors=risk_cfg.get("max_consecutive_errors", 5),
    )
    order_mgr = OrderManager(client=client, dry_run=bot_cfg.get("dry_run", True))

    return client, monitor, detector, portfolio, risk, order_mgr


# ------------------------------------------------------------------
# Bot main loop
# ------------------------------------------------------------------

class ArbBot:
    def __init__(self, cfg: dict):
        (
            self._client,
            self._monitor,
            self._detector,
            self._portfolio,
            self._risk,
            self._order_mgr,
        ) = build_components(cfg)

        self._max_open_positions = cfg.get("bot", {}).get("max_open_positions", 5)
        self._logger = get_logger("ArbBot")
        self._running = False

    async def run(self) -> None:
        self._running = True
        self._logger.info("Bot starting...")

        # Start market monitor in background
        monitor_task = asyncio.create_task(self._monitor.start())

        # Wait for initial data
        await asyncio.sleep(10)

        report_interval = 300  # Print portfolio report every 5 minutes
        last_report = time.time()

        try:
            while self._running:
                # Check stop-loss on open positions
                self._check_stop_losses()

                # Scan for arbitrage
                opportunities = self._detector.scan()

                open_count = len(self._order_mgr.get_open_trades())

                for opp in opportunities:
                    if open_count >= self._max_open_positions:
                        self._logger.info("Max open positions reached, skipping")
                        break

                    allowed, reason = self._risk.can_trade(opp, self._portfolio)
                    if not allowed:
                        self._logger.debug(f"Trade blocked: {reason}")
                        continue

                    try:
                        trade = self._order_mgr.execute_intramarket_arb(opp)
                        if trade:
                            self._portfolio.open_position(
                                condition_id=opp.condition_id,
                                question=opp.question,
                                yes_token_id=opp.yes_token_id,
                                no_token_id=opp.no_token_id,
                                yes_cost=opp.yes_ask * round(opp.order_size / opp.yes_ask, 4),
                                no_cost=opp.no_ask * round(opp.order_size / opp.no_ask, 4),
                                yes_shares=round(opp.order_size / opp.yes_ask, 4),
                                no_shares=round(opp.order_size / opp.no_ask, 4),
                            )
                            self._risk.record_trade(opp.condition_id)
                            open_count += 1
                    except Exception as e:
                        self._logger.error(f"Trade execution error: {e}")
                        self._risk.record_error()

                # Periodic report
                if time.time() - last_report >= report_interval:
                    self._portfolio.print_report()
                    self._logger.info(f"Risk status: {self._risk.get_status()}")
                    last_report = time.time()

                await asyncio.sleep(self._monitor._poll_interval)

        except asyncio.CancelledError:
            pass
        finally:
            self._logger.info("Bot shutting down...")
            self._monitor.stop()
            monitor_task.cancel()
            self._portfolio.print_report()

    def stop(self) -> None:
        self._running = False

    def _check_stop_losses(self) -> None:
        for cid, pos in list(self._portfolio._open_positions.items()):
            if self._risk.should_stop_loss(pos.total_cost, pos.payout_at_resolution):
                self._logger.warning(
                    f"Stop-loss triggered for {cid[:8]} | "
                    f"cost=${pos.total_cost:.4f} payout=${pos.payout_at_resolution:.4f}"
                )
                # For intra-market arb positions the payout is already guaranteed
                # so stop-loss mainly applies to partial fills / edge cases
                self._portfolio.close_position(cid, payout=pos.payout_at_resolution)


# ------------------------------------------------------------------
# CLI commands
# ------------------------------------------------------------------

def cmd_test_connection(cfg: dict) -> None:
    logger = get_logger("test")
    setup_logger("root", level="INFO")
    logger.info("Testing connection to Polymarket...")
    client = PolymarketClient()
    client.authenticate()
    markets = client.get_all_markets()
    logger.info(f"Connection OK — {len(markets)} markets available")
    balance = client.get_balance()
    logger.info(f"Balance: {balance}")


def cmd_scan_once(cfg: dict) -> None:
    logger = get_logger("scan")
    setup_logger("root", level="INFO")
    logger.info("Running single arbitrage scan...")
    client = PolymarketClient()
    client.authenticate()
    monitor = MarketMonitor(client=client)

    arb_cfg = cfg.get("arbitrage", {})
    detector = ArbitrageDetector(
        monitor=monitor,
        min_profit_threshold=arb_cfg.get("min_profit_threshold", 0.02),
        max_order_size=arb_cfg.get("max_order_size", 100.0),
        fee_rate=arb_cfg.get("fee_rate", 0.005),
        min_liquidity=arb_cfg.get("min_liquidity", 10.0),
    )

    async def _run():
        await monitor._refresh_market_list()
        await monitor._poll_orderbooks()
        opps = detector.scan()
        if not opps:
            logger.info("No arbitrage opportunities found")
        return opps

    asyncio.run(_run())


def cmd_report() -> None:
    setup_logger("root", level="INFO")
    portfolio = Portfolio()
    portfolio.print_report()


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Arbitrage Bot")
    parser.add_argument("--config", default="config/config.yaml", help="Config file path")
    parser.add_argument("--test-connection", action="store_true", help="Test API connectivity")
    parser.add_argument("--scan-once", action="store_true", help="Single scan, then exit")
    parser.add_argument("--report", action="store_true", help="Print portfolio report and exit")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.test_connection:
        cmd_test_connection(cfg)
        return

    if args.scan_once:
        cmd_scan_once(cfg)
        return

    if args.report:
        cmd_report()
        return

    # Full bot run
    bot = ArbBot(cfg)

    loop = asyncio.new_event_loop()

    def _shutdown(signum, frame):
        print("\nShutdown signal received...")
        bot.stop()
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(bot.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
