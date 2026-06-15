from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scanner import start_background_filter, start_daily_refresh, scan_all, get_filter_status

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== SERVER INITIALIZAT ===")
    start_background_filter()
    start_daily_refresh()
    yield
    print("=== SERVER INCHIS ===")

app = FastAPI(lifespan=lifespan)

# Permite comunicarea cu Vercel (Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
def status_endpoint():
    return get_filter_status()

@app.get("/scan")
def scan_endpoint(min_score: int = 2):
    return scan_all(min_score=min_score)

# Rute "Punte" pentru a nu mai avea erori 404 in frontend-ul vechi
@app.get("/api/market")
def market_bridge(): return {"status": "ok", "data": []}
@app.get("/api/sectors")
def sectors_bridge(): return []
@app.get("/api/macro")
def macro_bridge(): return {}
