# app/api/cpes/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...auth import User, get_current_active_user
from ...services.cpe_service import CPEService
from .models import CPEGlobalInfo, AssignedCPE

router = APIRouter()

# --- Dependencia del Inyector de Servicio ---
def get_cpe_service() -> CPEService:
    return CPEService()

# --- Endpoints de la API ---
@router.get("/cpes/unassigned", response_model=List[AssignedCPE])
def api_get_unassigned_cpes(
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_unassigned_cpes()

@router.post("/cpes/{mac}/assign/{client_id}", response_model=AssignedCPE)
def api_assign_cpe_to_client(
    mac: str, 
    client_id: int, 
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.assign_cpe_to_client(mac, client_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/cpes/{mac}/unassign", response_model=AssignedCPE)
def api_unassign_cpe(
    mac: str, 
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.unassign_cpe(mac)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/cpes/all", response_model=List[CPEGlobalInfo])
def api_get_all_cpes_globally(
    service: CPEService = Depends(get_cpe_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.get_all_cpes_globally()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))