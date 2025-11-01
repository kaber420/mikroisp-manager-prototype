# routers_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
import sqlite3
import time
from typing import List, Optional, Dict, Any

# Importaciones de módulos del proyecto
from auth import User, get_current_active_user
# --- MODIFICACIÓN: Ya no importamos get_db_connection, solo la constante ---
from database import INVENTORY_DB_FILE
from mikrotik_client import (
    get_api_connection, 
    provision_router_api_ssl, 
    get_system_resources,
    install_core_config
    # (Aquí importarías más funciones de mikrotik_client a medida que las agregues)
)

# 1. Crea un ROUTER, no una APP
router = APIRouter()

# --- Modelos Pydantic para Routers ---

class RouterBase(BaseModel):
    host: str
    username: str
    zona_id: Optional[int] = None
    api_port: int = 8728
    api_ssl_port: int = 8729
    is_enabled: bool = True

class RouterCreate(RouterBase):
    password: str

class RouterUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    is_enabled: Optional[bool] = None

class RouterResponse(RouterBase):
    model_config = ConfigDict(from_attributes=True)
    
    hostname: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None

class ProvisionRequest(BaseModel):
    new_api_user: str
    new_api_password: str

class ProvisionResponse(BaseModel):
    status: str
    message: str

class SystemResource(BaseModel):
    version: Optional[str] = None
    platform: Optional[str] = None
    board_name: Optional[str] = None
    cpu: Optional[str] = None
    name: Optional[str] = None # De /system/identity
    model_config = ConfigDict(extra='ignore') # Ignora otros campos de la API

class CoreConfigRequest(BaseModel):
    pppoe_interface: str


