import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"

SP500_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","BRK.B","LLY","AVGO","TSLA",
    "JPM","UNH","V","XOM","COST","MA","PG","JNJ","HD","ABBV",
    "BAC","MRK","CVX","KO","NFLX","ORCL","CRM","AMD","PEP","TMO",
    "ACN","MCD","ABT","CSCO","WMT","LIN","TXN","ADBE","INTU","CAT",
    "ISRG","HON","AMGN","IBM","GS","SPGI","BLK","BKNG","AXP","RTX",
    "GILD","SYK","ELV","MDT","TJX","PLD","VRTX","REGN","PANW","ADI",
    "LRCX","MU","KLAC","SNPS","CDNS","CI","CVS","MDLZ","ZTS","BSX",
    "EOG","SO","DUK","ICE","MCO","WM","APD","GD","NOC","ITW",
    "UBER","ANET","WELL","CRWD","NET","DDOG","MELI","SHOP","TMUS","NEM",
]

def get_bars(ticker: str, days: int = 120) -> Optional[List]:
    try:
        end   = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url   = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        res   = requests.get(url, params={
            "apiKey": POLYGON_API_KEY,
            "adjusted": "true",
            "sort": "asc",
            "limit": 120,
        }, timeout=10)
        if res.status_code != 200:
            return None
        results = res.json().get("results", [])
        return results if len(results) >= 10 else None
    except Exception as e:
        logger.error(f"Bars error {ticker}: {e}")
        return None

def analyze_ticker(ticker: str) -> Optional[Dict]:
    try:
        bars = get_bars(ticker)
        if not bars:
            return None

        closes  = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        highs   = [b["h"] for b in bars]
        lows    = [b["l"] for b in bars]

        current_price = closes[-1]
        prev_price    = closes[-2] if len(closes) >= 2 else current_price

        # Moving averages
        ma20 = sum(closes[-20:]) / min(20, len(closes))
        ma50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else ma20
        ma10 = sum(closes[-10:]) / min(10, len(closes))

        # ── SEMN 1: Mișcare puternică recentă (ultimele 3 zile) ──
        earnings_surprise = False
        earnings_note = ""
        if len(closes) >= 4:
            chg3d = (closes[-1] / closes[-4] - 1) * 100
            chg1d = (closes[-1] / closes[-2] - 1) * 100
            if chg3d > 5 or chg1d > 3:
                earnings_surprise = True
                earnings_note = f"Mișcare +{chg3d:.1f}% în 3 zile, +{chg1d:.1f}% ieri"

        # ── SEMN 2: Trend ascendent puternic ──
        analyst_revision = False
        analyst_note = ""
        if len(closes) >= 50:
            above_ma20 = current_price > ma20
            above_ma50 = current_price > ma50
            ma20_rising = ma20 > sum(closes[-30:-10]) / 20
            if above_ma20 and above_ma50 and ma20_rising:
                upside_ma20 = (current_price / ma20 - 1) * 100
                analyst_revision = True
                analyst_note = f"Deasupra MA20 (+{upside_ma20:.1f}%) și MA50, trend up"

        # ── SEMN 3: Volume Anomaly (volum mare față de medie) ──
        volume_anomaly = False
        volume_note = ""
        if len(volumes) >= 20:
            avg_vol_20 = sum(volumes[-21:-1]) / 20
            avg_vol_5  = sum(volumes[-6:-1]) / 5
            if avg_vol_20 > 0:
                ratio = avg_vol_5 / avg_vol_20
                if ratio > 1.3:
                    volume_anomaly = True
                    volume_note = f"Volum mediu 5z = {ratio:.1f}x față de medie 20z"

        # ── SEMN 4: Relative Strength (performanță > medie) ──
        relative_strength = False
        rs_note = ""
        if len(closes) >= 20:
            ret5  = (closes[-1] / closes[-6]  - 1) * 100 if len(closes) >= 6  else 0
            ret10 = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
            ret20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
            # Companie în trend pozitiv pe 3 timeframes
            if ret5 > 1 and ret10 > 3 and ret20 > 5:
                relative_strength = True
                rs_note = f"+{ret5:.1f}% (5z), +{ret10:.1f}% (10z), +{ret20:.1f}% (20z)"

        # ── SEMN 5: Institutional Accumulation (volum crescut consistent pe 10z) ──
        inst_accumulation = False
        inst_note = ""
        if len(volumes) >= 30:
            recent10 = sum(volumes[-10:]) / 10
            prev20   = sum(volumes[-30:-10]) / 20
            if prev20 > 0 and recent10 / prev20 > 1.2:
                # Verifică că prețul a crescut și el
                price_up = closes[-1] > closes[-10]
                if price_up:
                    inst_accumulation = True
                    inst_note = f"Volum 10z = {recent10/prev20:.1f}x față de anterior, preț în creștere"

        signals = {
            "earnings_surprise":  earnings_surprise,
            "analyst_revision":   analyst_revision,
            "volume_anomaly":     volume_anomaly,
            "relative_strength":  relative_strength,
            "inst_accumulation":  inst_accumulation,
        }
        notes = {
            "earnings_surprise":  earnings_note,
            "analyst_revision":   analyst_note,
            "volume_anomaly":     volume_note,
            "relative_strength":  rs_note,
            "inst_accumulation":  inst_note,
        }
        score = sum(signals.values())

        chg1  = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0
        chg5  = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
        chg20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0

        return {
            "ticker":     ticker,
            "name":       ticker,
            "sector":     "S&P 500",
            "price":      round(current_price, 2),
            "change_1d":  round(chg1, 2),
            "change_5d":  round(chg5, 2),
            "change_20d": round(chg20, 2),
            "pe":         None,
            "score":      score,
            "signals":    signals,
            "notes":      notes,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None


def scan_all(min_score: int = 3) -> List[Dict]:
    results = []
    total = len(SP500_TICKERS)
    for i, ticker in enumerate(SP500_TICKERS):
        logger.info(f"Scanning {ticker} ({i+1}/{total})")
        result = analyze_ticker(ticker)
        if result and result["score"] >= min_score:
            results.append(result)
        time.sleep(0.15)
    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
