"""
Production server launcher.
Runs the FastAPI app with uvicorn.

Usage:
    python server.py                   # port 8000 (default)
    python server.py --port 3000
    python server.py --host 0.0.0.0 --port 80

The React build is served from dashboard/dist/ at the root path.
Build it first with:  cd dashboard && npm run build
"""

import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Hot-reload (dev only)")
    args = parser.parse_args()

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
