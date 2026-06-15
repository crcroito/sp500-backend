from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import httpx
import asyncio
from scanner import start_background_filter, start_daily_refresh, scan_all, get_filter_status, _cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== SERVER INITIALIZAT ===")
    start_background_filter()
    start_daily_refresh()
    yield
    print("=== SERVER INCHIS ===")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"

SECTORS = [
    {"name": "Tehnologie",   "ticker": "XLK",  "emoji": "💻"},
    {"name": "Financiar",    "ticker": "XLF",  "emoji": "🏦"},
    {"name": "Sănătate",     "ticker": "XLV",  "emoji": "⚕️"},
    {"name": "Energie",      "ticker": "XLE",  "emoji": "⚡"},
    {"name": "Consum Disc.", "ticker": "XLY",  "emoji": "🛍️"},
    {"name": "Consum Baz.",  "ticker": "XLP",  "emoji": "🛒"},
    {"name": "Industrie",    "ticker": "XLI",  "emoji": "⚙️"},
    {"name": "Real Estate",  "ticker": "XLRE", "emoji": "🏢"},
    {"name": "Utilități",    "ticker": "XLU",  "emoji": "🔋"},
    {"name": "Materiale",    "ticker": "XLB",  "emoji": "🪨"},
    {"name": "Comunicații",  "ticker": "XLC",  "emoji": "📡"},
]

MARKET_TICKERS = {
    "^GSPC": "SPY",
    "^VIX": "VIXY",
    "^TNX": "TLT",
    "DX-Y.NYB": "UUP",
}


def get_etf_from_cache(ticker: str) -> dict:
    """Citește datele ETF-ului din RAM cache."""
    data = _cache.get("global_market_data", {}).get(ticker, [])
    if len(data) >= 2:
        prev = data[-2]["c"]
        curr = data[-1]["c"]
        chg = round((curr - prev) / prev * 100, 2)
        return {"price": round(curr, 2), "change": chg}
    return {"price": None, "change": None}


@app.get("/")
def root():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/status")
def status_endpoint():
    return get_filter_status()


@app.get("/scan")
def scan_endpoint(min_score: int = 2):
    return scan_all(min_score=min_score)


@app.get("/api/filter-status")
def filter_status_bridge():
    return get_filter_status()


@app.get("/api/market")
def market():
    result = {}
    for key, etf in MARKET_TICKERS.items():
        d = get_etf_from_cache(etf)
        result[key] = d
    return result


@app.get("/api/sectors")
def sectors():
    result = []
    for s in SECTORS:
        d = get_etf_from_cache(s["ticker"])
        result.append({**s, **d})
    return result


@app.get("/api/macro")
def macro():
    return {
        "fed_rate": "5.25-5.50%",
        "cpi": "3.2%",
        "core_pce": "2.8%",
        "unemployment": "3.9%",
        "source": "FRED / BLS",
        "updated": datetime.utcnow().isoformat()
    }


@app.get("/api/early-warning")
def early_warning_bridge(min_score: int = 2):
    results = scan_all(min_score=min_score)
    return {
        "signals": results,
        "count": len(results),
        "scanned": get_filter_status()["count"],
        "scanned_at": datetime.utcnow().isoformat()
    }


@app.get("/api/early-warning/scan-now")
def scan_now_bridge():
    return {"status": "ok"}
