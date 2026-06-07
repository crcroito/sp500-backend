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

def get_price_data(ticker: str) -> Optional[Dict]:
    """Obține date de preț și volum pentru ultimele 90 zile."""
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        res = requests.get(url, params={"apiKey": POLYGON_API_KEY, "adjusted": "true", "sort": "asc"}, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        results = data.get("results", [])
        if len(results) < 20:
            return None
        return results
    except Exception as e:
        logger.error(f"Price data error {ticker}: {e}")
        return None

def get_ticker_details(ticker: str) -> Optional[Dict]:
    """Obține detalii despre companie."""
    try:
        url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
        res = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=10)
        if res.status_code != 200:
            return None
        return res.json().get("results", {})
    except:
        return None

def get_financials(ticker: str) -> Optional[Dict]:
    """Obține date financiare."""
    try:
        url = f"{BASE_URL}/vX/reference/financials"
        res = requests.get(url, params={"apiKey": POLYGON_API_KEY, "ticker": ticker, "limit": 1}, timeout=10)
        if res.status_code != 200:
            return None
        results = res.json().get("results", [])
        return results[0] if results else None
    except:
        return None

def analyze_ticker(ticker: str) -> Optional[Dict]:
    try:
        bars = get_price_data(ticker)
        if not bars or len(bars) < 20:
            return None

        closes  = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        current_price = closes[-1]
        current_vol   = volumes[-1]

        # ── SEMN 1: Earnings Surprise (Relative price jump > 5% în ultima zi) ──
        earnings_surprise = False
        earnings_note = ""
        if len(closes) >= 2:
            day_chg = (closes[-1] / closes[-2] - 1) * 100
            if day_chg > 5:
                earnings_surprise = True
                earnings_note = f"Mișcare puternică +{day_chg:.1f}% azi"

        # ── SEMN 2: Analyst Revision (preț deasupra MA20 și trend pozitiv) ──
        analyst_revision = False
        analyst_note = ""
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ma20
        if current_price > ma20 * 1.05 and ma20 > ma50:
            analyst_revision = True
            analyst_note = f"Deasupra MA20 cu +{((current_price/ma20)-1)*100:.1f}%, trend pozitiv"

        # ── SEMN 3: Volume Anomaly ──
        volume_anomaly = False
        volume_note = ""
        avg_vol = sum(volumes[-20:-1]) / 19 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        if avg_vol > 0:
            ratio = current_vol / avg_vol
            if ratio > 1.5:
                volume_anomaly = True
                volume_note = f"Volum {ratio:.1f}x față de medie 20z"

        # ── SEMN 4: Relative Strength ──
        relative_strength = False
        rs_note = ""
        if len(closes) >= 20:
            ret5  = (closes[-1] / closes[-5]  - 1) * 100 if len(closes) >= 5  else 0
            ret20 = (closes[-1] / closes[-20] - 1) * 100
            if ret5 > 2 and ret20 > 5 and current_price > ma50:
                relative_strength = True
                rs_note = f"+{ret5:.1f}% (5z), +{ret20:.1f}% (20z), >MA50"

        # ── SEMN 5: Institutional Accumulation (volum crescut consistent) ──
        inst_accumulation = False
        inst_note = ""
        if len(volumes) >= 10:
            recent_avg = sum(volumes[-5:]) / 5
            older_avg  = sum(volumes[-20:-5]) / 15 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            if older_avg > 0 and recent_avg / older_avg > 1.3:
                inst_accumulation = True
                inst_note = f"Volum mediu 5z este {recent_avg/older_avg:.1f}x față de medie 20z"

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

        # Detalii companie
        details = get_ticker_details(ticker)
        name   = details.get("name", ticker) if details else ticker
        sector = details.get("sic_description", "N/A") if details else "N/A"

        chg1 = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0
        chg5 = (closes[-1] / closes[-5] - 1) * 100 if len(closes) >= 5 else 0

        return {
            "ticker":     ticker,
            "name":       name,
            "sector":     sector,
            "price":      round(current_price, 2),
            "change_1d":  round(chg1, 2),
            "change_5d":  round(chg5, 2),
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
        time.sleep(0.15)  # Polygon permite 5 req/sec pe planul gratuit

    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
