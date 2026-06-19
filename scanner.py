import os
import time
import httpx
import logging
import asyncio
import threading
from datetime import datetime, timedelta

# Configurare Logging profesional pentru monitorizarea în Railway Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scanner")

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9")
BASE_URL = "https://api.polygon.io"

# Cache-ul centralizat din memoria RAM
_cache = {
    "tickers": [],
    "status": "ready",  # Setat direct 'ready' pentru conformitate instantanee cu serviciile Cloud
    "global_market_data": {},  # Structura: { "AAPL": [{"t":..., "c":...}, ... ] }
    "updated_at": datetime.utcnow()
}

# Lista companiilor monitorizate: S&P 500 filtrat după capitalizare de piață > $30B
# Sursă: Slickcharts (cumulative market cap), actualizat 19.06.2026
SP500_ALL = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK.B", "LLY", "AVGO",
    "TSLA", "JPM", "UNH", "V", "XOM", "MA", "HD", "PG", "COST", "JNJ",
    "AMD", "NFLX", "MRK", "ADBE", "CRM", "BAC", "CVX", "PEP", "TMO", "KO",
    "WMT", "WFC", "LIN", "QCOM", "DIS", "ACN", "INTC", "ORCL", "MCD", "INTU",
    "CSCO", "AMAT", "CMCSA", "PFE", "VZ", "DHR", "IBM", "PM", "TXN", "GE",
    "MU", "MS", "KLAC", "GS", "PLTR", "SNDK", "DELL", "GEV", "RTX", "C",
    "PANW", "AXP", "STX", "ANET", "TMUS", "ADI", "VRT", "COF", "PH", "VRTX",
    "FTNT", "NEM", "PWR", "CDNS", "MAR", "SO", "HWM", "NOW", "EQIX", "MDT",
    "TT", "BNY", "FCX", "DUK", "GD", "CME", "PNC", "MCK", "UPS", "USB",
    "CMI", "MNST", "CEG", "ADP", "JCI", "CSX", "WMB", "WM", "ELV", "AMT",
    "SNPS", "KKR", "HCA", "SLB", "HOOD", "MMM", "DDOG", "MRSH", "MDLZ", "FDX",
    "EMR", "ICE", "RCL", "CI", "HLT", "ABNB", "SHW", "MCO", "NOC", "MPWR",
    "APO", "ROST", "NXPI", "MPC", "VLO", "ORLY", "COHR", "ECL", "ITW", "GM",
    "EOG", "PSX", "LITE", "AON", "CL", "CRH", "KMI", "SPG", "CTAS", "NSC",
    "AEP", "TDG", "BSX", "MSI", "WBD", "URI", "NKE", "FIX", "DASH", "TRV",
    "DLR", "RSG", "TFC", "REGN", "HPE", "CIEN", "TER", "APD", "BKR", "PCAR",
    "GWW", "TGT", "TEL", "NUE", "SRE", "AFL", "KEYS", "D", "F", "TRGP",
    "O", "CARR", "LHX", "PSA", "MET", "OKE", "ALL", "OXY", "AJG", "COR",
    "DAL", "FANG", "FAST", "CAH", "DVN", "AME", "MCHP", "ROK", "ODFL", "AZO",
    "EA", "CTVA", "ETR", "NDAQ", "VST", "FITB", "XEL", "EW", "EBAY", "EXC",
    "STT", "GRMN", "CVNA", "HUM", "ON", "WAB", "IDXX", "DHI", "MSCI", "KDP",
    "YUM", "COIN", "ADSK", "XYZ", "CMG", "AMP", "VTR", "STLD", "JBL", "IBKR",
    "CCL", "BDX", "CCI", "AIG", "LYV", "KR", "PEG", "ED", "TTWO", "CBRE",
    "ADM", "SYY", "IRM", "PRU", "UAL", "PCG", "VMC", "WEC", "HSY", "A",
    "PYPL", "EME", "PAYX", "AXON", "HIG", "HBAN", "WAT", "KVUE", "MLM", "MTB",
    "KMB", "ROP", "LVS", "ZTS", "CASY", "HAL", "SATS", "EQT", "EL", "WDAY",
    "NTRS", "CNC", "ACGL", "EXR", "NTAP", "Q", "CBOE", "VICI", "DTE", "ARES",
    "IQV", "AEE", "RJF"
]
SP500_SET = set(SP500_ALL)

