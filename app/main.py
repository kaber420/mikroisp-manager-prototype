# app/main.py

import os
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth import (
    User, get_current_active_user, verify_password,
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, Token
)
# --- IMPORTACIONES DE API ACTUALIZADAS ---
from .db import users_db
from .api import users_api, clients_api, cpes_api, zonas_api, settings_api, aps_api, stats_api
# ¡Importamos el nuevo módulo principal de routers!
from .api.routers import main as routers_main_api

app = FastAPI(title="µMonitor Pro", version="0.4.0")

origins = ["*"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, '..', 'static')
templates_dir = os.path.join(current_dir, '..', 'templates')

os.makedirs("uploads", exist_ok=True) 
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)
ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"

async def get_current_user_or_redirect(user: User = Depends(get_current_active_user)) -> User:
    return user

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401 and not request.url.path.startswith('/api/'):
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/login", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token", tags=["Auth & Pages"], include_in_schema=False)
async def login_for_web_ui(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        request_data = {"request": {}, "error_message": "Incorrect username or password"}
        return templates.TemplateResponse("login.html", request_data, status_code=status.HTTP_401_UNAUTHORIZED)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key=ACCESS_TOKEN_COOKIE_NAME, value=access_token, httponly=True, max_age=int(access_token_expires.total_seconds()), samesite="Lax")
    return response

@app.get("/logout", tags=["Auth & Pages"], include_in_schema=False)
async def logout_and_redirect():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return response

# --- Endpoints para servir las páginas HTML ---
@app.get("/", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_dashboard(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "dashboard"})

@app.get("/aps", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_aps_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("aps.html", {"request": request, "active_page": "aps"})

@app.get("/ap/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_ap_details_page(request: Request, host: str, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("ap_details.html", {"request": request, "active_page": "ap_details", "host": host})

@app.get("/zonas", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zones_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("zonas.html", {"request": request, "active_page": "zonas"})

@app.get("/zona/{zona_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zona_details_page(request: Request, zona_id: int, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("zona_details.html", {"request": request, "active_page": "zonas", "zona_id": zona_id})

@app.get("/settings", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_settings_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("settings.html", {"request": request, "active_page": "settings"})

@app.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("users.html", {"request": request, "active_page": "users"})

@app.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("cpes.html", {"request": request, "active_page": "cpes"})

@app.get("/clients", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_clients_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("clients.html", {"request": request, "active_page": "clients"})

@app.get("/client/{client_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_client_details_page(request: Request, client_id: int, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("client_details.html", {"request": request, "active_page": "clients", "client_id": client_id})

@app.get("/routers", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_routers_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("routers.html", {"request": request, "active_page": "routers"})

@app.get("/router/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_router_details_page(request: Request, host: str, current_user: User = Depends(get_current_user_or_redirect)):
    return templates.TemplateResponse("router_details.html", {"request": request, "active_page": "router_details", "host": host})

@app.post("/api/login/access-token", response_model=Token, tags=["API Auth"])
async def login_for_api_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# --- Inclusión de todos los routers de la API ---
app.include_router(routers_main_api.router, prefix="/api", tags=["Routers"]) # <-- ¡LÍNEA CAMBIADA!
app.include_router(aps_api.router, prefix="/api", tags=["APs"])
app.include_router(cpes_api.router, prefix="/api", tags=["CPEs"])
app.include_router(clients_api.router, prefix="/api", tags=["Clients"])
app.include_router(zonas_api.router, prefix="/api", tags=["Zonas"])
app.include_router(users_api.router, prefix="/api", tags=["Users"])
app.include_router(settings_api.router, prefix="/api", tags=["Settings"])
app.include_router(stats_api.router, prefix="/api", tags=["Stats"])