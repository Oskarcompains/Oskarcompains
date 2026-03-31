"""
FastAPI backend for the Polymarket Arbitrage Bot dashboard.
Serves REST endpoints + WebSocket for real-time data.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Polymarket Arb Bot", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# State store — reads from portfolio_state.json + in-memory event log
# ---------------------------------------------------------------------------

PORTFOLIO_FILE = Path("logs/portfolio_state.json")
MAX_EVENTS = 100


class BotState:
    def __init__(self):
        self.running: bool = False
        self.started_at: Optional[float] = None
        self.markets_tracked: int = 0
        self.last_scan_at: Optional[float] = None
        self.scans_total: int = 0
        self.opportunities_found: int = 0
        self.opportunities: list[dict] = []  # rolling last 50
        self.errors: int = 0


bot_state = BotState()


def load_portfolio() -> dict:
    if not PORTFOLIO_FILE.exists():
        return {"open_positions": {}, "closed_positions": []}
    try:
        return json.loads(PORTFOLIO_FILE.read_text())
    except Exception:
        return {"open_positions": {}, "closed_positions": []}


def compute_pnl(portfolio: dict) -> dict:
    closed = portfolio.get("closed_positions", [])
    open_pos = portfolio.get("open_positions", {})

    realized = sum(p.get("realized_pnl", 0) or 0 for p in closed)
    unrealized = sum(
        max(p.get("yes_shares", 0), p.get("no_shares", 0)) - p.get("yes_cost", 0) - p.get("no_cost", 0)
        for p in open_pos.values()
    )
    total_cost = sum(
        p.get("yes_cost", 0) + p.get("no_cost", 0) for p in open_pos.values()
    )

    # Build P&L history from closed positions (sorted by close time)
    history = []
    running = 0.0
    for p in sorted(closed, key=lambda x: x.get("closed_at") or 0):
        running += p.get("realized_pnl", 0) or 0
        history.append({
            "time": p.get("closed_at"),
            "pnl": round(running, 4),
            "question": p.get("question", "")[:40],
        })

    return {
        "realized": round(realized, 4),
        "unrealized": round(unrealized, 4),
        "total": round(realized + unrealized, 4),
        "total_exposure": round(total_cost, 4),
        "total_trades": len(closed),
        "history": history[-50:],  # last 50 data points
    }


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    portfolio = load_portfolio()
    open_count = len(portfolio.get("open_positions", {}))
    return {
        "running": bot_state.running,
        "started_at": bot_state.started_at,
        "uptime_sec": round(time.time() - bot_state.started_at, 0) if bot_state.started_at else 0,
        "markets_tracked": bot_state.markets_tracked,
        "last_scan_at": bot_state.last_scan_at,
        "scans_total": bot_state.scans_total,
        "opportunities_found": bot_state.opportunities_found,
        "open_positions": open_count,
        "errors": bot_state.errors,
    }


@app.get("/api/pnl")
def get_pnl():
    portfolio = load_portfolio()
    return compute_pnl(portfolio)


@app.get("/api/positions")
def get_positions():
    portfolio = load_portfolio()
    positions = []
    for cid, p in portfolio.get("open_positions", {}).items():
        yes_shares = p.get("yes_shares", 0)
        no_shares = p.get("no_shares", 0)
        cost = p.get("yes_cost", 0) + p.get("no_cost", 0)
        payout = max(yes_shares, no_shares)
        positions.append({
            "condition_id": cid[:8] + "...",
            "question": p.get("question", "")[:60],
            "yes_price": round(p.get("yes_cost", 0) / yes_shares, 4) if yes_shares else 0,
            "no_price": round(p.get("no_cost", 0) / no_shares, 4) if no_shares else 0,
            "cost": round(cost, 4),
            "expected_payout": round(payout, 4),
            "unrealized_pnl": round(payout - cost, 4),
            "opened_at": p.get("opened_at"),
            "status": p.get("status", "open"),
        })
    return {"positions": positions}


@app.get("/api/opportunities")
def get_opportunities():
    return {"opportunities": bot_state.opportunities[-50:]}


@app.get("/api/trades")
def get_trades():
    portfolio = load_portfolio()
    trades = []
    for p in sorted(
        portfolio.get("closed_positions", []),
        key=lambda x: x.get("closed_at") or 0,
        reverse=True,
    )[:50]:
        trades.append({
            "question": p.get("question", "")[:60],
            "yes_price": round(p.get("yes_cost", 0) / p.get("yes_shares", 1), 4) if p.get("yes_shares") else 0,
            "no_price": round(p.get("no_cost", 0) / p.get("no_shares", 1), 4) if p.get("no_shares") else 0,
            "cost": round((p.get("yes_cost", 0) + p.get("no_cost", 0)), 4),
            "realized_pnl": round(p.get("realized_pnl", 0) or 0, 4),
            "opened_at": p.get("opened_at"),
            "closed_at": p.get("closed_at"),
            "status": p.get("status", "closed"),
        })
    return {"trades": trades}


# ---------------------------------------------------------------------------
# Bot control endpoints
# ---------------------------------------------------------------------------

@app.post("/api/bot/start")
def start_bot():
    bot_state.running = True
    bot_state.started_at = time.time()
    return {"ok": True, "message": "Bot started"}


@app.post("/api/bot/stop")
def stop_bot():
    bot_state.running = False
    return {"ok": True, "message": "Bot stopped"}


# ---------------------------------------------------------------------------
# Ingest endpoint — the Python bot posts events here
# ---------------------------------------------------------------------------

class OpportunityEvent(BaseModel):
    condition_id: str
    question: str
    yes_ask: float
    no_ask: float
    net_profit: float
    order_size: float
    executed: bool = False


@app.post("/api/ingest/opportunity")
def ingest_opportunity(event: OpportunityEvent):
    opp = event.dict()
    opp["timestamp"] = time.time()
    bot_state.opportunities.append(opp)
    bot_state.opportunities = bot_state.opportunities[-MAX_EVENTS:]
    bot_state.opportunities_found += 1
    bot_state.last_scan_at = time.time()
    bot_state.scans_total += 1
    # Broadcast to WS clients
    asyncio.create_task(_broadcast(json.dumps({"type": "opportunity", "data": opp})))
    return {"ok": True}


@app.post("/api/ingest/scan")
def ingest_scan(payload: dict = {}):
    bot_state.last_scan_at = time.time()
    bot_state.scans_total += 1
    bot_state.markets_tracked = payload.get("markets_tracked", bot_state.markets_tracked)
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket — real-time push to dashboard
# ---------------------------------------------------------------------------

_ws_clients: list[WebSocket] = []


async def _broadcast(message: str):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        # Send initial state on connect
        portfolio = load_portfolio()
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": {
                "status": get_status(),
                "pnl": compute_pnl(portfolio),
                "positions": get_positions()["positions"],
                "opportunities": bot_state.opportunities[-20:],
            },
        }))

        # Keep alive + periodic heartbeat
        while True:
            await asyncio.sleep(5)
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "data": get_status(),
            }))
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)


# ---------------------------------------------------------------------------
# Serve React build (production)
# ---------------------------------------------------------------------------

DIST = Path("dashboard/dist")

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(str(DIST / "index.html"))
