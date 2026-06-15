import os
import time
import httpx
import logging
import asyncio
import threading
from datetime import datetime, timedelta

# Configurare Logging profesional pentru monitorizarea execuției în server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scanner")

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9")
BASE_URL = "https://api.polygon.io"

# Cache-ul centralizat din memoria RAM. 
# Cât timp serverul rulează, 'global_market_data' păstrează istoricul acumulat.
_cache = {
    "tickers": [],
    "status": "pending",  # pending -> se descarcă zilele lipsă; ready -> gata de scanat
    "global_market_data": {},  # Structura din RAM: { "AAPL": [{"t":..., "c":...}, ...], "MSFT": [...] }
    "updated_at": None
}

# Lista companiilor de scanat (S&P 500 selectat)
SP500_ALL = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "BRK.B", "LLY", "AVGO",
    "JPM", "TSLA", "UNH", "V", "XOM", "MA", "HD", "PG", "COST", "JNJ",
    "AMD", "NFLX", "MRK", "ADBE", "CRM", "BAC", "CVX", "PEP", "TMO", "KO",
    "WMT", "WFC", "LIN", "QCOM", "DIS", "ACN", "INTC", "ORCL", "MCD", "INTU",
    "CSCO", "AMAT", "CMCSA", "PFE", "VZ", "DHR", "IBM", "PM", "TXN", "GE",
    "AMCR", "AEE", "AFL", "A", "APD", "ARE", "ALGN", "ALLE", "LNT", "ALL", 
    "MMM", "AOS", "ABT", "ABBV", "AKAM", "ALB", "ABNB"
]
SP500_SET = set(SP500_ALL)

def get_tickers_to_scan() -> list:
    tickers = _cache.get("tickers", [])
    if not tickers:
        return SP500_ALL
    return tickers

def get_filter_status() -> dict:
    return {
        "status": _cache.get("status", "pending"),
        "count": len(_cache.get("tickers", [])),
        "updated_at": _cache.get("updated_at", datetime.utcnow()).isoformat() if _cache.get("updated_at") else None
    }

async def fetch_bulk_day_data(client: httpx.AsyncClient, date_str: str) -> dict:
    """Descarcă pachetul bulk (toată piața) pentru o singură zi din API-ul Polygon."""
    url = f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {"apiKey": POLYGON_API_KEY, "adjusted": "true"}
    
    for attempt in range(1, 4):
        try:
            response = await client.get(url, params=params, timeout=30.0)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning(f"Rate limit (429) la Polygon pentru data {date_str}. Reîncercăm în 65s...")
                await asyncio.sleep(65)
            else:
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Eroare rețea la data {date_str}: {e}")
            await asyncio.sleep(2)
    return {}

async def build_or_extend_ram_history(target_days: int = 65):
    """
    VERIFICARE INTELIGENTĂ: Citește ce există deja în RAM, calculează diferența
    și descarcă din trecut strict zilele de tranzacționare care lipsesc până la 65.
    """
    global_market_data = _cache.get("global_market_data", {})
    
    # Folosim AAPL ca indicator martor pentru a număra zilele prezente în RAM
    current_ram_days = len(global_market_data.get("AAPL", []))
    
    if current_ram_days >= target_days:
        logger.info(f"RAM-ul conține deja {current_ram_days} zile de date (Ținta: {target_days}). Descărcarea istorică este ocolită.")
        return

    needed_days = target_days - current_ram_days
    logger.info(f"RAM-ul conține {current_ram_days} zile. Pornim descărcarea diferențială în trecut pentru cele {needed_days} zile lipsă...")

    # Extragem amprentele unice de timp (timestamps) ale zilelor pe care le avem deja în memorie
    existing_timestamps = {bar["t"] for bar in global_market_data.get("AAPL", [])}

    async with httpx.AsyncClient() as client:
        current_date = datetime.utcnow()
        downloaded_days = 0
        days_checked = 0
        
        # Mergem în trecut zi calendaristică cu zi calendaristică
        while downloaded_days < needed_days and days_checked < 120:
            target_date = current_date - timedelta(days=days_checked)
            days_checked += 1
            
            if target_date.weekday() >= 5:  # Weekend-urile nu sunt zile de tranzacționare
                continue
                
            date_str = target_date.strftime("%Y-%m-%d")
            data = await fetch_bulk_day_data(client, date_str)
            
            if data and data.get("results"):
                first_result_t = data["results"][0].get("t") if data["results"] else None
                
                # Verificăm dacă timestamp-ul acestei zile se potrivește cu ce avem deja în RAM
                if first_result_t and first_result_t in existing_timestamps:
                    logger.info(f"Ziua {date_str} există deja în memoria RAM. Ocolim adăugarea ei.")
                    continue  # Sărim peste ea, mergem mai în spate în istoric

                downloaded_days += 1
                logger.info(f"[{downloaded_days}/{needed_days}] Sincronizat cu succes ziua lipsă: {date_str}. Pauză de siguranță 17s...")
                
                for res in data["results"]:
                    ticker = res.get("T")
                    if ticker in SP500_SET:
                        if ticker not in global_market_data:
                            global_market_data[ticker] = []
                        
                        # Adăugăm datele istorice lipsă
                        global_market_data[ticker].append({
                            "t": res.get("t"), "o": res.get("o"), "h": res.get("h"),
                            "l": res.get("l"), "c": res.get("c"), "v": res.get("v")
                        })
                
                # Facem pauză doar dacă mai avem de descărcat, pentru a respecta limita planului gratuit
                if downloaded_days < needed_days:
                    await asyncio.sleep(17)
            else:
                await asyncio.sleep(1)
                
    # FOARTE IMPORTANT: Deoarece am adus date din trecut, sortăm cronologic listele din RAM
    for t in global_market_data:
        global_market_data[t].sort(key=lambda x: x["t"])
        
    _cache["global_market_data"] = global_market_data
    logger.info(f"Sincronizare RAM finalizată cu succes! Istoricul total consolidat are {len(_cache['global_market_data'].get('AAPL', []))} zile.")

