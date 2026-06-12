import requests
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Configurare Logging pentru vizibilitate în consola Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"

# Lista completă S&P 500 (componente oficiale)
SP500_ALL = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB","AKAM","ALB","ARE","ALGN",
    "ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN","AMCR","AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP",
    "AME","AMGN","APH","ADI","ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG","AIZ","T",
    "ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC","BBWI","BAX","BDX","BRK.B","BBY","BIO",
    "TECH","BIIB","BLK","BX","BA","BSX","BMY","AVGO","BR","BRO","BLDR","BG","CDNS","CPT","CPB","COF",
    "CAH","KMX","CCL","CARR","CTLT","CAT","CBOE","CBRE","CDW","CE","COR","CNC","CDAY","CF","CRL","SCHW",
    "CHTR","CVX","CMG","CB","CHD","CI","CINF","CTAS","CSCO","C","CFG","CLX","CME","CMS","KO","CTSH",
    "CL","CMCSA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CPAY","CTVA","CSGP","COST","CTRA",
    "CCI","CSX","CMI","CVS","DHR","DRI","DVA","DAY","DECK","DE","DELL","DAL","DVN","DXCM","FANG","DLR",
    "DFS","DG","DLTR","D","DPZ","DOV","DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX","EW",
    "EA","ELV","LLY","EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR","ESS","EL","ETSY","EG",
    "EVRG","ES","EXC","EXPE","EXPD","EXR","XOM","FFIV","FDS","FICO","FAST","FRT","FDX","FIS","FITB",
    "FSLR","FE","FI","FMC","F","FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT","GE","GEHC","GEV",
    "GEN","GNRC","GD","GIS","GM","GPC","GILD","GS","HAL","HIG","HAS","HCA","DOC","HSIC","HSY","HES",
    "HPE","HLT","HOLX","HD","HON","HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX","IDXX",
    "ITW","INCY","IR","PODD","INTC","ICE","IFF","IP","IPG","INTU","ISRG","IVZ","INVH","IQV","IRM","JBHT",
    "JBL","JKHY","J","JNJ","JCI","JPM","K","KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KLAC","KHC",
    "KR","LHX","LH","LRCX","LW","LVS","LDOS","LEN","LIN","LYV","LKQ","LMT","L","LOW","LULU","LYB",
    "MTB","MRO","MPC","MKTX","MAR","MMC","MLM","MAS","MA","MTCH","MKC","MCD","MCK","MDT","MRK","META",
    "MET","MTD","MGM","MCHP","MU","MSFT","MAA","MRNA","MHK","MOH","TAP","MDLZ","MPWR","MNST","MCO","MS",
    "MOS","MSI","MSCI","NDAQ","NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC","NTRS",
    "NOC","NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY","OXY","ODFL","OMC","ON","OKE","ORCL","OTIS",
    "PCAR","PKG","PANW","PARA","PH","PAYX","PAYC","PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC",
    "POOL","PPG","PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","PWR","QCOM","DGX","RL",
    "RJF","RTX","O","REG","REGN","RF","RSG","RMD","RVTY","ROK","ROL","ROP","ROST","RCL","SPGI","CRM",
    "SBAC","SLB","STX","SRE","NOW","SHW","SPG","SJM","SW","SNA","SOLV","SO","LUV","SWK","SBUX","STT",
    "STLD","STE","SYK","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT","TEL","TDY","TFX",
    "TER","TSLA","TXN","TXT","TMO","TJX","TSCO","TT","TDG","TRV","TRMB","TFC","TYL","TSN","USB","UBER",
    "UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK","VZ","VRTX","V",
    "VST","VFC","VTRS","VICI","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT","WEC","WFC",
    "WELL","WST","WDC","WY","WMB","WTW","WYNN","XEL","XYL","YUM","ZBRA","ZBH","ZTS","SMCI","CRWD","AXON"
]

FALLBACK_TICKERS = ["NVDA","GOOGL","GOOG","AAPL","MSFT","AMZN","AVGO","TSLA","META","BRK.B","LLY","JPM","WMT"]

# Memoria Cache globală extinsă pentru stocarea istorică
_cache = {
    "tickers": [],
    "updated_at": None,
    "status": "pending",
    "global_market_data": {}  # RAM Storage pentru prețurile istorice
}


