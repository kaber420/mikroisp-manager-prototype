# app/api/routers/pppoe.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any

# --- CORRECCIÓN DE IMPORTS ---
from ...core.router_service import RouterService, get_router_service, RouterCommandError
from ...auth import User, get_current_active_user
# --- FIN DE CORRECCIÓN ---

from .models import PppoeSecretCreate, PppoeSecretUpdate, PppoeSecretDisable

router = APIRouter()

@router.get("/pppoe/secrets", response_model=List[Dict[str, Any]])
def api_get_pppoe_secrets(name: Optional[str] = Query(None), service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.get_pppoe_secrets(username=name)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pppoe/active", response_model=List[Dict[str, Any]])
def api_get_pppoe_active_connections(name: Optional[str] = Query(None), service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.get_pppoe_active_connections(name=name)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pppoe/secrets", response_model=Dict[str, Any])
def api_create_pppoe_secret(secret: PppoeSecretCreate, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.create_pppoe_secret(**secret.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.put("/pppoe/secrets/{secret_id:path}", response_model=Dict[str, Any])
def api_update_pppoe_secret(secret_id: str, secret_update: PppoeSecretUpdate, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    updates = secret_update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
    try:
        return service.update_pppoe_secret(secret_id, **updates)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/pppoe/secrets/{secret_id:path}/status", response_model=Dict[str, Any])
def api_disable_pppoe_secret(secret_id: str, status_update: PppoeSecretDisable, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.set_pppoe_secret_status(secret_id, disable=status_update.disable)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/pppoe/secrets/{secret_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_pppoe_secret(secret_id: str, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        service.remove_pppoe_secret(secret_id)
        return
    except RouterCommandError as e:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el 'secret': {e}")