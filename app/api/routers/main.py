# app/api/routers/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import ssl
from routeros_api import RouterOsApiPool

# --- CORRECCIÓN DE IMPORTS ---
from ...auth import User, get_current_active_user
from ...db import router_db
from ...core.mikrotik_client import provision_router_api_ssl
# --- FIN DE CORRECCIÓN ---

from .models import RouterResponse, RouterCreate, RouterUpdate, ProvisionRequest, ProvisionResponse
from . import config, pppoe, system

router = APIRouter()

# --- Endpoints CRUD (Gestión de Routers en BD) ---
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
         raise HTTPException(status_code=404, detail="Could not retrieve router after update.")
    return updated_router

@router.delete("/routers/{host}", status_code=status.HTTP_204_NO_CONTENT)
def delete_router(host: str, current_user: User = Depends(get_current_active_user)):
    rows_affected = router_db.delete_router_from_db(host)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="Router not found to delete.")
    return

# --- Endpoint de Aprovisionamiento (Lógica especial que no usa el servicio SSL) ---
@router.post("/routers/{host}/provision", response_model=ProvisionResponse)
def provision_router_endpoint(host: str, data: ProvisionRequest, current_user: User = Depends(get_current_active_user)):
    creds = router_db.get_router_by_host(host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")
        
    admin_pool: RouterOsApiPool = None
    try:
        admin_pool = RouterOsApiPool(creds['host'], username=creds['username'], password=creds['password'], port=creds['api_port'], use_ssl=False, plaintext_login=True)
        api = admin_pool.get_api()
        result = provision_router_api_ssl(api, host, data.new_api_user, data.new_api_password)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
            
        update_data = {"username": data.new_api_user, "password": data.new_api_password, "api_port": creds['api_ssl_port']}
        router_db.update_router_in_db(host, update_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if admin_pool:
            admin_pool.disconnect()


# --- Inclusión de los otros módulos de la API de routers ---
router.include_router(config.router, prefix="/routers/{host}")
router.include_router(pppoe.router, prefix="/routers/{host}")
router.include_router(system.router, prefix="/routers/{host}")