async def do_incremental_refresh():
    """Descarcă doar ziua curentă la finalul ședinței (ora 22:00), o adaugă în RAM și menține limita de 65 de zile."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"Se pornește actualizarea zilnică incrementală pentru data de azi: {today_str}")
    
    async with httpx.AsyncClient() as client:
        data = await fetch_bulk_day_data(client, today_str)
        
        if data and data.get("results"):
            global_market_data = _cache.get("global_market_data", {})
            added_count = 0
            
            for res in data["results"]:
                ticker = res.get("T")
                if ticker in SP500_SET:
                    if ticker not in global_market_data:
                        global_market_data[ticker] = []
                        
                    timestamp = res.get("t")
                    # Evităm duplicarea accidentala a aceleiași zile
                    if not any(bar["t"] == timestamp for bar in global_market_data[ticker]):
                        global_market_data[ticker].append({
                            "t": timestamp, "o": res.get("o"), "h": res.get("h"),
                            "l": res.get("l"), "c": res.get("c"), "v": res.get("v")
                        })
                        added_count += 1
                    
                    # MENȚINERE LIMITĂ FEREASTRĂ GLISANTĂ: Dacă depășim 65 de zile în RAM, ștergem cea mai veche zi
                    if len(global_market_data[ticker]) > 65:
                        global_market_data[ticker].pop(0)
            
            logger.info(f"Actualizare incrementală completă. S-au adăugat lumânări noi pentru {added_count} companii.")
            
            _cache["tickers"] = [t for t in SP500_ALL if t in global_market_data and len(global_market_data[t]) >= 10]
            _cache["status"] = "ready"
            _cache["updated_at"] = datetime.utcnow()
        else:
            logger.warning(f"Nu s-au găsit date bulk pentru ziua de azi ({today_str}). Piața poate fi închisă sau API-ul are întârzieri.")

def _build_filtered_list():
    """Funcție de execuție din thread de fundal care rulează validarea RAM-ului."""
    logger.info("Se lansează verificarea structurii de date din RAM...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Pornește logica de completare până la 65 de zile
        loop.run_until_complete(build_or_extend_ram_history(target_days=65))
    except Exception as e:
        logger.error(f"Eroare critică la verificarea/extinderea cache-ului din RAM: {e}")

    # Permitem scanarea doar dacă companiile au acumulat un istoric destul de lung
    filtered = [t for t in SP500_ALL if t in _cache["global_market_data"] and len(_cache["global_market_data"][t]) >= 55]
    _cache["tickers"] = filtered
    _cache["status"] = "ready" if filtered else "fallback"
    _cache["updated_at"] = datetime.utcnow()

def start_background_filter():
    """Se apelează la pornirea aplicației din main.py pentru a valida structura RAM fără a bloca pornirea serverului."""
    _cache["status"] = "pending"
    t = threading.Thread(target=_build_filtered_list, daemon=True)
    t.start()

def start_daily_refresh():
    """Planificatorul automat în fundal care verifică ora și descarcă ziua curentă la 22:00 UTC."""
    def run_scheduler():
        logger.info("Planificatorul zilnic incremental a fost inițializat pentru ora 22:00 UTC")
        while True:
            now = datetime.utcnow()
            target = now.replace(hour=22, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
                
            sleep_seconds = (target - now).total_seconds()
            time.sleep(sleep_seconds)
            
            # Executăm descărcarea doar de luni până vineri
            if datetime.utcnow().weekday() < 5:
                logger.info("Ceasul a atins 22:00 UTC. Se rulează descărcarea și adăugarea zilei curente în RAM...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(do_incremental_refresh())

    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

def scan_all(min_score: int = 2) -> list:
    """
    SISTEM DE SCANARE TIMPURIE (EARLY WARNING)
    Rulează instantaneu peste datele din RAM folosind filtre macro pe o scară de 65 de zile.
    """
    tickers = get_tickers_to_scan()
    global_data = _cache.get("global_market_data", {})
    results = []

    for ticker in tickers:
        data = global_data.get(ticker, [])
        # Securitate tehnică: avem nevoie de un istoric mediu solid pentru a calcula indicatorii (ex: MA50)
        if len(data) < 55:
            continue

        try:
            prices = [x["c"] for x in data]
            volumes = [x["v"] for x in data]
            
            curr_price = prices[-1]
            prev_price = prices[-2]
            curr_vol = volumes[-1]

            score = 0
            reasons = []

            # 🚨 PILON 1: Trend Strength - Breakout peste MA50 (Standardul Marilor Fonduri)
            # Folosește ultimele 50 de lumânări din cele 65 stocate
            ma50 = sum(prices[-50:]) / 50
            if curr_price > (ma50 * 1.015):  # Prețul trebuie să fie cu peste 1.5% deasupra mediei mobile
                score += 1
                reasons.append(f"Trend Structural Puternic (Preț cu >1.5% peste MA50)")

            # 🚨 PILON 2: Volume Anomaly - Explozie masivă de capital raportată la MA20 Volum (o lună)
            avg_vol_20d = sum(volumes[-21:-1]) / 20
            if avg_vol_20d > 0 and curr_vol > (avg_vol_20d * 1.5):  # Volum cu minimum 50% mai mare decât media
                percent_gain = round((curr_vol / avg_vol_20d - 1) * 100)
                score += 1
                reasons.append(f"Volum Instituțional Anomal (+{percent_gain}% vs MA20 Vol)")

            # 🚨 PILON 3: Medium-Term Momentum - Structură solidă de Higher Highs pe 15 și 30 de zile în urmă
            price_15d_ago = prices[-16]
            price_30d_ago = prices[-31]
            if curr_price > price_15d_ago and price_15d_ago > price_30d_ago:
                score += 1
                total_gain_30d = round(((curr_price - price_30d_ago) / price_30d_ago) * 100, 1)
                reasons.append(f"Momentum Susținut pe Termen Mediu (+{total_gain_30d}% în 30z)")

            # 🚨 PILON 4: Institutional Accumulation - Amprenta volumului pe ultimele 10 zile
            # Volumul mediu din zilele în care prețul a crescut trebuie să fie clar superior zilelor de scădere
            green_days_vol = []
            red_days_vol = []
            for i in range(-10, 0):
                if i == -10:
                    continue
                if prices[i] > prices[i-1]:
                    green_days_vol.append(volumes[i])
                else:
                    red_days_vol.append(volumes[i])
            
            avg_green_vol = sum(green_days_vol) / len(green_days_vol) if green_days_vol else 0
            avg_red_vol = sum(red_days_vol) / len(red_days_vol) if red_days_vol else 0
            
            if avg_green_vol > (avg_red_vol * 1.15) and curr_price > prev_price:
                score += 1
                reasons.append("Acumulare Instituțională (Zilele de creștere au volume net superioare)")

            # Trimitere către interfață dacă îndeplinește scorul setat de utilizator
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
            logger.error(f"Eroare la analiza tehnică a tickerului {ticker}: {e}")
            continue

    # Sortăm descrescător după scor (cele mai bune primele) și performanța de preț a zilei
    results.sort(key=lambda x: (x["score"], x["change_percent"]), reverse=True)
    return results