# ETF-uri de sectoare si piata (descarcate in RAM dar nu scanate)
ETF_TICKERS = [
    "XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLI", "XLRE", "XLU", "XLB", "XLC",
    "SPY", "VIXY", "TLT", "UUP"
]
ALL_TICKERS_SET = set(SP500_ALL) | set(ETF_TICKERS)

# Pragul minim de zile istorice necesare pentru ca un ticker să fie inclus în scanare
# (trebuie să coincidă cu pragul folosit în scan_all pentru calculul MA50)
MIN_DAYS_REQUIRED = 55

def get_tickers_to_scan() -> list:
    tickers = _cache.get("tickers", [])
    if not tickers:
        return SP500_ALL
    return tickers

def get_filter_status() -> dict:
    return {
        "status": _cache.get("status", "ready"),
        "count": len(_cache.get("tickers", [])),
        "updated_at": _cache.get("updated_at", datetime.utcnow()).isoformat() if _cache.get("updated_at") else None
    }

async def fetch_bulk_day_data(client: httpx.AsyncClient, date_str: str) -> dict:
    """Interoghează API-ul Polygon pentru datele agregate ale întregii piețe într-o zi."""
    url = f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {"apiKey": POLYGON_API_KEY, "adjusted": "true"}
    
    for attempt in range(1, 4):
        try:
            response = await client.get(url, params=params, timeout=30.0)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning(f"Rate limit (429) detectat pentru data {date_str}. Așteptăm 65s...")
                await asyncio.sleep(65)
            elif response.status_code == 403:
                # 403 înseamnă de obicei că datele pentru ziua respectivă nu sunt încă
                # finalizate/disponibile pe planul curent. Așteptăm mult mai mult decât la 429.
                logger.warning(
                    f"403 Forbidden pentru data {date_str} (date probabil neprocesate încă). "
                    f"Încercarea {attempt}/3, așteptăm 5 minute..."
                )
                await asyncio.sleep(300)
            else:
                logger.warning(f"Status neașteptat {response.status_code} pentru {date_str}. Reîncercăm în 2s...")
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Eroare rețea la data {date_str}: {e}")
            await asyncio.sleep(2)
    logger.error(f"Nu s-au putut obține date pentru {date_str} după 3 încercări. Ziua va fi omisă.")
    return {}

async def build_or_extend_ram_history(target_days: int = 65):
    """
    Sincronizare diferențială inteligentă.
    Măsoară ce existea deja în RAM și trage strict zilele lipsă din trecut.
    """
    global_market_data = _cache.get("global_market_data", {})
    current_ram_days = len(global_market_data.get("AAPL", []))
    
    if current_ram_days >= target_days:
        logger.info(f"RAM-ul are deja {current_ram_days} zile stocate. Skip descărcare istorică.")
        return

    needed_days = target_days - current_ram_days
    logger.info(f"RAM-ul conține {current_ram_days} zile. Pornim completarea pentru restul de {needed_days} zile...")

    # Set de amprente de timp (timestamps) pentru eliminarea duplicatelor zilnice
    existing_timestamps = {bar["t"] for bar in global_market_data.get("AAPL", [])}

    async with httpx.AsyncClient() as client:
        current_date = datetime.utcnow()
        downloaded_days = 0
        days_checked = 0
        
        while downloaded_days < needed_days and days_checked < 120:
            target_date = current_date - timedelta(days=days_checked)
            days_checked += 1
            
            if target_date.weekday() >= 5:  # Sărim peste sâmbătă și duminică
                continue
                
            date_str = target_date.strftime("%Y-%m-%d")
            data = await fetch_bulk_day_data(client, date_str)
            
            if data and data.get("results"):
                first_result_t = data["results"][0].get("t") if data["results"] else None
                
                # Dacă ziua din trecut există deja în RAM, o ignorăm și mergem mai departe în spate
                if first_result_t and first_result_t in existing_timestamps:
                    continue

                downloaded_days += 1
                logger.info(f"[{downloaded_days}/{needed_days}] S-a sincronizat ziua istorică lipsă: {date_str}. Pauză API 17s...")
                
                for res in data["results"]:
                    ticker = res.get("T")
                    if ticker in ALL_TICKERS_SET:
                        if ticker not in global_market_data:
                            global_market_data[ticker] = []
                        
                        global_market_data[ticker].append({
                            "t": res.get("t"), "o": res.get("o"), "h": res.get("h"),
                            "l": res.get("l"), "c": res.get("c"), "v": res.get("v")
                        })
                
                if downloaded_days < needed_days:
                    await asyncio.sleep(17)
            else:
                await asyncio.sleep(1)
                
    # Sortăm cronologic datele aduse din trecut pentru ca formulele MA50 să ruleze corect
    for t in global_market_data:
        global_market_data[t].sort(key=lambda x: x["t"])
        
    _cache["global_market_data"] = global_market_data
    logger.info(f"Sincronizare finalizată! Istoric consolidat în RAM: {len(_cache['global_market_data'].get('AAPL', []))} zile.")

