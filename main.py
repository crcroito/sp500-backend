from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import requests
from datetime import datetime, timedelta
import os
from scanner import scan_all, get_tickers_to_scan, get_filter_status, start_background_filter, POLYGON_API_KEY, BASE_URL
from emailer import send_alert_email

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Porneste filtrul market cap in background la startup
    start_background_filter()
    yield

app = FastAPI(title="S&P 500 Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = {}

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


def get_polygon_etf(ticker: str) -> dict:
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        res = requests.get(url, params={"apiKey": POLYGON_API_KEY, "sort": "asc"}, timeout=8)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if len(results) >= 2:
                prev = results[-2]["c"]
                curr = results[-1]["c"]
                chg = round((curr - prev) / prev * 100, 2)
                return {"price": round(curr, 2), "change": chg}
    except:
        pass
    return {"price": None, "change": None}


@app.get("/")
def root():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/api/filter-status")
def filter_status():
    return get_filter_status()


@app.get("/api/sectors")
def sectors():
    result = []
    for s in SECTORS:
        q = get_polygon_etf(s["ticker"])
        result.append({**s, **q})
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
def early_warning(min_score: int = Query(default=3, ge=1, le=4)):
    cache_key = f"ew_{min_score}"
    cached = _cache.get(cache_key)
    if cached:
        age = (datetime.utcnow() - datetime.fromisoformat(cached["scanned_at"])).seconds / 60
        if age < 30:
            return cached

    tickers = get_tickers_to_scan()
    results = scan_all(min_score=min_score)

    response = {
        "signals": results,
        "count": len(results),
        "scanned": len(tickers),
        "filter_status": get_filter_status()["status"],
        "min_score": min_score,
        "scanned_at": datetime.utcnow().isoformat(),
    }
    _cache[cache_key] = response
    return response


@app.get("/api/early-warning/scan-now")
def scan_now(background_tasks: BackgroundTasks):
    def do_scan():
        tickers = get_tickers_to_scan()
        results = scan_all(min_score=3)
        base = {
            "signals": results,
            "count": len(results),
            "scanned": len(tickers),
            "filter_status": get_filter_status()["status"],
            "scanned_at": datetime.utcnow().isoformat(),
        }
        _cache["ew_3"] = base
        high = [r for r in results if r["score"] >= 4]
        _cache["ew_4"] = {**base, "signals": high, "count": len(high)}
        alert_email = os.getenv("ALERT_EMAIL")
        if alert_email and high:
            send_alert_email(high, alert_email)

    background_tasks.add_task(do_scan)
    return {"status": "scan started", "tickers": len(get_tickers_to_scan())}


@app.post("/api/early-warning/email")
def send_email(to: str = Query(...)):
    cached = _cache.get("ew_4")
    signals = cached.get("signals", []) if cached else scan_all(min_score=4)
    high = [s for s in signals if s["score"] >= 4]
    success = send_alert_email(high, to)
    return {"success": success, "sent_to": to, "signals_count": len(high)}
