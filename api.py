# api.py

import sqlite3
import os
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict
from datetime import datetime, timedelta

# --- IMPORTACIONES DE DATABASE MODIFICADAS ---
from database import (
    _get_current_stats_db_file, INVENTORY_DB_FILE, get_all_settings, 
    update_settings, get_setting, get_all_users, create_user_in_db, 
    update_user_in_db, delete_user_from_db
)
from ap_client import UbiquitiClient
# --- IMPORTACIONES DE AUTENTICACIÓN MODIFICADAS ---
from auth import (
    User, get_current_active_user, get_user, verify_password, 
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
)


# --- Modelos de Datos (Pydantic) ---
class Zona(BaseModel):
    id: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)
class ZonaCreate(BaseModel):
    nombre: str
class ZonaUpdate(BaseModel):
    nombre: str

class UserResponse(BaseModel):
    username: str
    role: str
    telegram_chat_id: Optional[str] = None
    receive_alerts: bool
    receive_announcements: bool
    disabled: bool
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = 'admin'

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    receive_alerts: Optional[bool] = None
    receive_announcements: Optional[bool] = None
    disabled: Optional[bool] = None

class APUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    is_enabled: Optional[bool] = None
    monitor_interval: Optional[int] = None

class AP(BaseModel):
    host: str
    username: str
    zona_id: Optional[int] = None
    is_enabled: bool
    monitor_interval: Optional[int] = None
    hostname: Optional[str] = None
    model: Optional[str] = None
    mac: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None
    client_count: Optional[int] = None
    airtime_total_usage: Optional[int] = None
    airtime_tx_usage: Optional[int] = None
    airtime_rx_usage: Optional[int] = None
    total_throughput_tx: Optional[int] = None
    total_throughput_rx: Optional[int] = None
    noise_floor: Optional[int] = None
    chanbw: Optional[int] = None
    frequency: Optional[int] = None
    essid: Optional[str] = None
    total_tx_bytes: Optional[int] = None
    total_rx_bytes: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_sats: Optional[int] = None
    zona_nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class APCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: int
    is_enabled: bool = True
    monitor_interval: Optional[int] = None

class CPEDetail(BaseModel):
    cpe_mac: str
    cpe_hostname: Optional[str] = None
    ip_address: Optional[str] = None
    signal: Optional[int] = None
    signal_chain0: Optional[int] = None
    signal_chain1: Optional[int] = None
    noisefloor: Optional[int] = None
    dl_capacity: Optional[int] = None
    ul_capacity: Optional[int] = None
    throughput_rx_kbps: Optional[int] = None
    throughput_tx_kbps: Optional[int] = None
    total_rx_bytes: Optional[int] = None
    total_tx_bytes: Optional[int] = None
    cpe_uptime: Optional[int] = None
    eth_plugged: Optional[bool] = None
    eth_speed: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# --- NUEVO MODELO PARA LA VISTA GLOBAL DE CPES ---
class CPEGlobalInfo(CPEDetail):
    ap_host: Optional[str] = None
    ap_hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class APLiveDetail(AP):
    clients: List[CPEDetail]

class HistoryDataPoint(BaseModel):
    timestamp: datetime
    client_count: Optional[int] = None
    airtime_total_usage: Optional[int] = None
    total_throughput_tx: Optional[int] = None
    total_throughput_rx: Optional[int] = None

class APHistoryResponse(BaseModel):
    host: str
    hostname: Optional[str]
    history: List[HistoryDataPoint]

class TopAP(BaseModel):
    hostname: Optional[str]
    host: str
    airtime_total_usage: Optional[int]
    model_config = ConfigDict(from_attributes=True)

class TopCPE(BaseModel):
    cpe_hostname: Optional[str]
    cpe_mac: str
    ap_host: str
    signal: Optional[int]
    model_config = ConfigDict(from_attributes=True)

