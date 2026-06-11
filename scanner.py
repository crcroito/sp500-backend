import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLYGON_API_KEY = "mNiA3ZcUdRe5C5Uwo3PaGOH3lwmPzYy9"
BASE_URL = "https://api.polygon.io"

# Lista completa S&P 500
SP500_ALL_TICKERS = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB","AKAM","ALB","ARE","ALGN",
    "ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN","AMCR","AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP",
    "AME","AMGN","APH","ADI","ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG","AIZ","T",
    "ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC","BBWI","BAX","BDX","BRK.B","BBY","BIO",
    "TECH","BIIB","BLK","BX","BA","BCX","BSX","BMY","AVGO","BR","BRO","BF.B","BLDR","BG","CDNS","CZR",
    "CPT","CPB","COF","CAH","KMX","CCL","CARR","CTLT","CAT","CBOE","CBRE","CDW","CE","COR","CNC","CNX",
    "CDAY","CF","CRL","SCHW","CHTR","CVX","CMG","CB","CHD","CI","CINF","CTAS","CSCO","C","CFG","CLX",
    "CME","CMS","KO","CTSH","CL","CMCSA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CPAY","CTVA",
    "CSGP","COST","CTRA","CCI","CSX","CMI","CVS","DHR","DRI","DVA","DAY","DECK","DE","DELL","DAL","DVN",
    "DXCM","FANG","DLR","DFS","DG","DLTR","D","DPZ","DOV","DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY",
    "ECL","EIX","EW","EA","ELV","LLY","EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR","ESS",
    "EL","ETSY","EG","EVRG","ES","EXC","EXPE","EXPD","EXR","XOM","FFIV","FDS","FICO","FAST","FRT","FDX",
    "FIS","FITB","FSLR","FE","FI","FMC","F","FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT","GE","GEHC",
    "GEV","GEN","GNRC","GD","GIS","GM","GPC","GILD","GS","HAL","HIG","HAS","HCA","DOC","HSIC","HSY","HES",
    "HPE","HLT","HOLX","HD","HON","HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX","IDXX",
    "ITW","INCY","IR","PODD","INTC","ICE","IFF","IP","IPG","INTU","ISRG","IVZ","INVH","IQV","IRM","JBHT",
    "JBL","JKHY","J","JNJ","JCI","JPM","JNPR","K","KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KLAC",
    "KHC","KR","LHX","LH","LRCX","LW","LVS","LDOS","LEN","LNC","LIN","LYV","LKQ","LMT","L","LOW","LULU",
    "LYB","MTB","MRO","MPC","MKTX","MAR","MMC","MLM","MAS","MA","MTCH","MKC","MCD","MCK","MDT","MRK",
    "META","MET","MTD","MGM","MCHP","MU","MSFT","MAA","MRNA","MHK","MOH","TAP","MDLZ","MPWR","MNST","MCO",
    "MS","MOS","MSI","MSCI","NDAQ","NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC","NTRS",
    "NOC","NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY","OXY","ODFL","OMC","ON","OKE","ORCL","OTIS","PCAR",
    "PKG","PANW","PARA","PH","PAYX","PAYC","PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC","POOL",
    "PPG","PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","QRVO","PWR","QCOM","DGX","RL","RJF",
    "RTX","O","REG","REGN","RF","RSG","RMD","RVTY","ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SBAC",
    "SLB","STX","SRE","NOW","SHW","SPG","SWKS","SJM","SW","SNA","SOLV","SO","LUV","SWK","SBUX","STT",
    "STLD","STE","SYK","SMCI","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT","TEL","TDY",
    "TFX","TER","TSLA","TXN","TXT","TMO","TJX","TSCO","TT","TDG","TRV","TRMB","TFC","TYL","TSN","USB",
    "UBER","UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK","VZ","VRTX",
    "VIAV","V","VST","VFC","VTRS","VICI","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT","WEC",
    "WFC","WELL","WST","WDC","WY","WMB","WTW","WYNN","XEL","XYL","YUM","ZBRA","ZBH","ZTS"
]

def get_market_cap_filtered_tickers(min_cap_billions: float = 30.0) -> List[str]:
    """Filtrează tickerele după market cap > min_cap_billions miliarde."""
    filtered = []
    min_cap = min_cap_billions * 1_000_000_000
    
    logger.info(f"Pre-filtering {len(SP500_ALL_TICKERS)} tickers by market cap > ${min_cap_billions}B...")
    
    for i, ticker in enumerate(SP500_ALL_TICKERS):
        try:
            url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
            res = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=8)
            if res.status_code == 200:
                data = res.json().get("results", {})
                market_cap = data.get("market_cap", 0) or 0
                if market_cap >= min_cap:
                    filtered.append(ticker)
            time.sleep(0.12)
        except Exception as e:
            logger.error(f"Market cap error {ticker}: {e}")
    
    logger.info(f"Pre-filtering done: {len(filtered)} tickers pass market cap filter")
    return filtered


