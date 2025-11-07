# app/api/routers_api.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
import time
import ssl # <-- AÑADIR IMPORTACIÓN
from typing import List, Optional, Dict, Any

# Importaciones de módulos del proyecto
from ..auth import User, get_current_active_user
from ..db import router_db

# --- IMPORTACIONES ACTUALIZADAS ---
from routeros_api import RouterOsApiPool # <-- USAR RouterOsApiPool
from routeros_api.api import RouterOsApi
from ..core.mikrotik_client import (
    # Ya no importamos 'get_api_connection'
    provision_router_api_ssl, 
    get_system_resources,
    install_core_config,
    get_interfaces,
    get_ip_addresses,
    get_nat_rules,
    get_pppoe_servers,
    get_ppp_profiles,
    get_simple_queues,
    get_ip_pools,
    create_service_plan,
    add_ip_address,
    add_nat_masquerade,
    add_pppoe_server,
    remove_ip_address,
    remove_nat_rule,
    remove_pppoe_server,
    remove_service_plan,
    # --- ¡NUEVAS IMPORTACIONES PPPoE! ---
    get_pppoe_secrets,
    get_pppoe_active_connections,
    create_pppoe_secret,
    update_pppoe_secret,
    enable_disable_pppoe_secret,
    remove_pppoe_secret
)

router = APIRouter()

# --- Modelos Pydantic (Sin cambios) ---
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
    name: Optional[str] = None
    model_config = ConfigDict(extra='ignore')

class CoreConfigRequest(BaseModel):
    pppoe_interface: str

class AddIpRequest(BaseModel):
    interface: str
    address: str
    comment: str = "Managed by µMonitor"

class AddNatRequest(BaseModel):
    out_interface: str
    comment: str = "NAT-WAN (µMonitor)"

class AddPppoeServerRequest(BaseModel):
    service_name: str
    interface: str
    default_profile: str = "default"

class CreatePlanRequest(BaseModel):
    plan_name: str
    bandwidth: str
    pool_range: str
    local_address: str
    comment: str = "Managed by µMonitor"

class RouterFullDetails(BaseModel):
    interfaces: List[Dict[str, Any]]
    ip_addresses: List[Dict[str, Any]]
    nat_rules: List[Dict[str, Any]]
    pppoe_servers: List[Dict[str, Any]]
    ppp_profiles: List[Dict[str, Any]]
    simple_queues: List[Dict[str, Any]]
    ip_pools: List[Dict[str, Any]]

# --- ¡NUEVOS MODELOS PARA PPPoE! ---
class PppoeSecretCreate(BaseModel):
    username: str
    password: str
    profile: str
    comment: str = ""
    service: str = 'pppoe'

class PppoeSecretUpdate(BaseModel):
    password: Optional[str] = None
    profile: Optional[str] = None
    comment: Optional[str] = None

class PppoeSecretDisable(BaseModel):
    disable: bool = True

# --- Dependencias (Refactorizadas) ---

def get_router_creds(host: str) -> Dict[str, Any]:
    router_creds = router_db.get_router_by_host(host)
    if not router_creds:
        raise HTTPException(status_code=404, detail="Router not found in database")
    return router_creds

# --- CORRECCIÓN DE FUGA #1 (Usando RouterOsApiPool) ---
def get_router_api_connection(creds: dict = Depends(get_router_creds)):
    """
    Dependencia que proporciona una conexión API-SSL a un router aprovisionado
    usando un Pool y asegurando su cierre.
    """
    if creds['api_port'] != creds['api_ssl_port']:
         raise HTTPException(status_code=400, detail="Router is not provisioned. Please provision first.")
    
    # Crear el SSL context aquí
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    pool: Optional[RouterOsApiPool] = None
    try:
        # 1. Crear el Pool (el 'connection' de tu ejemplo)
        pool = RouterOsApiPool(
            creds['host'], 
            username=creds['username'], 
            password=creds['password'], 
            port=creds['api_ssl_port'],
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True
        )
        # 2. Obtener el objeto 'api' del pool
        api = pool.get_api()
        yield api # Entregar el objeto 'api' al endpoint
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Connection Error: {e}")
    finally:
        # 3. Llamar a .disconnect() SOBRE EL POOL
        if pool:
            pool.disconnect()
