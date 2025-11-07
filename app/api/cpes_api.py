# app/api/cpes_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from ..auth import User, get_current_active_user
# --- CAMBIO: Importar el nuevo módulo de DB ---
from ..db import cpes_db

router = APIRouter()

# --- Modelos Pydantic (sin cambios) ---
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

class CPEGlobalInfo(CPEDetail):
    ap_host: Optional[str] = None
    ap_hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AssignedCPE(BaseModel):
    mac: str
    hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Endpoints de la API ---

@router.get("/cpes/unassigned", response_model=List[AssignedCPE])
def api_get_unassigned_cpes(current_user: User = Depends(get_current_active_user)):
    return cpes_db.get_unassigned_cpes()

@router.post("/cpes/{mac}/assign/{client_id}", response_model=AssignedCPE)
def api_assign_cpe_to_client(mac: str, client_id: int, current_user: User = Depends(get_current_active_user)):
    try:
        rows_affected = cpes_db.assign_cpe_to_client(mac, client_id)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="CPE not found.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # Client ID no encontrado
        
    updated_cpe = cpes_db.get_cpe_by_mac(mac)
    if not updated_cpe:
        raise HTTPException(status_code=404, detail="Could not retrieve CPE after assignment.")
    return updated_cpe

@router.post("/cpes/{mac}/unassign", response_model=AssignedCPE)
def api_unassign_cpe(mac: str, current_user: User = Depends(get_current_active_user)):
    rows_affected = cpes_db.unassign_cpe(mac)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="CPE not found.")
    
    unassigned_cpe = cpes_db.get_cpe_by_mac(mac)
    if not unassigned_cpe:
        raise HTTPException(status_code=404, detail="Could not retrieve CPE after unassignment.")
    return unassigned_cpe

@router.get("/cpes/all", response_model=List[CPEGlobalInfo])
def api_get_all_cpes_globally(current_user: User = Depends(get_current_active_user)):
    try:
        return cpes_db.get_all_cpes_globally()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))