# app/api/clients_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from ..auth import User, get_current_active_user
# --- CAMBIO: Importar los nuevos módulos de DB ---
from ..db import clients_db

router = APIRouter()

# --- Modelos Pydantic (sin cambios) ---
class Client(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    telegram_contact: Optional[str] = None
    coordinates: Optional[str] = None
    notes: Optional[str] = None
    service_status: str
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    created_at: datetime
    cpe_count: Optional[int] = 0 
    model_config = ConfigDict(from_attributes=True)

class ClientCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: str = 'active'
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: Optional[str] = None
    suspension_method: Optional[str] = None
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class AssignedCPE(BaseModel):
    mac: str
    hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- Endpoints de la API ---

@router.get("/clients", response_model=List[Client])
def api_get_all_clients(current_user: User = Depends(get_current_active_user)):
    return clients_db.get_all_clients_with_cpe_count()

@router.post("/clients", response_model=Client, status_code=status.HTTP_201_CREATED)
def api_create_client(client: ClientCreate, current_user: User = Depends(get_current_active_user)):
    try:
        new_client = clients_db.create_client(client.model_dump())
        return new_client
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {e}")

@router.put("/clients/{client_id}", response_model=Client)
def api_update_client(client_id: int, client_update: ClientUpdate, current_user: User = Depends(get_current_active_user)):
    update_fields = client_update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update provided.")
        
    updated_client = clients_db.update_client(client_id, update_fields)
    if not updated_client:
        raise HTTPException(status_code=404, detail="Client not found.")
    return updated_client

@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client(client_id: int, current_user: User = Depends(get_current_active_user)):
    deleted_rows = clients_db.delete_client(client_id)
    if deleted_rows == 0:
        raise HTTPException(status_code=404, detail="Client not found to delete.")
    return

@router.get("/clients/{client_id}/cpes", response_model=List[AssignedCPE])
def api_get_cpes_for_client(client_id: int, current_user: User = Depends(get_current_active_user)):
    return clients_db.get_cpes_for_client(client_id)