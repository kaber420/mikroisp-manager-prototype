# app/api/clients_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from ..auth import User, get_current_active_user
from ..db import clients_db, payments_db
from ..core import billing_service # Asumimos que quieres mantener la lógica de reactivación

router = APIRouter()

# --- Modelos Pydantic (Cliente) ---
class Client(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: str
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
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    service_status: Optional[str] = None
    billing_day: Optional[int] = None
    notes: Optional[str] = None

class AssignedCPE(BaseModel):
    mac: str
    hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- Modelos Pydantic (Servicios) ---
class ClientServiceBase(BaseModel):
    router_host: str
    service_type: str
    pppoe_username: Optional[str] = None
    router_secret_id: Optional[str] = None
    profile_name: Optional[str] = None
    suspension_method: str

class ClientServiceCreate(ClientServiceBase):
    pass

class ClientService(ClientServiceBase):
    id: int
    client_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Modelos Pydantic (Pagos) ---
class PaymentBase(BaseModel):
    monto: float
    mes_correspondiente: str # ej. "2025-11"
    metodo_pago: Optional[str] = None
    notas: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: int
    client_id: int
    fecha_pago: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Endpoints de la API (Clientes) ---
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

# --- Endpoints (Servicios) ---
@router.post("/clients/{client_id}/services", response_model=ClientService, status_code=status.HTTP_201_CREATED)
def api_create_client_service(client_id: int, service: ClientServiceCreate, current_user: User = Depends(get_current_active_user)):
    try:
        new_service = clients_db.create_client_service(client_id, service.model_dump())
        return new_service
    except ValueError as e:
        if "UNIQUE constraint failed: client_services.pppoe_username" in str(e):
            raise HTTPException(status_code=409, detail=f"El nombre de usuario PPPoE '{service.pppoe_username}' ya existe.")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/clients/{client_id}/services", response_model=List[ClientService])
def api_get_client_services(client_id: int, current_user: User = Depends(get_current_active_user)):
    return clients_db.get_services_for_client(client_id)

# --- Endpoints (Pagos) ---
@router.post("/clients/{client_id}/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
def api_register_payment_and_reactivate(client_id: int, payment: PaymentCreate, current_user: User = Depends(get_current_active_user)):
    try:
        # Usamos el billing_service que ya tenías para registrar el pago y reactivar
        new_payment = billing_service.reactivate_client_services(
            client_id=client_id, 
            payment_data=payment.model_dump()
        )
        return new_payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

@router.get("/clients/{client_id}/payments", response_model=List[Payment])
def api_get_payment_history(client_id: int, current_user: User = Depends(get_current_active_user)):
    return payments_db.get_payments_for_client(client_id)