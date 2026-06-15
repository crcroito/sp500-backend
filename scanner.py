import httpx
import asyncio
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"

# Lista oficiala completa S&P 500
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

SP500_SET = set(SP500_ALL)

_cache = {
    "tickers": SP500_ALL,
    "updated_at": None,
    "status": "pending",
    "global_market_data": {}
}

async def get_global_market_history(days_back: int = 20) -> Dict[str, List[dict]]:
    historical_data = {}
    current_date = datetime.now()
    dates_to_fetch = []
    
    # Generăm exact 20 de zile pentru testul rapid
    while len(dates_to_fetch) < days_back:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            dates_to_fetch.append(current_date.strftime("%Y-%m-%d"))
            
    dates_to_fetch.reverse()
    logger.info(f"Downloading historical bulk data for {len(dates_to_fetch)} trading days...")

    async with httpx.AsyncClient() as client:
        idx = 0
        while idx < len(dates_to_fetch):
            date_str = dates_to_fetch[idx]
            url = f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
            try:
                res = await client.get(url, params={"apiKey": POLYGON_API_KEY, "adjusted": "true"}, timeout=15.0)
                
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    for bar in results:
                        ticker = bar.get("T")
                        if ticker in SP500_SET:
                            if ticker not in historical_data:
                                historical_data[ticker] = []
                            historical_data[ticker].append({
                                "c": bar["c"],
                                "v": bar["v"]
                            })
                    
                    logger.info(f"[{idx+1}/{len(dates_to_fetch)}] Succes pentru data {date_str}. Așteptăm 17s...")
                    await asyncio.sleep(17)
                    idx += 1
                    
                elif res.status_code == 429:
                    logger.warning(f"Rate limit (429) atins pentru {date_str}. Reîncercăm peste 65 de secunde...")
                    await asyncio.sleep(65)
                    
                else:
                    logger.error(f"Eroare API {res.status_code} pentru {date_str}. Sărim peste zi.")
                    idx += 1
                    
            except Exception as e:
                logger.error(f"Eroare conexiune pentru data {date_str}: {e}. Reîncercăm în 5 secunde...")
                await asyncio.sleep(5)
                
    return historical_data

def _build_filtered_list():
    logger.info("Starting background preload data process...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _cache["global_market_data"] = loop.run_until_complete(get_global_market_history(days_back=20))
        logger.info("Successfully loaded historical market data into RAM cache.")
    except Exception as e:
        logger.error(f"Failed to preload history cache: {e}")

    filtered = []
    min_cap = 30 * 1_000_000_000
    
    for ticker in SP500_ALL:
        try:
            url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
            res = httpx.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8.0)
            if res.status_code == 200:
                data = res.json().get("results", {})
                market_cap = data.get("market_cap", 0) or 0
                if market_cap >= min_cap:
                    filtered.append(ticker)
            elif res.status_code == 429:
                logger.warning(f"Rate limit la market cap pentru {ticker}. Backoff 60s...")
                time.sleep(60)
                res = httpx.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8.0)
                if res.status_code == 200:
                    data = res.json().get("results", {})
                    if (data.get("market_cap", 0) or 0) >= min_cap:
                        filtered.append(ticker)
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Error filtering {ticker}: {e}")
            time.sleep(0.2)

    if filtered:
        _cache["tickers"] = filtered
        _cache["status"] = "ready"
    else:
        _cache["tickers"] = SP500_ALL
        _cache["status"] = "fallback"
        
    _cache["updated_at"] = datetime.utcnow()
    logger.info(f"Filter process finished. Active tickers: {len(_cache['tickers'])}")

def start_background_filter():
    _cache["tickers"] = SP500_ALL
    _cache["status"] = "pending"
    t = threading.Thread(target=_build_filtered_list, daemon=True)
    t.start()

def _daily_refresh():
    logger.info("Starting daily data refresh...")
    _build_filtered_list()
    logger.info("Daily refresh complete.")

def _schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_daily_refresh():
    schedule.every().day.at("22:00").do(_daily_refresh)
    t = threading.Thread(target=_schedule_runner, daemon=True)
    t.start()
    logger.info("Daily refresh scheduled at 22:00 UTC")

def get_tickers_to_scan() -> List[str]:
    return _cache["tickers"] if _cache["tickers"] else SP500_ALL