async def do_incremental_refresh():
    """Actualizează memoria RAM cu lumânarea zilei de tranzacționare anterioare (rulează la 06:00 UTC, suficient după închiderea pieței)."""
    target_date = datetime.utcnow() - timedelta(days=1)
    # Dacă "ieri" UTC a fost weekend, mergem înapoi până la ultima zi lucrătoare
    while target_date.weekday() >= 5:
        target_date -= timedelta(days=1)
    today_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"Rulare actualizare incrementală zilnică: {today_str}")
    
    async with httpx.AsyncClient() as client:
        data = await fetch_bulk_day_data(client, today_str)
        
        if data and data.get("results"):
            global_market_data = _cache.get("global_market_data", {})
            added_count = 0
            
            for res in data["results"]:
                ticker = res.get("T")
                if ticker in ALL_TICKERS_SET:
                    if ticker not in global_market_data:
                        global_market_data[ticker] = []
                        
                    timestamp = res.get("t")
                    if not any(bar["t"] == timestamp for bar in global_market_data[ticker]):
                        global_market_data[ticker].append({
                            "t": timestamp, "o": res.get("o"), "h": res.get("h"),
                            "l": res.get("l"), "c": res.get("c"), "v": res.get("v")
                        })
                        added_count += 1
                    
                    # FEREASTRĂ GLISANTĂ: Dacă depășim 65 de zile stocate, aruncăm cea mai veche zi din RAM
                    if len(global_market_data[ticker]) > 65:
                        global_market_data[ticker].pop(0)
            
            logger.info(f"Actualizare incrementală completă. Adăugat date noi pentru {added_count} companii.")
            _cache["tickers"] = [t for t in SP500_ALL if t in global_market_data and len(global_market_data[t]) >= MIN_DAYS_REQUIRED]
            _cache["updated_at"] = datetime.utcnow()

def _build_filtered_list():
    """Execuție din thread separat pentru a lăsa FastAPI liber în rețea."""
    logger.info("Thread secundar activat. Pornim colectarea datelor istorice...")
    _cache["status"] = "updating"
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(build_or_extend_ram_history(target_days=65))
    except Exception as e:
        logger.error(f"Eroare în execuția threadului de sincronizare: {e}")

    # Permitem scanarea activă doar pentru companiile care au acumulat pragul minim de date de analiză
    filtered = [t for t in SP500_ALL if t in _cache["global_market_data"] and len(_cache["global_market_data"][t]) >= MIN_DAYS_REQUIRED]
    _cache["tickers"] = filtered
    _cache["status"] = "ready"
    _cache["updated_at"] = datetime.utcnow()

def start_background_filter():
    """Lansează threadul asincron de fundal."""
    t = threading.Thread(target=_build_filtered_list, daemon=True)
    t.start()