def get_global_market_history(days_back: int = 75) -> Dict[str, List[dict]]:
    """
    Descarcă datele masive grupate zilnic (Grouped Daily) de la Polygon pentru ultimele X zile comerciale.
    Reduce sute de apeluri la doar numărul de zile din istoric.
    """
    historical_data = {}
    current_date = datetime.now()
    dates_to_fetch = []
    
    # Selectăm doar zilele lucrătoare (Luni-Vineri)
    while len(dates_to_fetch) < days_back:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:  
            dates_to_fetch.append(current_date.strftime("%Y-%m-%d"))
            
    dates_to_fetch.reverse()  # Ordonare cronologică (vechi -> nou)
    logger.info(f"Downloading historical bulk data for {len(dates_to_fetch)} trading days...")

    for date_str in dates_to_fetch:
        url = f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
        try:
            res = requests.get(url, params={"apiKey": POLYGON_API_KEY, "adjusted": "true"}, timeout=10)
            if res.status_code == 200:
                results = res.json().get("results", [])
                for bar in results:
                    ticker = bar.get("T")
                    if ticker:
                        if ticker not in historical_data:
                            historical_data[ticker] = []
                        historical_data[ticker].append({
                            "c": bar["c"],  # Close price
                            "v": bar["v"]   # Volume
                        })
            elif res.status_code == 429:
                logger.warning(f"Rate limit hit during history download on {date_str}. Waiting 60s...")
                time.sleep(60)
            time.sleep(0.15)  # Mică pauză anti-spike
        except Exception as e:
            logger.error(f"Error fetching historical date {date_str}: {e}")
            
    return historical_data


def _build_filtered_list():
    """
    Funcție executată în thread secundar la startup.
    Filtrează companiile mari (Cap > 30B) și pre-încarcă tot istoricul pieței în RAM.
    """
    logger.info("Starting startup data pre-load (History + Market Cap Filter)...")
    
    # 1. Pre-încărcăm istoricul global în RAM cache
    try:
        _cache["global_market_data"] = get_global_market_history(days_back=65)
        logger.info("Successfully loaded historical market data into RAM cache.")
    except Exception as e:
        logger.error(f"Failed to preload history cache: {e}")

    # 2. Rulam filtrul de Market Cap
    filtered = []
    min_cap = 30 * 1_000_000_000

    for ticker in SP500_ALL:
        try:
            url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
            res = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8)
            if res.status_code == 200:
                data = res.json().get("results", {})
                market_cap = data.get("market_cap", 0) or 0
                if market_cap >= min_cap:
                    filtered.append(ticker)
            elif res.status_code == 429:
                logger.warning(f"Rate limited at {ticker}, sleeping 60s...")
                time.sleep(60)
                res = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8)
                if res.status_code == 200:
                    data = res.json().get("results", {})
                    market_cap = data.get("market_cap", 0) or 0
                    if market_cap >= min_cap:
                        filtered.append(ticker)
            time.sleep(0.25)  # Pauză pentru a respecta limita planului free
        except Exception as e:
            logger.error(f"Error filtering {ticker}: {e}")
            time.sleep(0.25)

    if filtered:
        _cache["tickers"] = filtered
        _cache["updated_at"] = datetime.utcnow()
        _cache["status"] = "ready"
        logger.info(f"Filter finished. {len(filtered)} tickers are ready.")
    else:
        _cache["tickers"] = FALLBACK_TICKERS
        _cache["updated_at"] = datetime.utcnow()
        _cache["status"] = "fallback"
        logger.warning("Filter returned empty list. Fallback loaded.")


def start_background_filter():
    _cache["tickers"] = FALLBACK_TICKERS
    _cache["status"] = "pending"
    t = threading.Thread(target=_build_filtered_list, daemon=True)
    t.start()


def get_tickers_to_scan() -> List[str]:
    return _cache["tickers"] if _cache["tickers"] else FALLBACK_TICKERS


def get_filter_status() -> dict:
    return {
        "status": _cache["status"],
        "tickers_count": len(_cache["tickers"]),
        "updated_at": _cache["updated_at"].isoformat() if _cache["updated_at"] else None,
    }


