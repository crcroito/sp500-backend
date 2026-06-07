import yfinance as yf
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def analyze_ticker(ticker: str) -> Optional[Dict]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="90d", timeout=10)
        if hist is None or len(hist) < 20:
            return None

        closes  = hist["Close"]
        volumes = hist["Volume"]
        current_price = float(closes.iloc[-1])
        current_vol   = float(volumes.iloc[-1])

        # ── SEMN 1: Earnings Surprise ──
        earnings_surprise = False
        earnings_note = ""
        try:
            info = t.info or {}
            eps_a = info.get("trailingEps", 0) or 0
            eps_e = info.get("forwardEps",  0) or 0
            if eps_e and eps_a and abs(eps_e) > 0:
                beat = (eps_a - eps_e) / abs(eps_e) * 100
                if beat > 10:
                    earnings_surprise = True
                    earnings_note = f"EPS beat +{beat:.0f}%"
        except:
            pass

        # ── SEMN 2: Analyst Revision ──
        analyst_revision = False
        analyst_note = ""
        try:
            info = t.info or {}
            target = info.get("targetMeanPrice", 0) or 0
            rec    = info.get("recommendationMean", 3) or 3
            if target and current_price:
                upside = (target - current_price) / current_price * 100
                if upside > 15 and rec < 2.2:
                    analyst_revision = True
                    analyst_note = f"Target +{upside:.0f}% upside"
        except:
            pass

        # ── SEMN 3: Volume Anomaly ──
        volume_anomaly = False
        volume_note = ""
        try:
            avg_vol = float(volumes.iloc[-20:-1].mean())
            if avg_vol > 0:
                ratio = current_vol / avg_vol
                if ratio > 1.5:
                    volume_anomaly = True
                    volume_note = f"Volum {ratio:.1f}x față de medie"
        except:
            pass

        # ── SEMN 4: Relative Strength ──
        relative_strength = False
        rs_note = ""
        try:
            ret5  = (closes.iloc[-1] / closes.iloc[-5]  - 1) * 100
            ret20 = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100
            ma50  = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean()
            if ret5 > 2 and ret20 > 5 and current_price > ma50:
                relative_strength = True
                rs_note = f"+{ret5:.1f}% (5z), +{ret20:.1f}% (20z), >MA50"
        except:
            pass

        # ── SEMN 5: Institutional ──
        inst_accumulation = False
        inst_note = ""
        try:
            info = t.info or {}
            inst = info.get("heldPercentInstitutions", 0) or 0
            if inst < 1: inst *= 100
            if inst > 60:
                inst_accumulation = True
                inst_note = f"Inst. ownership {inst:.0f}%"
        except:
            pass

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

        try:
            info   = t.info or {}
            name   = info.get("longName", ticker)
            sector = info.get("sector", "N/A")
            pe     = info.get("trailingPE", None)
        except:
            name, sector, pe = ticker, "N/A", None

        chg1 = float((closes.iloc[-1] / closes.iloc[-2] - 1) * 100) if len(closes) >= 2 else 0
        chg5 = float((closes.iloc[-1] / closes.iloc[-5] - 1) * 100) if len(closes) >= 5 else 0

        return {
            "ticker":     ticker,
            "name":       name,
            "sector":     sector,
            "price":      round(current_price, 2),
            "change_1d":  round(chg1, 2),
            "change_5d":  round(chg5, 2),
            "pe":         round(pe, 1) if pe else None,
            "score":      score,
            "signals":    signals,
            "notes":      notes,
            "scanned_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error {ticker}: {e}")
        return None


def scan_all(min_score: int = 3) -> List[Dict]:
    results = []
    total = len(SP500_TICKERS)
    for i, ticker in enumerate(SP500_TICKERS):
        logger.info(f"Scanning {ticker} ({i+1}/{total})")
        result = analyze_ticker(ticker)
        if result and result["score"] >= min_score:
            results.append(result)
        # Pauză între request-uri ca să nu fie blocat de Yahoo Finance
        time.sleep(0.5)

    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