# --- NUEVOS MODELOS PARA CLIENTES (PERSONAS) ---
class Client(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    telegram_contact: Optional[str] = None
    coordinates: Optional[str] = None
    notes: Optional[str] = None
    service_status: str
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    created_at: datetime
    cpe_count: Optional[int] = 0 
    model_config = ConfigDict(from_attributes=True)

class ClientCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: str = 'active'
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: Optional[str] = None
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class AssignedCPE(BaseModel):
    mac: str
    hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


app = FastAPI(title="Ubiquiti Network Monitor API", version="1.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"

templates = Jinja2Templates(directory="templates")

# --- Funciones de Dependencia para la Base de Datos ---
def get_inventory_db():
    try:
        conn = sqlite3.connect(INVENTORY_DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

def get_stats_db():
    stats_db_file = _get_current_stats_db_file()
    if not os.path.exists(stats_db_file):
        return None
    try:
        conn = sqlite3.connect(stats_db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")
    finally:
        if conn:
            conn.close()
            
def _get_ap_by_host(host: str, conn: sqlite3.Connection):
    stats_db_file = _get_current_stats_db_file()
    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
    except sqlite3.OperationalError:
        cursor = conn.execute("SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id WHERE a.host = ?", (host,))
        return cursor.fetchone()
    
    query = """
        WITH LatestStats AS (
            SELECT 
                *, 
                ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
            FROM stats_db.ap_stats_history
            WHERE ap_host = ?
        )
        SELECT 
            a.*, 
            z.nombre as zona_nombre, 
            s.client_count, s.airtime_total_usage, s.airtime_tx_usage, s.airtime_rx_usage,
            s.total_throughput_tx, s.total_throughput_rx, s.noise_floor, s.chanbw, s.frequency,
            s.essid, s.total_tx_bytes, s.total_rx_bytes, s.gps_lat, s.gps_lon, s.gps_sats
        FROM aps AS a
        LEFT JOIN zonas AS z ON a.zona_id = z.id
        LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
        WHERE a.host = ?;
    """
    cursor = conn.execute(query, (host, host))
    return cursor.fetchone()

# --- Dependencia para obtener el usuario actual o redirigir al login ---
async def get_current_user_or_redirect(request: Request) -> User | RedirectResponse:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        return RedirectResponse(url="/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    try:
        user = await get_current_active_user(token)
        return user
    except HTTPException:
        response = RedirectResponse(url="/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response


# --- Endpoints de Autenticación y Páginas HTML ---

@app.get("/login", response_class=HTMLResponse, tags=["Auth"])
async def read_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token", tags=["Auth"], include_in_schema=False)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        request_data = {"request": {}, "error_message": "Incorrect username or password"}
        response = templates.TemplateResponse("login.html", request_data, status_code=status.HTTP_401_UNAUTHORIZED)
        return response

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME, 
        value=access_token, 
        httponly=True,
        max_age=int(access_token_expires.total_seconds()),
        samesite="Lax"
    )
    return response

@app.get("/logout", tags=["Auth"], include_in_schema=False)
async def logout_and_redirect():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return response

# --- Endpoints para servir las páginas HTML (AHORA PROTEGIDOS) ---
@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def read_dashboard(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "dashboard"})

@app.get("/ap/{host}", response_class=HTMLResponse, tags=["Dashboard"])
async def read_ap_details_page(request: Request, host: str, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("ap_details.html", {"request": request, "active_page": "ap_details", "host": host})

@app.get("/zonas", response_class=HTMLResponse, tags=["Dashboard"])
async def read_zones_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("zonas.html", {"request": request, "active_page": "zonas"})

@app.get("/settings", response_class=HTMLResponse, tags=["Dashboard"])
async def read_settings_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("settings.html", {"request": request, "active_page": "settings"})

@app.get("/users", response_class=HTMLResponse, tags=["Dashboard"])
async def read_users_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("users.html", {"request": request, "active_page": "users"})

@app.get("/cpes", response_class=HTMLResponse, tags=["Dashboard"])
async def read_cpes_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("cpes.html", {"request": request, "active_page": "cpes"})

# --- NUEVO ENDPOINT PARA LA PÁGINA DE CLIENTES ---
@app.get("/clients", response_class=HTMLResponse, tags=["Dashboard"])
async def read_clients_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    if isinstance(current_user, RedirectResponse): return current_user
    return templates.TemplateResponse("clients.html", {"request": request, "active_page": "clients"})


# --- Endpoint para el modo "Live" / Diagnóstico (AHORA PROTEGIDO) ---
@app.get("/api/aps/{host}/live", response_model=APLiveDetail, tags=["APs"])
def get_ap_live_data(host: str, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("SELECT username, password FROM aps WHERE host = ?", (host,))
    ap_credentials = cursor.fetchone()
    if not ap_credentials:
        raise HTTPException(status_code=404, detail="AP no encontrado en el inventario.")

    client = UbiquitiClient(
        host=host,
        username=ap_credentials['username'],
        password=ap_credentials['password']
    )
    status_data = client.get_status_data()

    if not status_data:
        raise HTTPException(status_code=503, detail="No se pudo obtener datos del AP. Puede estar offline.")

    host_info = status_data.get("host", {})
    wireless_info = status_data.get("wireless", {})
    ath0_status = status_data.get("interfaces", [{}, {}])[1].get("status", {})
    gps_info = status_data.get("gps", {})
    throughput_info = wireless_info.get("throughput", {})
    polling_info = wireless_info.get("polling", {})
    
    clients_list = []
    for cpe_data in wireless_info.get("sta", []):
        remote = cpe_data.get("remote", {})
        stats = cpe_data.get("stats", {})
        airmax = cpe_data.get("airmax", {})
        eth_info = remote.get("ethlist", [{}])[0]
        chainrssi = cpe_data.get('chainrssi', [None, None, None])

        clients_list.append(CPEDetail(
            cpe_mac=cpe_data.get("mac"), cpe_hostname=remote.get("hostname"),
            ip_address=cpe_data.get("lastip"), signal=cpe_data.get("signal"),
            signal_chain0=chainrssi[0], signal_chain1=chainrssi[1],
            noisefloor=cpe_data.get("noisefloor"), dl_capacity=airmax.get("dl_capacity"),
            ul_capacity=airmax.get("ul_capacity"), throughput_rx_kbps=remote.get('rx_throughput'),
            throughput_tx_kbps=remote.get('tx_throughput'), total_rx_bytes=stats.get('rx_bytes'),
            total_tx_bytes=stats.get('tx_bytes'), cpe_uptime=remote.get('uptime'),
            eth_plugged=eth_info.get('plugged'), eth_speed=eth_info.get('speed')
        ))

    response_data = APLiveDetail(
        host=host, username=ap_credentials['username'], is_enabled=True,
        hostname=host_info.get("hostname"), model=host_info.get("devmodel"),
        mac=status_data.get("interfaces", [{}, {}])[1].get("hwaddr"),
        firmware=host_info.get("fwversion"), last_status='online',
        client_count=wireless_info.get("count"), noise_floor=wireless_info.get("noisef"),
        chanbw=wireless_info.get("chanbw"), frequency=wireless_info.get("frequency"),
        essid=wireless_info.get("essid"), total_tx_bytes=ath0_status.get("tx_bytes"),
        total_rx_bytes=ath0_status.get("rx_bytes"), gps_lat=gps_info.get("lat"),
        gps_lon=gps_info.get("lon"), gps_sats=gps_info.get("sats"),
        total_throughput_tx=throughput_info.get("tx"), total_throughput_rx=throughput_info.get("rx"),
        airtime_total_usage=polling_info.get("use"), airtime_tx_usage=polling_info.get("tx_use"),
        airtime_rx_usage=polling_info.get("rx_use"), clients=clients_list
    )
    return response_data

# --- Endpoints de la API para Usuarios ---
@app.get("/api/users", response_model=List[UserResponse], tags=["Users"])
def api_get_all_users(current_user: User = Depends(get_current_active_user)):
    users = get_all_users()
    return users

@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def api_create_user(user_data: UserCreate, current_user: User = Depends(get_current_active_user)):
    hashed_password = get_password_hash(user_data.password)
    try:
        new_user = create_user_in_db(
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/users/{username}", response_model=UserResponse, tags=["Users"])
def api_update_user(username: str, user_data: UserUpdate, current_user: User = Depends(get_current_active_user)):
    updates = user_data.model_dump(exclude_unset=True)
    if 'password' in updates and updates['password']:
        updates['hashed_password'] = get_password_hash(updates.pop('password'))
    elif 'password' in updates:
        del updates['password']
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
    updated_user = update_user_in_db(username, updates)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return updated_user

@app.delete("/api/users/{username}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def api_delete_user(username: str, current_user: User = Depends(get_current_active_user)):
    if username == current_user.username:
        raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta.")
    was_deleted = delete_user_from_db(username)
    if not was_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return


# --- ENDPOINTS DE API PARA CLIENTES ---

@app.get("/api/clients", response_model=List[Client], tags=["Clients"])
def get_all_clients(conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    query = """
        SELECT c.*, COUNT(p.mac) as cpe_count
        FROM clients c
        LEFT JOIN cpes p ON c.id = p.client_id
        GROUP BY c.id
        ORDER BY c.name;
    """
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/clients", response_model=Client, status_code=status.HTTP_201_CREATED, tags=["Clients"])
def create_client(client: ClientCreate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    try:
        cursor = conn.execute(
            """INSERT INTO clients (name, address, phone_number, whatsapp_number, email, service_status, suspension_method, billing_day, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (client.name, client.address, client.phone_number, client.whatsapp_number, client.email, client.service_status, client.suspension_method, client.billing_day, client.notes)
        )
        conn.commit()
        new_client_id = cursor.lastrowid
        
        cursor = conn.execute("SELECT c.*, 0 as cpe_count FROM clients c WHERE c.id = ?", (new_client_id,))
        new_client_row = cursor.fetchone()
        if not new_client_row:
             raise HTTPException(status_code=404, detail="Could not retrieve client after creation.")
        return dict(new_client_row)
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"Database error: {e}")

@app.put("/api/clients/{client_id}", response_model=Client, tags=["Clients"])
def update_client(client_id: int, client_update: ClientUpdate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    update_fields = client_update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update provided.")
        
    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(client_id)
    
    cursor = conn.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", tuple(values))
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Client not found.")
        
    cursor = conn.execute("SELECT c.*, (SELECT COUNT(*) FROM cpes WHERE client_id = c.id) as cpe_count FROM clients c WHERE c.id = ?", (client_id,))
    updated_client_row = cursor.fetchone()
    if not updated_client_row:
        raise HTTPException(status_code=404, detail="Could not retrieve client after update.")
    return dict(updated_client_row)

@app.delete("/api/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Clients"])
def delete_client(client_id: int, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    conn.execute("UPDATE cpes SET client_id = NULL WHERE client_id = ?", (client_id,))
    cursor = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Client not found to delete.")
    return

# --- ENDPOINTS PARA GESTIÓN DE CPES ASIGNADOS A CLIENTES ---

@app.get("/api/clients/{client_id}/cpes", response_model=List[AssignedCPE], tags=["Clients"])
def get_cpes_for_client(client_id: int, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE client_id = ?", (client_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/cpes/unassigned", response_model=List[AssignedCPE], tags=["CPEs"])
def get_unassigned_cpes(conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE client_id IS NULL ORDER BY hostname")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/cpes/{mac}/assign/{client_id}", response_model=AssignedCPE, tags=["CPEs"])
def assign_cpe_to_client(mac: str, client_id: int, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    try:
        cursor = conn.execute("UPDATE cpes SET client_id = ? WHERE mac = ?", (client_id, mac))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="CPE not found.")
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=404, detail="Client ID not found.")
        
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE mac = ?", (mac,))
    updated_cpe = cursor.fetchone()
    return dict(updated_cpe)

@app.post("/api/cpes/{mac}/unassign", response_model=AssignedCPE, tags=["CPEs"])
def unassign_cpe(mac: str, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("UPDATE cpes SET client_id = NULL WHERE mac = ?", (mac,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="CPE not found.")
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE mac = ?", (mac,))
    unassigned_cpe = cursor.fetchone()
    return dict(unassigned_cpe)


# --- Endpoints de la API (Zonas, Settings, APs...) ---
@app.post("/api/zonas", response_model=Zona, status_code=status.HTTP_201_CREATED, tags=["Zonas"])
def create_zona(zona: ZonaCreate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    try:
        cursor = conn.execute("INSERT INTO zonas (nombre) VALUES (?)", (zona.nombre,))
        conn.commit()
        _id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="El nombre de la zona ya existe.")
    return {"id": _id, **zona.model_dump()}

@app.get("/api/zonas", response_model=List[Zona], tags=["Zonas"])
def get_all_zonas(conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("SELECT id, nombre FROM zonas ORDER BY nombre")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.put("/api/zonas/{zona_id}", response_model=Zona, tags=["Zonas"])
def update_zona(zona_id: int, zona_update: ZonaUpdate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    try:
        cursor = conn.execute("UPDATE zonas SET nombre = ? WHERE id = ?", (zona_update.nombre, zona_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Zona no encontrada.")
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="El nombre de la zona ya existe.")
    return {"id": zona_id, "nombre": zona_update.nombre}

@app.delete("/api/zonas/{zona_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Zonas"])
def delete_zona(zona_id: int, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor_check = conn.execute("SELECT 1 FROM aps WHERE zona_id = ?", (zona_id,))
    if cursor_check.fetchone():
        raise HTTPException(status_code=400, detail="No se puede eliminar la zona porque contiene APs.")
    cursor_delete = conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))
    conn.commit()
    if cursor_delete.rowcount == 0:
        raise HTTPException(status_code=404, detail="Zona no encontrada para eliminar.")
    return

@app.get("/api/settings", response_model=Dict[str, str], tags=["Settings"])
def api_get_settings(current_user: User = Depends(get_current_active_user)):
    return get_all_settings()

@app.put("/api/settings", status_code=status.HTTP_204_NO_CONTENT, tags=["Settings"])
def api_update_settings(settings: Dict[str, str], current_user: User = Depends(get_current_active_user)):
    update_settings(settings)
    return

@app.post("/api/aps", response_model=AP, status_code=status.HTTP_201_CREATED, tags=["APs"])
def create_ap(ap: APCreate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    monitor_interval = ap.monitor_interval
    if monitor_interval is None:
        default_interval_str = get_setting('default_monitor_interval')
        monitor_interval = int(default_interval_str) if default_interval_str and default_interval_str.isdigit() else 300
    try:
        conn.execute("INSERT INTO aps (host, username, password, zona_id, is_enabled, monitor_interval, first_seen) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                     (ap.host, ap.username, ap.password, ap.zona_id, ap.is_enabled, monitor_interval))
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Host duplicado o zona_id inválida. Error: {e}")
    
    new_ap = get_ap(host=ap.host, conn=conn)
    if not new_ap:
        raise HTTPException(status_code=404, detail="No se pudo encontrar el AP después de crearlo.")
    return new_ap

@app.get("/api/aps", response_model=List[AP], tags=["APs"])
def get_all_aps(conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    stats_db_file = _get_current_stats_db_file()
    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
    except sqlite3.OperationalError:
        query = "SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id ORDER BY a.host;"
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    query = """
        WITH LatestStats AS (
            SELECT 
                ap_host, client_count, airtime_total_usage,
                ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
            FROM stats_db.ap_stats_history
        )
        SELECT a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage
        FROM aps AS a
        LEFT JOIN zonas AS z ON a.zona_id = z.id
        LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
        ORDER BY a.host;
    """
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/aps/{host}", response_model=AP, tags=["APs"])
def get_ap(host: str, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    ap = _get_ap_by_host(host, conn)
    if not ap:
        raise HTTPException(status_code=404, detail="AP no encontrado.")
    return dict(ap)

@app.put("/api/aps/{host}", response_model=AP, tags=["APs"])
def update_ap(host: str, ap_update: APUpdate, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    update_fields = ap_update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar.")
    
    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(host)
    
    cursor = conn.execute(f"UPDATE aps SET {set_clause} WHERE host = ?", tuple(values))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="AP no encontrado.")
        
    return get_ap(host=host, conn=conn)

@app.delete("/api/aps/{host}", status_code=status.HTTP_204_NO_CONTENT, tags=["APs"])
def delete_ap(host: str, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    cursor = conn.execute("DELETE FROM aps WHERE host = ?", (host,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="AP no encontrado para eliminar.")
    return

# --- ENDPOINTS DE CPES ---
@app.get("/api/aps/{host}/cpes", response_model=List[CPEDetail], tags=["CPEs"])
def get_cpes_for_ap(host: str, conn: sqlite3.Connection = Depends(get_stats_db), current_user: User = Depends(get_current_active_user)):
    if not conn: return []
    query = """
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac, ap_host ORDER BY timestamp DESC) as rn
            FROM cpe_stats_history
            WHERE ap_host = ?
        )
        SELECT 
            cpe_mac, cpe_hostname, ip_address, signal, signal_chain0, signal_chain1,
            noisefloor, dl_capacity, ul_capacity, throughput_rx_kbps, throughput_tx_kbps,
            total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed 
        FROM LatestCPEStats WHERE rn = 1 ORDER BY signal DESC;
    """
    cursor = conn.execute(query, (host,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/cpes/all", response_model=List[CPEGlobalInfo], tags=["CPEs"])
def get_all_cpes_globally(
    inv_conn: sqlite3.Connection = Depends(get_inventory_db),
    stats_conn: sqlite3.Connection = Depends(get_stats_db), 
    current_user: User = Depends(get_current_active_user)
):
    if not stats_conn:
        return []
        
    try:
        stats_conn.execute(f"ATTACH DATABASE '{INVENTORY_DB_FILE}' AS inv_db")
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"DB Attach Error: {e}")

    query = """
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
            FROM cpe_stats_history
        )
        SELECT 
            s.*,
            a.hostname as ap_hostname
        FROM LatestCPEStats s
        LEFT JOIN inv_db.aps a ON s.ap_host = a.host
        WHERE s.rn = 1
        ORDER BY s.cpe_hostname, s.cpe_mac;
    """
    cursor = stats_conn.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


# --- ENDPOINTS DE ESTADÍSTICAS ---
@app.get("/api/stats/top-aps-by-airtime", response_model=List[TopAP], tags=["Stats"])
def get_top_aps_by_airtime(limit: int = 5, conn: sqlite3.Connection = Depends(get_inventory_db), current_user: User = Depends(get_current_active_user)):
    stats_db_file = _get_current_stats_db_file()
    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
    except sqlite3.OperationalError:
        return []

    query = """
        WITH LatestStats AS (
            SELECT 
                ap_host, airtime_total_usage,
                ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
            FROM stats_db.ap_stats_history
            WHERE airtime_total_usage IS NOT NULL
        )
        SELECT a.hostname, a.host, s.airtime_total_usage
        FROM aps as a 
        JOIN LatestStats s ON a.host = s.ap_host AND s.rn = 1
        ORDER BY s.airtime_total_usage DESC 
        LIMIT ?;
    """
    cursor = conn.execute(query, (limit,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/stats/top-cpes-by-signal", response_model=List[TopCPE], tags=["Stats"])
def get_top_cpes_by_weak_signal(limit: int = 5, conn: sqlite3.Connection = Depends(get_stats_db), current_user: User = Depends(get_current_active_user)):
    if not conn: return []
    query = """
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
            FROM cpe_stats_history
            WHERE signal IS NOT NULL
        )
        SELECT cpe_hostname, cpe_mac, ap_host, signal
        FROM LatestCPEStats
        WHERE rn = 1
        ORDER BY signal ASC 
        LIMIT ?;
    """
    cursor = conn.execute(query, (limit,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/aps/{host}/history", response_model=APHistoryResponse, tags=["APs"])
def get_ap_history(host: str, period: str = "24h", 
                   inv_conn: sqlite3.Connection = Depends(get_inventory_db), 
                   stats_conn: sqlite3.Connection = Depends(get_stats_db),
                   current_user: User = Depends(get_current_active_user)):
    if not stats_conn: return {"host": host, "hostname": host, "history": []}
    
    if period == "7d":
        start_time = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_time = datetime.utcnow() - timedelta(days=30)
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)
    
    ap_info = inv_conn.execute("SELECT hostname FROM aps WHERE host = ?", (host,)).fetchone()
    
    query = """
        SELECT timestamp, client_count, airtime_total_usage, total_throughput_tx, total_throughput_rx
        FROM ap_stats_history WHERE ap_host = ? AND timestamp >= ? ORDER BY timestamp ASC;
    """
    cursor = stats_conn.execute(query, (host, start_time))
    rows = cursor.fetchall()
    return {"host": host, "hostname": ap_info['hostname'] if ap_info else host, "history": [dict(row) for row in rows]}