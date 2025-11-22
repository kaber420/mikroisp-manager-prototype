# app/main.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env ANTES de cualquier otra cosa
load_dotenv()

import asyncio
from fastapi import FastAPI, HTTPException, status, Depends, Request, WebSocket, WebSocketDisconnect, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List

# SlowAPI (Rate Limiting)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .auth import (
    User, get_current_active_user, verify_password,
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, Token
)
# Importaciones de API
from .db import users_db
from .api.routers import main as routers_main_api
from .api.clients import main as clients_main_api
from .api.cpes import main as cpes_main_api
from .api.zonas import main as zonas_main_api
from .api.users import main as users_main_api
from .api.settings import main as settings_main_api
from .api.aps import main as aps_main_api
from .api.stats import main as stats_main_api
from .api.plans import main as plans_main_api


app = FastAPI(title="µMonitor Pro", version="0.5.0")

# --- Configuración de SlowAPI ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if request.url.path == "/token":
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error_message": "⚠️ Demasiados intentos fallidos. Por favor, espera 1 minuto."
            }, 
            status_code=429
        )
    return JSONResponse(
        content={"error": f"Rate limit exceeded: {exc.detail}"}, 
        status_code=429
    )

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

APP_ENV = os.getenv("APP_ENV", "development")

# ============================================================================
# --- SEGURIDAD: CONFIGURACIÓN CORS ESTRICTA ---
# ============================================================================
# Leemos los orígenes permitidos desde el archivo .env
# Si no está definido, por defecto solo permitimos localhost para desarrollo.
# Formato en .env: ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
origins = allowed_origins_env.split(",")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,       # <--- Aquí está la clave: Solo IPs de la lista
    allow_credentials=True,      # Necesario para que funcionen las cookies y WebSockets
    allow_methods=["*"],         # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],         # Permitir todos los headers
)

# ============================================================================
# --- SEGURIDAD: TRUSTED HOSTS (Evitar ataques de Host Header) ---
# ============================================================================
# Un atacante podría falsificar el encabezado Host en una petición HTTP para
# engañar a tu aplicación y hacer que genere enlaces de restablecimiento de
# contraseña apuntando a un dominio malicioso.
# Este middleware valida el header "Host" para bloquear hosts no autorizados.

# Leer hosts permitidos desde .env
# Formato: ALLOWED_HOSTS="localhost,127.0.0.1,192.168.1.50,miwisp.com"
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# ============================================================================
# --- SEGURIDAD: CABECERAS DE SEGURIDAD HTTP (Security Headers) ---
# ============================================================================
# Los navegadores son muy permisivos por defecto. Enviamos cabeceras especiales
# que le indican al navegador que sea más estricto para evitar ataques como
# Clickjacking (poner tu web en un iframe invisible) o MIME sniffing.

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # 1. Evita que tu web sea puesta en un iframe (Clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    # 2. Evita que el navegador "adivine" tipos de archivo (MIME Sniffing)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # 3. Activa el filtro XSS del navegador (capa extra)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # 4. Política de Referrer estricta (Privacidad)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- Configuración de Directorios ---
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, '..', 'static')
templates_dir = os.path.join(current_dir, '..', 'templates')

os.makedirs("uploads", exist_ok=True) 
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"

# ============================================================================
# --- GESTOR DE WEBSOCKETS (REFACTORIZADO & GENÉRICO) ---
# ============================================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: dict = None):
        """
        Envía una señal JSON genérica a todos los clientes conectados.
        """
        payload = {"type": event_type}
        if data:
            payload.update(data)
            
        # Iteramos sobre una copia [:] para evitar errores si la lista cambia durante el envío
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# --- Funciones de Utilidad y Auth ---

async def get_current_user_or_redirect(user: User = Depends(get_current_active_user)) -> User:
    return user

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401 and not request.url.path.startswith('/api/'):
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ============================================================================
# --- ENDPOINTS WEBSOCKET Y NOTIFICACIÓN INTERNA ---
# ============================================================================

