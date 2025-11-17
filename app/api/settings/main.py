# app/api/settings/main.py
from fastapi import APIRouter, Depends, status, HTTPException
from typing import Dict

from ...auth import User, get_current_active_user
from ...services.settings_service import SettingsService
from ...services.billing_service import BillingService
from ...services.monitor_service import MonitorService

router = APIRouter()

def get_settings_service() -> SettingsService:
    return SettingsService()

@router.get("/settings", response_model=Dict[str, str])
def api_get_settings(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_all_settings()

@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def api_update_settings(
    settings: Dict[str, str], 
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
):
    service.update_settings(settings)
    return

# --- NUEVOS ENDPOINTS DE GESTIÓN MANUAL ---

@router.post("/settings/force-billing", status_code=200)
def force_billing_update(
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint administrativo para forzar la actualización de estados de facturación.
    """
    try:
        service = BillingService()
        stats = service.process_daily_suspensions()
        return {"message": "Estados actualizados correctamente.", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/force-monitor", status_code=200)
def force_monitor_scan(
    current_user: User = Depends(get_current_active_user)
):
    """
    Dispara una señal (simulada o real) para el monitor. 
    Nota: En esta arquitectura simple, esto solo devuelve confirmación ya que el monitor corre en otro proceso.
    Para una implementación real de 'forzar ahora', se requeriría una cola de tareas compartida (Redis/Celery).
    """
    return {"message": "El monitor continuará su ciclo en segundo plano (intervalo normal)."}