from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from datetime import datetime
import json
import os
from scanner import scan_all, analyze_ticker, SP500_TICKERS
from emailer import send_alert_email

app = FastAPI(title="S&P 500 Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache simplu în memorie
_cache = {}

SECTORS = [
    {"name": "Tehnologie",   "ticker": "XLK", "emoji": "💻"},
    {"name": "Financiar",    "ticker": "XLF", "emoji": "🏦"},
    {"name": "Sănătate",     "ticker": "XLV", "emoji": "⚕️"},
    {"name": "Energie",      "ticker": "XLE", "emoji": "⚡"},
    {"name": "Consum Disc.", "ticker": "XLY", "emoji": "🛍️"},
    {"name": "Consum Baz.",  "ticker": "XLP", "emoji": "🛒"},
    {"name": "Industrie",    "ticker": "XLI", "emoji": "⚙️"},
    {"name": "Real Estate",  "ticker": "XLRE","emoji": "🏢"},
    {"name": "Utilități",   "ticker": "XLU", "emoji": "🔋"},
    {"name": "Materiale",    "ticker": "XLB", "emoji": "🪨"},
    {"name": "Comunicații", "ticker": "XLC", "emoji": "📡"},
]

MARKET_TICKERS = ["^GSPC", "^VIX", "^TNX", "DX-Y.NYB"]

def get_quote(ticker: str):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return None
        prev = float(hist["Close"].iloc[-2])
        curr = float(hist["Close"].iloc[-1])
        chg  = round((curr - prev) / prev * 100, 2)
        vol  = int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0
        return {"price": round(curr, 2), "change": chg, "prev": round(prev, 2), "volume": vol}
    except:
        return None

@app.get("/")
def root():
    return {"status": "ok", "time": datetime.utcnow().isoformat(), "tickers": len(SP500_TICKERS)}

@app.get("/api/market")
def market():
    result = {}
    for t in MARKET_TICKERS:
        q = get_quote(t)
        if q:
            result[t] = q
    return result

@app.get("/api/sectors")
def sectors():
    result = []
    for s in SECTORS:
        q = get_quote(s["ticker"])
        result.append({**s, **(q or {"price": None, "change": None})})
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
def early_warning(min_score: int = Query(default=3, ge=1, le=5)):
    """
    Scanează S&P 500 și returnează companiile cu semnal puternic.
    min_score: numărul minim de semne simultane (1-5)
    """
    cache_key = f"ew_{min_score}"
    cached = _cache.get(cache_key)

    # Cache valabil 30 minute
    if cached:
        age_minutes = (datetime.utcnow() - datetime.fromisoformat(cached["scanned_at"])).seconds / 60
        if age_minutes < 30:
            return cached

    results = scan_all(min_score=min_score)
    response = {
        "signals": results,
        "count": len(results),
        "scanned": len(SP500_TICKERS),
        "min_score": min_score,
        "scanned_at": datetime.utcnow().isoformat(),
    }
    _cache[cache_key] = response
    return response

@app.post("/api/early-warning/email")
def send_email(to: str = Query(..., description="Email destinatar")):
    """Trimite email cu alertele curente."""
    cached = _cache.get("ew_4")
    if not cached:
        signals = scan_all(min_score=4)
    else:
        signals = cached.get("signals", [])

    high_conviction = [s for s in signals if s["score"] >= 4]
    success = send_alert_email(high_conviction, to)
    return {"success": success, "sent_to": to, "signals_count": len(high_conviction)}

@app.get("/api/early-warning/scan-now")
def scan_now(background_tasks: BackgroundTasks):
    """Pornește un scan proaspăt în background."""
    def do_scan():
        results = scan_all(min_score=3)
        _cache["ew_3"] = {
            "signals": results,
            "count": len(results),
            "scanned": len(SP500_TICKERS),
            "scanned_at": datetime.utcnow().isoformat(),
        }
        high = [r for r in results if r["score"] >= 4]
        _cache["ew_4"] = {**_cache["ew_3"], "signals": high, "count": len(high)}

        # Trimite email automat dacă e configurat
        alert_email = os.getenv("ALERT_EMAIL")
        if alert_email and high:
            send_alert_email(high, alert_email)

    background_tasks.add_task(do_scan)
    return {"status": "scan started", "tickers": len(SP500_TICKERS)}
