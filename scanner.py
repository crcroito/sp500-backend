import requests
import time
import threading
import schedule
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"
SP500_ALL = ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "BRK.B", "LLY", "AVGO", "JPM", "TSLA", "UNH", "V", "XOM", "MA", "HD", "PG", "COST", "JNJ", "AMD", "NFLX", "MRK", "ADBE", "CRM", "BAC", "CVX", "PEP", "TMO", "KO", "WMT", "WFC", "LIN", "QCOM", "DIS", "ACN", "INTC", "ORCL", "MCD", "INTU", "CSCO", "AMAT", "CMCSA", "PFE", "VZ", "DHR", "IBM", "PM", "TXN", "GE", "AMCR", "AEE", "AFL", "A", "APD", "ARE", "ALGN", "ALLE", "LNT", "ALL", "MMM", "AOS", "ABT", "ABBV", "AKAM", "ALB", "ABNB"]

_cache = {"tickers": SP500_ALL, "updated_at": None, "status": "pending", "global_market_data": {}}

def get_global_market_history(days_back=65):
    historical_data = {}
    current_date = datetime.now()
    dates = [(current_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days_back + 1) if (current_date - timedelta(days=i)).weekday() < 5]
    for date_str in reversed(dates):
        url = f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
        try:
            res = requests.get(url, params={"apiKey": POLYGON_API_KEY, "adjusted": "true"}, timeout=10)
            if res.status_code == 200:
                for bar in res.json().get("results", []):
                    ticker = bar.get("T")
                    if ticker in SP500_ALL:
                        if ticker not in historical_data: historical_data[ticker] = []
                        historical_data[ticker].append({"c": bar["c"], "v": bar["v"]})
                time.sleep(12)
        except: continue
    return historical_data

def _worker():
    logger.info(">>> Începe actualizarea datelor de piață...")
    try:
        _cache["global_market_data"] = get_global_market_history()
        _cache["status"] = "ready"
        _cache["updated_at"] = datetime.utcnow()
        logger.info(">>> Date actualizate cu succes.")
    except Exception as e:
        logger.error(f"Eroare update: {e}")
        _cache["status"] = "error"

def start_background_filter():
    # Pornire inițială
    threading.Thread(target=_worker, daemon=True).start()

def start_daily_refresh():
    # Programare zilnică
    def run_scheduler():
        schedule.every().day.at("01:00").do(_worker)
        while True:
            schedule.run_pending()
            time.sleep(60)
    threading.Thread(target=run_scheduler, daemon=True).start()
    logger.info(">>> Scheduler zilnic pornit pentru ora 01:00 UTC.")

def get_filter_status(): return {"status": _cache["status"], "updated_at": _cache["updated_at"].isoformat() if _cache["updated_at"] else None}
def get_tickers_to_scan(): return _cache["tickers"]

# Păstrează aici funcțiile tale originale: analyze_ticker_in_memory și scan_all