# --- FIN DE CORRECCIÓN ---

# --- Endpoints CRUD (Sin cambios) ---
@router.get("/routers", response_model=List[RouterResponse])
def get_all_routers(current_user: User = Depends(get_current_active_user)):
    return router_db.get_all_routers()

@router.post("/routers", response_model=RouterResponse, status_code=status.HTTP_201_CREATED)
def create_router(router_data: RouterCreate, current_user: User = Depends(get_current_active_user)):
    try:
        new_router = router_db.create_router_in_db(router_data.model_dump())
        return new_router
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/routers/{host}", response_model=RouterResponse)
def update_router(host: str, router_data: RouterUpdate, current_user: User = Depends(get_current_active_user)):
    update_fields = router_data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update provided.")
    if "password" in update_fields and not update_fields["password"]:
        del update_fields["password"] 
    rows_affected = router_db.update_router_in_db(host, update_fields)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="Router not found.")
    updated_router = router_db.get_router_by_host(host)
    if not updated_router:
        raise HTTPException(status_code=404, detail="No se pudo recuperar el router después de la actualización.")
    return updated_router

@router.delete("/routers/{host}", status_code=status.HTTP_204_NO_CONTENT)
def delete_router(host: str, current_user: User = Depends(get_current_active_user)):
    rows_affected = router_db.delete_router_from_db(host)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="Router not found to delete.")
    return

# --- Endpoints de Operaciones ---

