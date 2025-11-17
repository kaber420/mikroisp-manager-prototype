# app/api/aps/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- ¡IMPORTACIONES CORREGIDAS! (Ahora con '...') ---
from ...auth import User, get_current_active_user
from ...services.ap_service import (
    APService, APNotFoundError, APUnreachableError, 
    APDataError, APCreateError
)
# --- ¡IMPORTACIÓN CORREGIDA! (Ahora desde '.models') ---
from .models import (
    AP, APCreate, APUpdate, CPEDetail, 
    APLiveDetail, HistoryDataPoint, APHistoryResponse
)

router = APIRouter()

# --- Dependencia del Inyector de Servicio ---
def get_ap_service() -> APService:
    return APService()

# --- Endpoints de la API (Sin cambios en la lógica) ---

@router.post("/aps", response_model=AP, status_code=status.HTTP_201_CREATED)
def create_ap(
    ap: APCreate, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        new_ap_data = service.create_ap(ap)
        return AP(**new_ap_data)
    except APCreateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.get("/aps", response_model=List[AP])
def get_all_aps(
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    aps_data = service.get_all_aps()
    return [AP(**ap) for ap in aps_data]

@router.get("/aps/{host}", response_model=AP)
def get_ap(
    host: str, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        ap_data = service.get_ap_by_host(host)
        return AP(**ap_data)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/aps/{host}", response_model=AP)
def update_ap(
    host: str, 
    ap_update: APUpdate, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        updated_ap_data = service.update_ap(host, ap_update)
        return AP(**updated_ap_data)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APDataError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/aps/{host}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ap(
    host: str, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        service.delete_ap(host)
        return
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/aps/{host}/cpes", response_model=List[CPEDetail])
def get_cpes_for_ap(
    host: str, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    cpes_data = service.get_cpes_for_ap(host)
    return [CPEDetail(**cpe) for cpe in cpes_data]

@router.get("/aps/{host}/live", response_model=APLiveDetail)
def get_ap_live_data(
    host: str, 
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.get_live_data(host)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/aps/{host}/history", response_model=APHistoryResponse)
def get_ap_history(
    host: str,
    period: str = "24h",
    service: APService = Depends(get_ap_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.get_ap_history(host, period)
    except APNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APDataError as e:
        raise HTTPException(status_code=500, detail=str(e))