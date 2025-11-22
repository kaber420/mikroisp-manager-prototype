# app/api/routers/main.py
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import List
import ssl
from routeros_api import RouterOsApiPool
import asyncio
import logging

from ...auth import User, get_current_active_user
from ...db import router_db, settings_db
from ...services.monitor_service import MonitorService
from ...services.router_service import RouterService

# --- CAMBIO PRINCIPAL: Importación actualizada a la nueva estructura modular ---
# Antes: from ...utils.device_clients.mikrotik_client import provision_router_api_ssl 
from ...utils.device_clients.mikrotik.system import provision_router_api_ssl 

from .models import RouterResponse, RouterCreate, RouterUpdate, ProvisionRequest, ProvisionResponse
from . import config, pppoe, system, interfaces

router = APIRouter()

@router.websocket("/routers/{host}/ws/resources")
async def router_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del router (CPU, RAM, etc).
    Lee el intervalo de refresco dinámicamente desde la configuración.
    """
    await websocket.accept()
    
    try:
        # 1. Instanciamos el servicio. Esto valida y crea la conexión al Mikrotik.
        service = RouterService(host)
        
        while True:
            # --- A. Leer Configuración Dinámica ---
            # Consultamos la DB en cada ciclo para permitir cambios en tiempo real.
            interval_setting = settings_db.get_setting('dashboard_refresh_interval')
            
            try:
                # Si no existe o es inválido, usamos 2 segundos por defecto para que se sienta "Live"
                interval = int(interval_setting) if interval_setting else 2
                # Protección: Si el usuario puso 0 o negativo, forzamos 1 segundo mínimo
                if interval < 1: interval = 1
            except ValueError:
                interval = 2

            # --- B. Obtener Datos (Non-blocking) ---
            # Ejecutamos la librería síncrona (routeros_api) en un hilo aparte 
            # para no congelar el resto de la API de FastAPI.
            data = await asyncio.to_thread(service.get_system_resources)
            
            # --- C. Preparar Payload (ACTUALIZADO) ---
            payload = {
                "type": "resources",
                "data": {
                    # CPU y RAM (Ya funcionaban)
                    "cpu_load": data.get('cpu-load', 0),
                    "free_memory": data.get('free-memory', 0),
                    "total_memory": data.get('total-memory', 0),
                    "uptime": data.get('uptime', '--'),
                    
                    # --- CORRECCIÓN 1: DISCO ---
                    # Aseguramos que se envíen los datos de disco
                    "total_disk": data.get('total-disk', 0), 
                    "free_disk": data.get('free-disk', 0),

                    # --- CORRECCIÓN 2 y 3: SENSORES ---
                    # Enviamos null si no existen para que el JS sepa ocultarlos
                    "voltage": data.get('voltage'), 
                    "temperature": data.get('temperature'),       # Temp general/placa
                    "cpu_temperature": data.get('cpu-temperature') # Temp específica de CPU (si existe)
                }
            }
            
            # --- D. Enviar al Cliente ---
            await websocket.send_json(payload)
            
            # --- E. Dormir ---
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        print(f"WS: Cliente desconectado del stream {host}")
    except Exception as e:
        print(f"WS Error crítico en {host}: {e}")
        try:
            await websocket.close()
        except:
            pass

# --- Endpoints CRUD (Gestión de Routers en BD) ---
@router.get("/routers", response_model=List[RouterResponse])
def get_all_routers(current_user: User = Depends(get_current_active_user)):
    return router_db.get_all_routers()

@router.get("/routers/{host}", response_model=RouterResponse)
def get_router(host: str, current_user: User = Depends(get_current_active_user)):
    router_data = router_db.get_router_by_host(host)
    if not router_data:
        raise HTTPException(status_code=404, detail="Router not found")
    return router_data

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

# --- Endpoint de Aprovisionamiento ---
@router.post("/routers/{host}/provision", response_model=ProvisionResponse)
def provision_router_endpoint(host: str, data: ProvisionRequest, current_user: User = Depends(get_current_active_user)):
    creds = router_db.get_router_by_host(host)
    if not creds:
        raise HTTPException(status_code=404, detail="Router no encontrado")
        
    admin_pool: RouterOsApiPool = None
    try:
        # Conexión inicial insegura (sin SSL) para configurar el SSL
        admin_pool = RouterOsApiPool(
            creds['host'], 
            username=creds['username'], 
            password=creds['password'], 
            port=creds['api_port'], 
            use_ssl=False, 
            plaintext_login=True
        )
        api = admin_pool.get_api()
        
        # Llamada a la función modularizada
        result = provision_router_api_ssl(api, host, data.new_api_user, data.new_api_password)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
            
        # Actualizar DB con el nuevo usuario y puerto seguro
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
        if admin_pool:
            admin_pool.disconnect()


# --- Inclusión de los otros módulos de la API de routers ---
router.include_router(config.router, prefix="/routers/{host}")
router.include_router(pppoe.router, prefix="/routers/{host}")
router.include_router(system.router, prefix="/routers/{host}")
router.include_router(interfaces.router, prefix="/routers/{host}")

# --- NUEVO ENDPOINT PARA CONEXIÓN AUTOMÁTICA ---
@router.post("/routers/{host}/check", status_code=status.HTTP_200_OK)
def check_router_status_manual(host: str, current_user: User = Depends(get_current_active_user)):
    """
    Fuerza al monitor a leer los datos del router INMEDIATAMENTE.
    Se usa después de aprovisionar para poner el router 'Online' sin esperar 5 min.
    """
    creds = router_db.get_router_by_host(host)
    if not creds:
         raise HTTPException(status_code=404, detail="Router no encontrado")

    # Validaciones básicas antes de intentar conectar
    if not creds['is_enabled']:
         raise HTTPException(status_code=400, detail="El router está deshabilitado.")
    
    if creds['api_port'] != creds['api_ssl_port']:
         raise HTTPException(status_code=400, detail="El router no está aprovisionado (SSL).")
    
    try:
        # Instanciamos el servicio y ejecutamos el chequeo síncrono
        monitor = MonitorService()
        # Esto conecta, descarga info (CPU, Ver, etc) y actualiza la DB a 'online'
        monitor.check_router(creds) 
        return {"status": "success", "message": "Conexión verificada y datos actualizados."}
    except Exception as e:
        # Logueamos el error pero no rompemos la API si el router no responde
        raise HTTPException(status_code=500, detail=f"Fallo al conectar: {str(e)}")