def start_daily_refresh():
    """Planificatorul intern de timp (Cron-Job în RAM) pentru ora 06:00 UTC."""
    def run_scheduler():
        logger.info("Planificator incremental inițializat (Așteaptă ora 06:00 UTC)")
        while True:
            now = datetime.utcnow()
            target = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
                
            sleep_seconds = (target - now).total_seconds()
            time.sleep(sleep_seconds)
            
            if datetime.utcnow().weekday() < 5:
                logger.info("Ceasul a atins 06:00 UTC. Rulăm adăugarea automată a lumânării de azi...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(do_incremental_refresh())

    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

def scan_all(min_score: int = 2) -> list:
    """
    SISTEMUL MATEMATIC DE FILTRARE (EARLY WARNING)
    Analizează istoricul curat de 65 de zile direct din memoria RAM.
    """
    tickers = get_tickers_to_scan()
    global_data = _cache.get("global_market_data", {})
    results = []

    for ticker in tickers:
        data = global_data.get(ticker, [])
        if len(data) < MIN_DAYS_REQUIRED:
            continue

        try:
            prices = [x["c"] for x in data]
            volumes = [x["v"] for x in data]
            
            curr_price = prices[-1]
            prev_price = prices[-2]
            curr_vol = volumes[-1]

            score = 0
            reasons = []

            # 🚨 PILON 1: Trend Strength - Confirmare structurală: preț peste MA20 ȘI MA50, cu MA20 în creștere
            ma20 = sum(prices[-20:]) / 20
            ma50 = sum(prices[-50:]) / 50
            ma20_10d_ago = sum(prices[-30:-10]) / 20
            above_ma20 = curr_price > ma20
            above_ma50 = curr_price > (ma50 * 1.015)  # minim 1.5% peste MA50
            ma20_rising = ma20 > ma20_10d_ago
            if above_ma20 and above_ma50 and ma20_rising:
                upside_ma20 = (curr_price / ma20 - 1) * 100
                score += 1
                reasons.append(f"Trend Structural Puternic (Peste MA20 +{upside_ma20:.1f}% și MA50, cu MA20 în creștere)")

            # 🚨 PILON 2: Volume Anomaly - Explozie de volum raportată la MA20 Volum (o lună de trading)
            avg_vol_20d = sum(volumes[-21:-1]) / 20
            if avg_vol_20d > 0 and curr_vol > (avg_vol_20d * 1.5):  # Volum cu minimum +50% peste medie
                percent_gain = round((curr_vol / avg_vol_20d - 1) * 100)
                score += 1
                reasons.append(f"Volum Instituțional Anomal (+{percent_gain}% vs MA20 Vol)")

            # 🚨 PILON 3: Medium-Term Momentum - Confirmare Higher Highs structural pe 15 și 30 de zile în urmă
            price_15d_ago = prices[-16]
            price_30d_ago = prices[-31]
            if curr_price > price_15d_ago and price_15d_ago > price_30d_ago:
                score += 1
                total_gain_30d = round(((curr_price - price_30d_ago) / price_30d_ago) * 100, 1)
                reasons.append(f"Momentum Susținut pe Termen Mediu (+{total_gain_30d}% în 30z)")

            # 🚨 PILON 4: Institutional Accumulation - Amprenta Smart Money pe ultimele 9 zile (vs ziua anterioară fiecăreia)
            green_days_vol = []
            red_days_vol = []
            for i in range(-9, 0):
                if prices[i] > prices[i-1]:
                    green_days_vol.append(volumes[i])
                else:
                    red_days_vol.append(volumes[i])
            
            avg_green_vol = sum(green_days_vol) / len(green_days_vol) if green_days_vol else 0
            avg_red_vol = sum(red_days_vol) / len(red_days_vol) if red_days_vol else 0
            
            if avg_green_vol > (avg_red_vol * 1.15) and curr_price > prev_price:
                score += 1
                reasons.append("Acumulare Instituțională (Zilele de creștere au volume net superioare)")

            # Construim rezultatul dacă trece de filtrul scorului minim selectat
            if score >= min_score:
                price_day_change = ((curr_price - prev_price) / prev_price) * 100
                results.append({
                    "ticker": ticker,
                    "price": round(curr_price, 2),
                    "change_percent": round(price_day_change, 2),
                    "volume": int(curr_vol),
                    "score": score,
                    "signals": reasons,
                    "scanned_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            continue

    # Sortare: Scorul cel mai mare primul, iar la scoruri egale, sortare după randamentul zilnic (%)
    results.sort(key=lambda x: (x["score"], x["change_percent"]), reverse=True)
    return results
