import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Top 100 S&P 500 companies (extins la 500 în prod)
SP500_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","BRK.B","LLY","AVGO",
    "TSLA","JPM","UNH","V","XOM","COST","MA","PG","JNJ","HD",
    "ABBV","BAC","MRK","CVX","KO","NFLX","ORCL","CRM","AMD","PEP",
    "TMO","ACN","MCD","ABT","CSCO","WMT","LIN","DHR","TXN","PM",
    "NEE","ADBE","INTU","CAT","ISRG","UPS","HON","AMGN","IBM","GS",
    "SPGI","BLK","BKNG","AXP","RTX","GILD","SYK","ELV","MDT","TJX",
    "PLD","VRTX","REGN","PANW","ADI","LRCX","MU","KLAC","SNPS","CDNS",
    "CI","CVS","MDLZ","ZTS","BSX","EOG","SO","DUK","ICE","MCO",
    "WM","APD","GD","NOC","ITW","EMR","MMC","AON","AIG","PRU",
    "CME","COP","SLB","PSA","SPG","WELL","AMT","EQIX","PH","ROK",
    "UBER","ABNB","DASH","COIN","PLTR","CRWD","SNOW","NET","ZS","DDOG",
    "MELI","SE","SHOP","SPOT","RBLX","U","HOOD","SOFI","AFRM","UPST",
]

def analyze_ticker(ticker: str) -> Optional[Dict]:
    """Analizează un ticker și returnează semnalele detectate."""
    try:
        t = yf.Ticker(ticker)

        # Date istorice 90 zile
        hist = t.history(period="90d")
        if len(hist) < 30:
            return None

        closes = hist["Close"]
        volumes = hist["Volume"]

        current_price = float(closes.iloc[-1])
        current_vol = float(volumes.iloc[-1])

        # ── SEMN 1: Earnings Surprise ──────────────────────────
        earnings_surprise = False
        earnings_note = ""
        try:
            info = t.info
            if info:
                eps_actual = info.get("trailingEps", 0)
                eps_estimate = info.get("forwardEps", 0)
                if eps_estimate and eps_actual:
                    beat_pct = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
                    if beat_pct > 10:
                        earnings_surprise = True
                        earnings_note = f"EPS beat +{beat_pct:.0f}%"
        except:
            pass

        # ── SEMN 2: Analyst Revision Momentum ──────────────────
        analyst_revision = False
        analyst_note = ""
        try:
            info = t.info if hasattr(t, 'info') else {}
            target = info.get("targetMeanPrice", 0)
            if target and current_price:
                upside = ((target - current_price) / current_price) * 100
                rec = info.get("recommendationMean", 3)
                if upside > 15 and rec and rec < 2.2:
                    analyst_revision = True
                    analyst_note = f"Target +{upside:.0f}% upside, rating {rec:.1f}/5"
        except:
            pass

        # ── SEMN 3: Volume Anomaly ──────────────────────────────
        volume_anomaly = False
        volume_note = ""
        try:
            avg_vol_20 = float(volumes.iloc[-20:].mean())
            if avg_vol_20 > 0:
                vol_ratio = current_vol / avg_vol_20
                if vol_ratio > 1.5:
                    volume_anomaly = True
                    volume_note = f"Volum {vol_ratio:.1f}x față de medie 20z"
        except:
            pass

        # ── SEMN 4: Relative Strength ───────────────────────────
        relative_strength = False
        rs_note = ""
        try:
            ret_5d  = (closes.iloc[-1] / closes.iloc[-5]  - 1) * 100
            ret_20d = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100
            ret_50d = (closes.iloc[-1] / closes.iloc[-50] - 1) * 100 if len(closes) >= 50 else 0

            # Deasupra MA50
            ma50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else closes.mean()
            above_ma50 = current_price > ma50

            # Momentum pozitiv pe multiple timeframe-uri
            if ret_5d > 2 and ret_20d > 5 and above_ma50:
                relative_strength = True
                rs_note = f"+{ret_5d:.1f}% (5z) / +{ret_20d:.1f}% (20z) / deasupra MA50"
        except:
            pass

        # ── SEMN 5: Institutional Accumulation ─────────────────
        inst_accumulation = False
        inst_note = ""
        try:
            info = t.info if hasattr(t, 'info') else {}
            inst_own = info.get("institutionalOwnershipPercentage", 0) or \
                       info.get("heldPercentInstitutions", 0)
            if inst_own:
                if isinstance(inst_own, float) and inst_own < 1:
                    inst_own = inst_own * 100
                if inst_own > 60:
                    inst_accumulation = True
                    inst_note = f"Institutional ownership {inst_own:.0f}%"
        except:
            pass

        # ── SCOR FINAL ─────────────────────────────────────────
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

        # Informații companie
        try:
            info = t.info
            name = info.get("longName", ticker)
            sector = info.get("sector", "N/A")
            market_cap = info.get("marketCap", 0)
            pe = info.get("trailingPE", None)
        except:
            name = ticker
            sector = "N/A"
            market_cap = 0
            pe = None

        # Change 1 zi
        change_1d = float((closes.iloc[-1] / closes.iloc[-2] - 1) * 100) if len(closes) >= 2 else 0
        change_5d = float((closes.iloc[-1] / closes.iloc[-5] - 1) * 100) if len(closes) >= 5 else 0

        return {
            "ticker":     ticker,
            "name":       name,
            "sector":     sector,
            "price":      round(current_price, 2),
            "change_1d":  round(change_1d, 2),
            "change_5d":  round(change_5d, 2),
            "market_cap": market_cap,
            "pe":         round(pe, 1) if pe else None,
            "score":      score,
            "signals":    signals,
            "notes":      notes,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None


def scan_all(min_score: int = 3) -> List[Dict]:
    """Scanează toate ticker-ele și returnează cele cu scor >= min_score."""
    results = []
    total = len(SP500_TICKERS)
    for i, ticker in enumerate(SP500_TICKERS):
        logger.info(f"Scanning {ticker} ({i+1}/{total})")
        result = analyze_ticker(ticker)
        if result and result["score"] >= min_score:
            results.append(result)

    # Sortează după scor descrescător
    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