def analyze_ticker_in_memory(ticker: str, bars: List[dict]) -> Optional[Dict]:
    """
    Algoritmul tău matematic aplicat instantaneu în memorie (Zero latență rețea).
    Calculează mediile mobile și cele 4 semnale tehnice / cantitative.
    """
    try:
        if not bars or len(bars) < 15:
            return None

        closes = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        current_price = closes[-1]

        # Calcul medii mobile simple (SMA) bazate pe datele din RAM
        ma20 = sum(closes[-20:]) / min(20, len(closes))
        ma50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else ma20

        # ── SEMNAL 1: Trend Strength ──
        trend_strength = False
        trend_note = ""
        if len(closes) >= 50:
            above_ma20 = current_price > ma20
            above_ma50 = current_price > ma50
            ma20_rising = ma20 > sum(closes[-30:-10]) / 20
            if above_ma20 and above_ma50 and ma20_rising:
                upside_ma20 = (current_price / ma20 - 1) * 100
                trend_strength = True
                trend_note = f"Deasupra MA20 (+{upside_ma20:.1f}%) și MA50, trend macro ascendent"

        # ── SEMNAL 2: Volume Anomaly ──
        volume_anomaly = False
        volume_note = ""
        if len(volumes) >= 20:
            avg_vol_20 = sum(volumes[-21:-1]) / 20
            avg_vol_5 = sum(volumes[-6:-1]) / 5
            if avg_vol_20 > 0:
                ratio = avg_vol_5 / avg_vol_20
                if ratio > 1.3:
                    volume_anomaly = True
                    volume_note = f"Volum nespecific pe termen scurt: 5z = {ratio:.1f}x față de medie 20z"

        # ── SEMNAL 3: Relative Strength ──
        relative_strength = False
        rs_note = ""
        if len(closes) >= 20:
            ret5  = (closes[-1] / closes[-6]  - 1) * 100 if len(closes) >= 6  else 0
            ret10 = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
            ret20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
            if ret5 > 1 and ret10 > 3 and ret20 > 5:
                relative_strength = True
                rs_note = f"Impuls: +{ret5:.1f}% (5z), +{ret10:.1f}% (10z), +{ret20:.1f}% (20z)"

        # ── SEMNAL 4: Institutional Accumulation (Smart Money Tracker) ──
        inst_accumulation = False
        inst_note = ""
        if len(volumes) >= 30:
            recent10 = sum(volumes[-10:]) / 10
            prev20   = sum(volumes[-30:-10]) / 20
            if prev20 > 0 and recent10 / prev20 > 1.2:
                if closes[-1] > closes[-10]:
                    inst_accumulation = True
                    inst_note = f"Acumulare Fonduri: Volum 10z = {recent10/prev20:.1f}x mai mare cu preț în creștere"

        signals = {
            "trend_strength":    trend_strength,
            "volume_anomaly":    volume_anomaly,
            "relative_strength": relative_strength,
            "inst_accumulation": inst_accumulation,
        }
        notes = {
            "trend_strength":    trend_note,
            "volume_anomaly":    volume_note,
            "relative_strength": rs_note,
            "inst_accumulation": inst_note,
        }

        score = sum(signals.values())
        chg1  = (closes[-1] / closes[-2]  - 1) * 100 if len(closes) >= 2  else 0
        chg5  = (closes[-1] / closes[-6]  - 1) * 100 if len(closes) >= 6  else 0
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
        logger.error(f"Error executing analysis for {ticker} in memory: {e}")
        return None


def scan_all(min_score: int = 3) -> List[Dict]:
    """
    Metoda principală apelată din main.py.
    A fost optimizată complet să ruleze în RAM fără interogări API la click.
    """
    tickers = get_tickers_to_scan()
    results = []
    
    # Citim datele istorice din memoria RAM persistentă
    global_market_data = _cache.get("global_market_data", {})
    
    # Siguranță: dacă dintr-un motiv anume cache-ul s-a golit, facem un fetch rapid
    if not global_market_data:
        logger.warning("RAM history cache empty. Triggering emergency download...")
        global_market_data = get_global_market_history(days_back=55)
        _cache["global_market_data"] = global_market_data

    total = len(tickers)
    logger.info(f"Starting lighting-fast scanning inside RAM for {total} tickers...")

    # Calcul instantaneu în buclă
    for ticker in tickers:
        bars = global_market_data.get(ticker)
        if not bars:
            continue
            
        result = analyze_ticker_in_memory(ticker, bars)
        if result and result["score"] >= min_score:
            results.append(result)

    # Sortare: Scorul cel mai mare, urmat de performanța pe ultimele 5 zile
    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
