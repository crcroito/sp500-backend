import httpx
import asyncio

# ... restul listei SP500_ALL și _cache rămân identice ...

async def get_global_market_history(days_back: int = 65) -> Dict[str, List[dict]]:
    historical_data = {}
    current_date = datetime.now()
    dates_to_fetch = []
    
    while len(dates_to_fetch) < days_back:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            dates_to_fetch.append(current_date.strftime("%Y-%m-%d"))
            
    dates_to_fetch.reverse()
    logger.info(f"Downloading historical bulk data for {len(dates_to_fetch)} trading days...")

    # Folosim httpx pentru cereri asincrone care nu blochează serverul
    async with httpx.AsyncClient() as client:
        for date_str in dates_to_fetch:
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
                    
                    logger.info(f"Fetched data for {date_str}. Waiting for API limits (non-blocking)...")
                    # CORECTARE CRITICĂ: Eliberează complet procesorul pentru ca FastAPI să poată răspunde la Health Check
                    await asyncio.sleep(12)
                    
                elif res.status_code == 429:
                    logger.warning("Rate limit hit in bulk load. Waiting 60 seconds...")
                    await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error fetching bulk historical date {date_str}: {e}")
                await asyncio.sleep(1)
                
    return historical_data

# Deoarece funcția de mai sus a devenit async, trebuie să adaptăm și funcția care o apelează:
def _build_filtered_list():
    logger.info("Starting background preload data process...")
    
    try:
        # Rulăm funcția async în interiorul thread-ului de background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _cache["global_market_data"] = loop.run_until_complete(get_global_market_history(days_back=65))
        logger.info("Successfully loaded historical market data into RAM cache.")
    except Exception as e:
        logger.error(f"Failed to preload history cache: {e}")

    # Păstrează restul codului din _build_filtered_list neschimbat (filtrarea pe market cap)
    # ...