# --- CORRECCIÓN DE FUGA #2 (Usando RouterOsApiPool) ---
@router.post("/routers/{host}/provision", response_model=ProvisionResponse)
def provision_router(
    host: str, 
    data: ProvisionRequest,
    creds: dict = Depends(get_router_creds),
    current_user: User = Depends(get_current_active_user)
):
    admin_pool: Optional[RouterOsApiPool] = None # Definir pool fuera del try
    try:
        # 1. Crear el Pool (sin SSL para aprovisionamiento)
        admin_pool = RouterOsApiPool(
            creds['host'], 
            username=creds['username'], 
            password=creds['password'], 
            port=creds['api_port'],
            use_ssl=False,
            plaintext_login=True
        )
        # 2. Obtener el objeto 'api' del pool
        admin_api = admin_pool.get_api()
        
        result = provision_router_api_ssl(
            admin_api, 
            creds['host'], 
            data.new_api_user, 
            data.new_api_password
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        update_data = {
            "username": data.new_api_user,
            "password": data.new_api_password,
            "api_port": creds['api_ssl_port']
        }
        router_db.update_router_in_db(host, update_data)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 3. Llamar a .disconnect() SOBRE EL POOL
        if 'admin_pool' in locals() and admin_pool:
            admin_pool.disconnect()
# --- FIN DE CORRECCIÓN ---

@router.get("/routers/{host}/resources", response_model=SystemResource)
def get_router_resources(host: str, api: RouterOsApi = Depends(get_router_api_connection), creds: dict = Depends(get_router_creds), current_user: User = Depends(get_current_active_user)):
    try:
        resources = get_system_resources(api)
        if not creds.get('hostname') and resources.get('name'):
            update_data = {"hostname": resources.get('name'), "model": resources.get('board_name'), "firmware": resources.get('version')}
            router_db.update_router_in_db(host, update_data)
        return resources
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routers/{host}/install-core-config", response_model=ProvisionResponse)
def install_router_core_config(host: str, config_data: CoreConfigRequest, api: RouterOsApi = Depends(get_router_api_connection), current_user: User = Depends(get_current_active_user)):
    try:
        result = install_core_config(api, config_data.pppoe_interface)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT EFICIENTE PARA DETALLES ---
@router.get("/routers/{host}/full-details", response_model=RouterFullDetails)
def get_router_full_details(
    host: str, 
    api: RouterOsApi = Depends(get_router_api_connection),
    c: User = Depends(get_current_active_user)
):
    try:
        interfaces = get_interfaces(api)
        ips = get_ip_addresses(api)
        nat = get_nat_rules(api)
        pppoe = get_pppoe_servers(api)
        profiles = get_ppp_profiles(api)
        queues = get_simple_queues(api)
        pools = get_ip_pools(api)
        
        return {
            "interfaces": interfaces,
            "ip_addresses": ips,
            "nat_rules": nat,
            "pppoe_servers": pppoe,
            "ppp_profiles": profiles,
            "simple_queues": queues,
            "ip_pools": pools
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading bulk data from router: {e}")

# --- Endpoints de Lectura (Individuales, los eliminaremos del frontend) ---
@router.get("/routers/{host}/read/interfaces", response_model=List[Dict[str, Any]])
def read_router_interfaces(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_interfaces(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading interfaces: {e}")

@router.get("/routers/{host}/read/ip-addresses", response_model=List[Dict[str, Any]])
def read_router_ip_addresses(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_ip_addresses(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading IP addresses: {e}")

@router.get("/routers/{host}/read/nat-rules", response_model=List[Dict[str, Any]])
def read_router_nat_rules(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_nat_rules(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading NAT rules: {e}")

@router.get("/routers/{host}/read/pppoe-servers", response_model=List[Dict[str, Any]])
def read_router_pppoe_servers(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_pppoe_servers(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PPPoE servers: {e}")

@router.get("/routers/{host}/read/ppp-profiles", response_model=List[Dict[str, Any]])
def read_router_ppp_profiles(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_ppp_profiles(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PPP profiles: {e}")

@router.get("/routers/{host}/read/simple-queues", response_model=List[Dict[str, Any]])
def read_router_simple_queues(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_simple_queues(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading simple queues: {e}")

@router.get("/routers/{host}/read/ip-pools", response_model=List[Dict[str, Any]])
def read_router_ip_pools(api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        return get_ip_pools(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading IP pools: {e}")


# --- Endpoints de Escritura (ADD) (Sin cambios) ---
@router.post("/routers/{host}/write/create-plan", response_model=Dict[str, Any])
def write_create_service_plan(data: CreatePlanRequest, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        result = create_service_plan(api, data.plan_name, data.bandwidth, data.pool_range, data.local_address, data.comment)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routers/{host}/write/add-ip", response_model=Dict[str, Any])
def write_add_ip_address(data: AddIpRequest, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        api_response = add_ip_address(api, data.interface, data.address, data.comment)
        return {"status": "success", "message": "IP address added.", "data": api_response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/routers/{host}/write/add-nat", response_model=Dict[str, Any])
def write_add_nat_rule(data: AddNatRequest, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        api_response = add_nat_masquerade(api, data.out_interface, data.comment)
        if isinstance(api_response, dict) and api_response.get("status") == "warning":
            return api_response
        return {"status": "success", "message": "NAT rule added.", "data": api_response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/routers/{host}/write/add-pppoe-server", response_model=Dict[str, Any])
def write_add_pppoe_server(data: AddPppoeServerRequest, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        api_response = add_pppoe_server(api, data.service_name, data.interface, data.default_profile)
        if isinstance(api_response, dict) and api_response.get("status") == "warning":
            return api_response
        return {"status": "success", "message": "PPPoE server added.", "data": api_response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Endpoints de Escritura (DELETE) (Sin cambios) ---
@router.delete("/routers/{host}/write/delete-ip", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_ip_address(host: str, address: str = Query(..., description="La dirección IP a eliminar, ej: 192.168.1.1/24"), api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        success = remove_ip_address(api, address)
        if not success:
            raise HTTPException(status_code=404, detail="IP address not found on router.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return

@router.delete("/routers/{host}/write/delete-nat", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_nat_rule(host: str, comment: str = Query(..., description="El comentario de la regla NAT a eliminar"), api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        success = remove_nat_rule(api, comment)
        if not success:
            raise HTTPException(status_code=404, detail="NAT rule with that comment not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return

@router.delete("/routers/{host}/write/delete-pppoe-server", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_pppoe_server(host: str, service_name: str = Query(..., description="El 'service-name' del servidor PPPoE a eliminar"), api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        success = remove_pppoe_server(api, service_name)
        if not success:
            raise HTTPException(status_code=404, detail="PPPoE server with that service name not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return

@router.delete("/routers/{host}/write/delete-plan", response_model=Dict[str, bool])
def write_delete_service_plan(host: str, plan_name: str = Query(..., description="El nombre del plan a eliminar (ej: Oro, Plata)"), api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    try:
        results = remove_service_plan(api, plan_name)
        if not results:
             raise HTTPException(status_code=404, detail="No components found for that plan name.")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---
# ¡NUEVA SECCIÓN! Endpoints de Gestión de PPPoE
# ---

@router.get("/routers/{host}/pppoe/secrets", response_model=List[Dict[str, Any]])
def api_get_pppoe_secrets(host: str, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Obtiene todos los 'secrets' (usuarios) PPPoE del router."""
    try:
        return get_pppoe_secrets(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routers/{host}/pppoe/active", response_model=List[Dict[str, Any]])
def api_get_pppoe_active_connections(host: str, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Obtiene todas las conexiones PPPoE activas en este momento."""
    try:
        return get_pppoe_active_connections(api)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routers/{host}/pppoe/secrets", response_model=Dict[str, Any])
def api_create_pppoe_secret(host: str, secret: PppoeSecretCreate, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Crea un nuevo 'secret' (usuario) PPPoE."""
    try:
        new_secret = create_pppoe_secret(
            api, 
            username=secret.username, 
            password=secret.password, 
            profile=secret.profile,
            comment=secret.comment,
            service=secret.service
        )
        return new_secret
    except ValueError as e: # Captura el error de "usuario duplicado"
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.put("/routers/{host}/pppoe/secrets/{secret_id}", response_model=Dict[str, Any])
def api_update_pppoe_secret(host: str, secret_id: str, secret_update: PppoeSecretUpdate, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Actualiza un 'secret' PPPoE (ej. cambiar contraseña o plan)."""
    
    # El ID en MikroTik a menudo contiene '*', así que lo decodificamos
    decoded_secret_id = secret_id.replace("%2A", "*")
    
    updates = secret_update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
    
    try:
        updated_secret = update_pppoe_secret(api, decoded_secret_id, **updates)
        return updated_secret
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/routers/{host}/pppoe/secrets/{secret_id}/status", response_model=Dict[str, Any])
def api_disable_pppoe_secret(host: str, secret_id: str, status: PppoeSecretDisable, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Activa o desactiva (suspende/reactiva) un 'secret' PPPoE."""
    decoded_secret_id = secret_id.replace("%2A", "*")
    
    try:
        updated_secret = enable_disable_pppoe_secret(api, decoded_secret_id, disable=status.disable)
        return updated_secret
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/routers/{host}/pppoe/secrets/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_pppoe_secret(host: str, secret_id: str, api: RouterOsApi = Depends(get_router_api_connection), c: User = Depends(get_current_active_user)):
    """Elimina un 'secret' PPPoE."""
    decoded_secret_id = secret_id.replace("%2A", "*")
    
    try:
        remove_pppoe_secret(api, decoded_secret_id)
        return
    except Exception as e:
        # Podría fallar si el ID no existe
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el 'secret' con ID {decoded_secret_id}. Causa: {e}")