# Cache pentru lista filtrată (se actualizează o dată pe zi)
_filtered_tickers_cache = {
    "tickers": [],
    "updated_at": None
}

def get_tickers_to_scan() -> List[str]:
    """Returnează lista de tickere filtrate, cu cache de 24h."""
    cached = _filtered_tickers_cache
    now = datetime.utcnow()
    
    if cached["tickers"] and cached["updated_at"]:
        age_hours = (now - cached["updated_at"]).seconds / 3600
        if age_hours < 24:
            return cached["tickers"]
    
    tickers = get_market_cap_filtered_tickers(min_cap_billions=30.0)
    
    # Fallback dacă filtrul eșuează
    if not tickers:
        logger.warning("Market cap filter returned no results, using fallback list")
        tickers = SP500_ALL_TICKERS
    
    _filtered_tickers_cache["tickers"] = tickers
    _filtered_tickers_cache["updated_at"] = now
    return tickers


def get_bars(ticker: str, days: int = 120) -> Optional[List]:
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        res = requests.get(url, params={
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

        closes = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]

        current_price = closes[-1]

        # Moving averages
        ma20 = sum(closes[-20:]) / min(20, len(closes))
        ma50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else ma20

        # ── SEMN 1: Trend Strength (preț peste MA20 + MA50, trend în creștere) ──
        trend_strength = False
        trend_note = ""
        if len(closes) >= 50:
            above_ma20 = current_price > ma20
            above_ma50 = current_price > ma50
            ma20_rising = ma20 > sum(closes[-30:-10]) / 20
            if above_ma20 and above_ma50 and ma20_rising:
                upside_ma20 = (current_price / ma20 - 1) * 100
                trend_strength = True
                trend_note = f"Deasupra MA20 (+{upside_ma20:.1f}%) și MA50, trend up"

        # ── SEMN 2: Volume Anomaly (volum mare față de medie) ──
        volume_anomaly = False
        volume_note = ""
        if len(volumes) >= 20:
            avg_vol_20 = sum(volumes[-21:-1]) / 20
            avg_vol_5 = sum(volumes[-6:-1]) / 5
            if avg_vol_20 > 0:
                ratio = avg_vol_5 / avg_vol_20
                if ratio > 1.3:
                    volume_anomaly = True
                    volume_note = f"Volum mediu 5z = {ratio:.1f}x față de medie 20z"

        # ── SEMN 3: Relative Strength (performanță pozitivă pe 3 timeframes) ──
        relative_strength = False
        rs_note = ""
        if len(closes) >= 20:
            ret5 = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
            ret10 = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
            ret20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0
            if ret5 > 1 and ret10 > 3 and ret20 > 5:
                relative_strength = True
                rs_note = f"+{ret5:.1f}% (5z), +{ret10:.1f}% (10z), +{ret20:.1f}% (20z)"

        # ── SEMN 4: Institutional Accumulation (volum crescut consistent + preț up) ──
        inst_accumulation = False
        inst_note = ""
        if len(volumes) >= 30:
            recent10 = sum(volumes[-10:]) / 10
            prev20 = sum(volumes[-30:-10]) / 20
            if prev20 > 0 and recent10 / prev20 > 1.2:
                price_up = closes[-1] > closes[-10]
                if price_up:
                    inst_accumulation = True
                    inst_note = f"Volum 10z = {recent10/prev20:.1f}x față de anterior, preț în creștere"

        signals = {
            "trend_strength": trend_strength,
            "volume_anomaly": volume_anomaly,
            "relative_strength": relative_strength,
            "inst_accumulation": inst_accumulation,
        }

        notes = {
            "trend_strength": trend_note,
            "volume_anomaly": volume_note,
            "relative_strength": rs_note,
            "inst_accumulation": inst_note,
        }

        score = sum(signals.values())

        chg1 = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0
        chg5 = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
        chg20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 21 else 0

        return {
            "ticker": ticker,
            "name": ticker,
            "sector": "S&P 500",
            "price": round(current_price, 2),
            "change_1d": round(chg1, 2),
            "change_5d": round(chg5, 2),
            "change_20d": round(chg20, 2),
            "pe": None,
            "score": score,
            "signals": signals,
            "notes": notes,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None


def scan_all(min_score: int = 3) -> List[Dict]:
    tickers = get_tickers_to_scan()
    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        logger.info(f"Scanning {ticker} ({i+1}/{total})")
        result = analyze_ticker(ticker)
        if result and result["score"] >= min_score:
            results.append(result)
        time.sleep(0.15)

    results.sort(key=lambda x: (x["score"], x["change_5d"]), reverse=True)
    return results
