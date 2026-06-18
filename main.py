from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from scanner import (
    start_background_filter, 
    start_daily_refresh, 
    get_filter_status, 
    scan_all, 
    get_tickers_to_scan
)
from datetime import datetime

app = FastAPI(title="S&P 500 Intelligence API")

# Middleware CORS pentru a permite accesul de pe Vercel/Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Pornim thread-ul de preload și scheduler-ul de refresh zilnic
    start_background_filter()
    start_daily_refresh()

@app.get("/")
def root():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# --- RUTE PUNTE (Rezolvă erorile 404 din Railway) ---
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

@app.get("/api/early-warning")
def early_warning(min_score: int = Query(3)):
    return {
        "signals": scan_all(min_score), 
        "filter_status": get_filter_status()["status"]
    }

@app.get("/api/early-warning/scan-now")
def scan_now(): 
    return {
        "status": "scan running", 
        "results": scan_all(2)
    }
