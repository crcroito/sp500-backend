from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import requests
from datetime import datetime, timedelta
import json

app = FastAPI(title="S&P 500 Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sector ETFs
SECTORS = [
    {"name": "Tehnologie",    "ticker": "XLK", "emoji": "💻"},
    {"name": "Financiar",     "ticker": "XLF", "emoji": "🏦"},
    {"name": "Sănătate",      "ticker": "XLV", "emoji": "⚕️"},
    {"name": "Energie",       "ticker": "XLE", "emoji": "⚡"},
    {"name": "Consum Disc.",   "ticker": "XLY", "emoji": "🛍️"},
    {"name": "Consum Baz.",    "ticker": "XLP", "emoji": "🛒"},
    {"name": "Industrie",     "ticker": "XLI", "emoji": "⚙️"},
    {"name": "Real Estate",   "ticker": "XLRE","emoji": "🏢"},
    {"name": "Utilități",     "ticker": "XLU", "emoji": "🔋"},
    {"name": "Materiale",     "ticker": "XLB", "emoji": "🪨"},
    {"name": "Comunicații",   "ticker": "XLC", "emoji": "📡"},
]

MARKET_TICKERS = ["^GSPC", "^VIX", "^TNX", "DX-Y.NYB"]

GEM_TICKERS = ["NVDA","META","LLY","AMZN","AVGO","UBER","MSFT","MU","TSM","GOOGL","WELL","ANET"]

def get_quote(ticker: str):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return None
        prev  = float(hist["Close"].iloc[-2])
        curr  = float(hist["Close"].iloc[-1])
        chg   = round((curr - prev) / prev * 100, 2)
        vol   = int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0
        return {"price": round(curr, 2), "change": chg, "prev": round(prev, 2), "volume": vol}
    except Exception as e:
        return None

@app.get("/")
def root():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

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

@app.get("/api/gems")
def gems():
    result = []
    for ticker in GEM_TICKERS:
        q = get_quote(ticker)
        if q:
            result.append({"ticker": ticker, **q})
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
