from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
import os
from scanner import scan_all, get_tickers_to_scan, _filtered_tickers_cache, POLYGON_API_KEY, BASE_URL
from emailer import send_alert_email

app = FastAPI(title="S&P 500 Intelligence API")

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

MARKET_TICKERS = {
    "^GSPC": "SPX",
    "^VIX":  "VIX",
    "^TNX":  "TNX",
}


def get_polygon_etf(ticker: str) -> dict:
    try:
        from datetime import timedelta
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
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
    cached = _filtered_tickers_cache.get("tickers", [])
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "tickers": len(cached) if cached else "pending"
    }


@app.get("/api/market")
def market():
    result = {}
    for key, ticker in MARKET_TICKERS.items():
        q = get_polygon_etf("SPY") if key == "^GSPC" else {"price": None, "change": None}
        result[key] = q
    return result


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

    results = scan_all(min_score=min_score)
    tickers = get_tickers_to_scan()

    response = {
        "signals": results,
        "count": len(results),
        "scanned": len(tickers),
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
            "scanned_at": datetime.utcnow().isoformat(),
        }
        _cache["ew_3"] = base
        _cache["ew_4"] = {**base, "signals": [r for r in results if r["score"] >= 4], "count": len([r for r in results if r["score"] >= 4])}

        alert_email = os.getenv("ALERT_EMAIL")
        high = [r for r in results if r["score"] >= 4]
        if alert_email and high:
            send_alert_email(high, alert_email)

    tickers = get_tickers_to_scan()
    background_tasks.add_task(do_scan)
    return {"status": "scan started", "tickers": len(tickers)}


@app.post("/api/early-warning/email")
def send_email(to: str = Query(...)):
    cached = _cache.get("ew_4")
    signals = cached.get("signals", []) if cached else scan_all(min_score=4)
    high = [s for s in signals if s["score"] >= 4]
    success = send_alert_email(high, to)
    return {"success": success, "sent_to": to, "signals_count": len(high)}
