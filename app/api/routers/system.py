# app/api/routers/system.py
from fastapi import APIRouter, Depends, HTTPException, status, Query # <-- AÑADIR Query
from typing import List, Dict, Any

from ...services.router_service import RouterService, get_router_service, RouterCommandError # <-- LÍNEA CAMBIADA
from ...auth import User, get_current_active_user
from ...db import router_db
# --- ¡IMPORTACIÓN MODIFICADA! ---
from .models import SystemResource, BackupCreateRequest, RouterUserCreate, PppoeSecretDisable

router = APIRouter()

@router.get("/resources", response_model=SystemResource)
def get_router_resources(host: str, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        resources = service.get_system_resources()
        # Actualizamos la DB con la info obtenida
        update_data = {
            "hostname": resources.get('name'),
            "model": resources.get('board-name'), 
            "firmware": resources.get('version')
        }
        router_db.update_router_in_db(host, update_data)
        return resources
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/files", response_model=List[Dict[str, Any]])
def api_get_backup_files(service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.get_backup_files()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/create-backup", response_model=Dict[str, str])
def api_create_backup(request: BackupCreateRequest, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        if request.backup_type == 'backup':
            if not request.backup_name.endswith('.backup'): request.backup_name += '.backup'
            service.create_backup(request.backup_name)
            message = f"Archivo .backup '{request.backup_name}' creado."
        elif request.backup_type == 'export':
            if not request.backup_name.endswith('.rsc'): request.backup_name += '.rsc'
            service.create_export_script(request.backup_name)
            message = f"Archivo .rsc '{request.backup_name}' creado."
        else:
            raise HTTPException(status_code=400, detail="Tipo de backup no válido. Usar 'backup' o 'export'.")
        
        return {"status": "success", "message": message}
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el archivo: {e}")

@router.delete("/system/files/{file_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_backup_file(file_id: str, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        service.remove_file(file_id)
        return
    except RouterCommandError as e:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el archivo: {e}")

@router.get("/system/users", response_model=List[Dict[str, Any]])
def api_get_router_users(service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.get_router_users()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=f"Error al leer usuarios del router: {e}")

@router.post("/system/users", response_model=Dict[str, Any])
def api_create_router_user(user_data: RouterUserCreate, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        return service.add_router_user(**user_data.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/system/users/{user_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_router_user(user_id: str, service: RouterService = Depends(get_router_service), user: User = Depends(get_current_active_user)):
    try:
        service.remove_router_user(user_id)
        return
    except RouterCommandError as e:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el usuario: {e}")

# --- ¡ENDPOINTS MODIFICADOS AQUÍ! ---

@router.patch("/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_set_interface_status(
    interface_id: str, 
    status_update: PppoeSecretDisable,  # Reutilizamos este modelo (espera {"disable": true/false})
    type: str = Query(..., description="El tipo de interfaz, ej. 'ether', 'bridge'"), # <-- AÑADIDO
    service: RouterService = Depends(get_router_service), 
    user: User = Depends(get_current_active_user)
):
    """Habilita o deshabilita una interfaz."""
    try:
        # Pasar el tipo al servicio
        service.set_interface_status(interface_id, status_update.disable, interface_type=type) # <-- AÑADIDO
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"No se pudo actualizar la interfaz {interface_id}. Causa: {e}")

@router.delete("/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_interface(
    interface_id: str, 
    type: str = Query(..., description="El tipo de interfaz, ej. 'vlan', 'bridge'"), # <-- AÑADIDO
    service: RouterService = Depends(get_router_service), 
    user: User = Depends(get_current_active_user)
):
    """Elimina una interfaz (VLAN, Bridge, etc.)."""
    try:
        # Pasar el tipo al servicio
        service.remove_interface(interface_id, interface_type=type) # <-- AÑADIDO
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"No se pudo eliminar la interfaz {interface_id}. Causa: {e}")