@app.websocket("/ws/dashboard") # <--- Asegúrate que esta ruta coincida con tu JS
async def websocket_dashboard(
    websocket: WebSocket,
    umonitorpro_access_token: str = Cookie(None)
):
    # --- DEBUG: Imprimir qué está pasando ---
    if umonitorpro_access_token is None:
        print(f"⚠️ [WebSocket] Rechazado: No se encontró la cookie 'umonitorpro_access_token'.")
        # Por ahora, cerramos con Policy Violation
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    print(f"✅ [WebSocket] Cookie encontrada. Aceptando conexión...")
    # ----------------------------------------

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/internal/notify-monitor-update", include_in_schema=False)
async def notify_monitor_update():
    """
    Endpoint interno llamado por monitor.py cuando termina un ciclo de escaneo.
    Envía la señal 'db_updated' a todos los clientes conectados.
    """
    await manager.broadcast_event("db_updated")
    return {"status": "broadcast_sent"}


# ============================================================================
# --- ENDPOINTS DE PÁGINAS (HTML) ---
# ============================================================================

@app.get("/login", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token", tags=["Auth & Pages"], include_in_schema=False)
@limiter.limit("5/minute")
async def login_for_web_ui(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = users_db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        request_data = {"request": {}, "error_message": "Incorrect username or password"}
        return templates.TemplateResponse("login.html", request_data, status_code=status.HTTP_401_UNAUTHORIZED)
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    is_secure_cookie = (APP_ENV == "production")
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME, 
        value=access_token, 
        httponly=True, 
        max_age=int(access_token_expires.total_seconds()), 
        samesite="Lax",
        secure=is_secure_cookie
    )
    return response

@app.get("/logout", tags=["Auth & Pages"], include_in_schema=False)
async def logout_and_redirect():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return response

@app.get("/", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_dashboard(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "dashboard", "user": current_user})

@app.get("/aps", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_aps_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("aps.html", {"request": request, "active_page": "aps", "user": current_user})

@app.get("/ap/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_ap_details_page(request: Request, host: str, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("ap_details.html", {"request": request, "active_page": "ap_details", "host": host, "user": current_user})

@app.get("/zonas", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zones_page(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("zonas.html", {"request": request, "active_page": "zonas", "user": current_user})

@app.get("/zona/{zona_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zona_details_page(request: Request, zona_id: int, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("zona_details.html", {"request": request, "active_page": "zonas", "zona_id": zona_id, "user": current_user})

@app.get("/settings", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_settings_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("settings.html", {"request": request, "active_page": "settings", "user": current_user})

@app.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("users.html", {"request": request, "active_page": "users", "user": current_user})

@app.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("cpes.html", {"request": request, "active_page": "cpes", "user": current_user})

@app.get("/clients", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_clients_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("clients.html", {"request": request, "active_page": "clients", "user": current_user})

@app.get("/client/{client_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_client_details_page(request: Request, client_id: int, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("client_details.html", {"request": request, "active_page": "clients", "client_id": client_id, "user": current_user})

@app.get("/routers", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_routers_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("routers.html", {"request": request, "active_page": "routers", "user": current_user})

@app.get("/router/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_router_details_page(request: Request, host: str, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("router_details.html", {"request": request, "active_page": "router_details", "host": host, "user": current_user})

# --- API Token Auth ---
@app.post("/api/login/access-token", response_model=Token, tags=["API Auth"])
@limiter.limit("5/minute")
async def login_for_api_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = users_db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# --- Inclusión de Routers API ---
app.include_router(routers_main_api.router, prefix="/api", tags=["Routers"])
app.include_router(aps_main_api.router, prefix="/api", tags=["APs"])
app.include_router(cpes_main_api.router, prefix="/api", tags=["CPEs"])
app.include_router(clients_main_api.router, prefix="/api", tags=["Clients"])
app.include_router(zonas_main_api.router, prefix="/api", tags=["Zonas"])
app.include_router(users_main_api.router, prefix="/api", tags=["Users"])
app.include_router(settings_main_api.router, prefix="/api", tags=["Settings"])
app.include_router(stats_main_api.router, prefix="/api", tags=["Stats"])
app.include_router(plans_main_api.router, prefix="/api", tags=["Plans"])