def get_filter_status() -> dict:
    return {
        "status": _cache["status"],
        "tickers_count": len(_cache["tickers"]),
        "updated_at": _cache["updated_at"].isoformat() if _cache["updated_at"] else None,
    }

def analyze_ticker_in_memory(ticker: str, bars: List[dict]) -> Optional[Dict]:
    try:
        # Reducem la 10 lungimea minima pentru a genera date pe cele 20 de zile descarcate
        if not bars or len(bars) < 10:
            return None

        closes = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        current_price = closes[-1]

        # Adaptare ferestre medii mobile pentru istoricul scurt de test
        ma20 = sum(closes[-20:]) / min(20, len(closes))
        ma_short = sum(closes[-10:]) / min(10, len(closes))

        trend_strength = False
        trend_note = ""
        if len(closes) >= 10:
            above_ma20 = current_price > ma20
            ma20_rising = ma_short > ma20
            if above_ma20 and ma20_rising:
                upside_ma20 = (current_price / ma20 - 1) * 100
                trend_strength = True
                trend_note = f"Deasupra MA20 (+{upside_ma20:.1f}%), impuls ascendent pe termen scurt"

        volume_anomaly = False
        volume_note = ""
        if len(volumes) >= 10:
            avg_vol_20 = sum(volumes) / len(volumes)
            avg_vol_3 = sum(volumes[-3:]) / 3
            if avg_vol_20 > 0:
                ratio = avg_vol_3 / avg_vol_20
                if ratio > 1.2:
                    volume_anomaly = True
                    volume_note = f"Volum ridicat: ultimele 3z = {ratio:.1f}x față de media perioadei"

        relative_strength = False
        rs_note = ""
        if len(closes) >= 10:
            ret3  = (closes[-1] / closes[-4]  - 1) * 100 if len(closes) >= 4  else 0
            ret10 = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
            if ret3 > 1 or ret10 > 2:
                relative_strength = True
                rs_note = f"Impuls preț: +{ret3:.1f}% (3z), +{ret10:.1f}% (10z)"

        institutional_accumulation = False
        inst_note = ""
        if len(volumes) >= 10:
            recent5 = sum(volumes[-5:]) / 5
            prev10   = sum(volumes[:10]) / 10
            if prev10 > 0 and recent5 / prev10 > 1.1:
                if closes[-1] > closes[-5]:
                    institutional_accumulation = True
                    inst_note = f"Presiune de cumpărare: Volum în creștere pe ultimele 5 zile"

        signals = {
            "trend_strength": trend_strength, 
            "volume_anomaly": volume_anomaly, 
            "relative_strength": relative_strength, 
            "institutional_accumulation": institutional_accumulation
        }
        notes = {
            "trend_strength": trend_note, 
            "volume_anomaly": volume_note, 
            "relative_strength": rs_note, 
            "institutional_accumulation": inst_note
        }

        score = sum(signals.values())
        chg1  = (closes[-1] / closes[-2]  - 1) * 100 if len(closes) >= 2  else 0
        chg5  = (closes[-1] / closes[-6]  - 1) * 100 if len(closes) >= 6  else 0

        return {
            "ticker": ticker, "name": ticker, "sector": "S&P 500", "price": round(current_price, 2),
            "change_1d": round(chg1, 2), "change_5d": round(chg5, 2), "change_20d": round(chg1, 2),
            "pe": None, "score": score, "signals": signals, "notes": notes, "scanned_at": datetime.utcnow().isoformat(),
        }
    except:
        return None

def scan_all(min_score: int = 3) -> List[Dict]:
    tickers = get_tickers_to_scan()
    results = []
    global_market_data = _cache.get("global_market_data", {})
    
    if not global_market_data:
        logger.warning("RAM Cache global empty. Executing emergency historic bulk load...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            global_market_data = loop.run_until_complete(get_global_market_history(days_back=20))
            _cache["global_market_data"] = global_market_data
        except Exception as e:
            logger.error(f"Emergency bulk load failed: {e}")

    for ticker in tickers:
        bars = global_market_data.get(ticker)
        if not bars:
            continue
        result = analyze_ticker_in_memory(ticker, bars)
        if result and result["score"] >= min_score:
            results.append(result)

    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
