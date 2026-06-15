from fastapi import FastAPI
from contextlib import asynccontextmanager
from scanner import start_background_filter, start_daily_refresh, scan_all, get_filter_status

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🚀 Acest cod se execută IMEDIAT DUPĂ ce serverul s-a legat de portul Railway
    print("=== SERVER INSTALAT CU SUCCES IN RETEA ===")
    print("Lansăm procesele de fundal pentru istoricul de 65 de zile...")
    start_background_filter()
    start_daily_refresh()
    yield
    print("Serverul se închide...")

# Inițializăm FastAPI cu managerul de viață (lifespan)
app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    """Ruta principală care răspunde instant la ping-ul Railway."""
    return {
        "status": "online",
        "message": "Early Warning Scanner API functionează corect.",
        "endpoints": {
            "scan": "/scan?min_score=2",
            "status": "/status"
        }
    }

@app.get("/status")
def status_endpoint():
    """Verifică starea curentă a cache-ului din RAM."""
    return get_filter_status()

@app.get("/scan")
def scan_endpoint(min_score: int = 2):
    """Rulează algoritmul peste datele preîncărcate în RAM."""
    return scan_all(min_score=min_score)