# --- INICIO DE BLOQUE CORREGIDO ---
# --- Dependencia de Conexión a BD ---
def get_inventory_db():
    """
    Dependencia de FastAPI para la base de datos de inventario.
    Esta versión es idéntica a la de api.py y soluciona el error de threads.
    """
    try:
        conn = sqlite3.connect(INVENTORY_DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")
    finally:
        if conn:
            conn.close()
# --- FIN DE BLOQUE CORREGIDO ---


# --- Dependencia para obtener credenciales de router ---
def get_router_creds(host: str, conn: sqlite3.Connection = Depends(get_inventory_db)) -> Dict[str, Any]:
    """Obtiene los datos de un router de la BD."""
    cursor = conn.execute("SELECT * FROM routers WHERE host = ?", (host,))
    router_creds = cursor.fetchone()
    if not router_creds:
        raise HTTPException(status_code=404, detail="Router not found in database")
    return dict(router_creds)

#
# 2. Endpoints CRUD para Routers
#
@router.get("/routers", response_model=List[RouterResponse], tags=["Routers"])
def get_all_routers(
    conn: sqlite3.Connection = Depends(get_inventory_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene una lista de todos los routers configurados."""
    cursor = conn.execute("SELECT * FROM routers ORDER BY host")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@router.post("/routers", response_model=RouterResponse, status_code=status.HTTP_201_CREATED, tags=["Routers"])
def create_router(
    router_data: RouterCreate, 
    conn: sqlite3.Connection = Depends(get_inventory_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Añade un nuevo router a la base de datos (sin aprovisionar)."""
    try:
        conn.execute(
            """INSERT INTO routers (host, username, password, zona_id, api_port, is_enabled) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (router_data.host, router_data.username, router_data.password, router_data.zona_id, router_data.api_port, router_data.is_enabled)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Router host (IP) already exists.")
    
    new_router = get_router_creds(router_data.host, conn)
    return new_router

@router.put("/routers/{host}", response_model=RouterResponse, tags=["Routers"])
def update_router(
    host: str,
    router_data: RouterUpdate,
    conn: sqlite3.Connection = Depends(get_inventory_db),
    current_user: User = Depends(get_current_active_user)
):
    """Actualiza los datos de un router en la base de datos."""
    update_fields = router_data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update provided.")

    # Si la contraseña está vacía, no la actualizamos
    if "password" in update_fields and not update_fields["password"]:
        del update_fields["password"]

    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(host)
    
    cursor = conn.execute(f"UPDATE routers SET {set_clause} WHERE host = ?", tuple(values))
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Router not found.")
        
    updated_router = get_router_creds(host, conn)
    return updated_router

@router.delete("/routers/{host}", status_code=status.HTTP_204_NO_CONTENT, tags=["Routers"])
def delete_router(
    host: str,
    conn: sqlite3.Connection = Depends(get_inventory_db),
    current_user: User = Depends(get_current_active_user)
):
    """Elimina un router de la base de datos."""
    cursor = conn.execute("DELETE FROM routers WHERE host = ?", (host,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Router not found to delete.")
    return

#
# 3. Endpoint de Aprovisionamiento (Llama a tu script)
#
@router.post("/routers/{host}/provision", response_model=ProvisionResponse, tags=["Routers"])
def provision_router(
    host: str, 
    data: ProvisionRequest,
    conn: sqlite3.Connection = Depends(get_inventory_db), 
    creds: dict = Depends(get_router_creds),
    current_user: User = Depends(get_current_active_user)
):
    """
    Aprovisiona un router. Se conecta con las credenciales de ADMIN guardadas
    y crea el nuevo usuario API y el SSL.
    """
    try:
        # 1. Conexión INSEGURA (sin SSL) usando creds de admin guardadas
        admin_api = get_api_connection(
            host=creds['host'], 
            user=creds['username'], 
            password=creds['password'], 
            port=creds['api_port'], # Puerto API sin SSL (ej. 8728)
            use_ssl=False
        )
        
        # 2. Llama a tu lógica de aprovisionamiento
        result = provision_router_api_ssl(
            admin_api, 
            creds['host'], 
            data.new_api_user, 
            data.new_api_password
        )
        # --- LÍNEA ELIMINADA (Esta era la causa del error 'disconnect') ---
        # admin_api.disconnect() 

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        # 3. ÉXITO: Actualizar la BD con las NUEVAS credenciales y puerto
        conn.execute(
            "UPDATE routers SET username = ?, password = ?, api_port = ? WHERE host = ?",
            (data.new_api_user, data.new_api_password, creds['api_ssl_port'], host)
        )
        conn.commit()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#
# 4. Endpoints de Operaciones (Ejemplos)
#
@router.get("/routers/{host}/resources", response_model=SystemResource, tags=["Routers"])
def get_router_resources(
    host: str, 
    creds: dict = Depends(get_router_creds), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtiene los recursos del sistema (ejemplo de operación 'read').
    Asume que el router ya está aprovisionado.
    """
    if creds['api_port'] != creds['api_ssl_port']:
         raise HTTPException(status_code=400, detail="Router is not provisioned. Please provision first.")
    
    try:
        # Conexión SEGURA (SSL) usando creds de API guardadas
        api = get_api_connection(
            host=creds['host'], 
            user=creds['username'], 
            password=creds['password'], 
            port=creds['api_ssl_port'], # Puerto API-SSL (ej. 8729)
            use_ssl=True
        )
        
        resources = get_system_resources(api)
        # --- LÍNEA ELIMINADA (Esta era la causa del error 'disconnect') ---
        # api.disconnect()
        
        # Actualizar hostname en la BD si no está
        if not creds['hostname'] and resources.get('name'):
            conn = get_db_connection(INVENTORY_DB_FILE)
            conn.execute("UPDATE routers SET hostname = ?, model = ?, firmware = ? WHERE host = ?", 
                         (resources.get('name'), resources.get('board_name'), resources.get('version'), host))
            conn.commit()
            conn.close()

        return resources
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routers/{host}/install-core-config", response_model=ProvisionResponse, tags=["Routers"])
def install_router_core_config(
    host: str, 
    config_data: CoreConfigRequest,
    creds: dict = Depends(get_router_creds), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Ejecuta la lógica de 'install_core_config' de tu script.
    """
    if creds['api_port'] != creds['api_ssl_port']:
         raise HTTPException(status_code=400, detail="Router is not provisioned. Please provision first.")

    try:
        api = get_api_connection(
            host=creds['host'], 
            user=creds['username'], 
            password=creds['password'], 
            port=creds['api_ssl_port'], 
            use_ssl=True
        )
        
        result = install_core_config(api, config_data.pppoe_interface)
        # --- LÍNEA ELIMINADA (Esta era la causa del error 'disconnect') ---
        # api.disconnect()

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))