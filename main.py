from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
# Importăm funcțiile necesare din scanner
from scanner import (
    start_background_filter, 
    start_daily_refresh, 
    get_filter_status, 
    scan_all, 
    get_tickers_to_scan
)

app = FastAPI(title="S&P 500 Intelligence API")

# Middleware CORS pentru a permite accesul de pe frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Pornim thread-ul de preload date și scheduler-ul de refresh zilnic
    start_background_filter()
    start_daily_refresh()

@app.get("/")
def root():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# --- RUTE PUNTE (Rezolvă erorile 404 din logurile Railway) ---
@app.get("/api/market")
def market(): 
    return {"status": "ready" if get_filter_status()["status"] == "ready" else "loading"}

@app.get("/api/sectors")
def sectors(): 
    return []

@app.get("/api/macro")
def macro(): 
    return {"fed_rate": "5.25-5.50%", "status": "active"}

@app.get("/status")
def status(): 
    return get_filter_status()

# --- RUTE PRINCIPALE ---
@app.get("/api/filter-status")
def filter_status(): 
    return get_filter_status()

# Ruta veche /scan pentru compatibilitate cu frontend-ul
@app.get("/scan")
def scan_redirect(min_score: int = Query(3)):
    return scan_all(min_score)

# Ruta Early Warning: Returnează scanarea direct
@app.get("/api/early-warning")
def early_warning(min_score: int = Query(3)):
    results = scan_all(min_score)
    return {
        "signals": results,
        "count": len(results),
        "filter_status": get_filter_status()["status"],
        "scanned_at": datetime.utcnow().isoformat()
    }

# Ruta Scan Now
@app.get("/api/early-warning/scan-now")
def scan_now(): 
    results = scan_all(2)
    return {
        "status": "scan complete", 
        "count": len(results),
        "results": results
    }
