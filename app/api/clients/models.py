# app/api/clients/models.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

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
    ip_address: Optional[str] = None  # <--- AGREGADO: Ahora la API puede enviar la IP
    model_config = ConfigDict(from_attributes=True)

# --- Modelos Pydantic (Servicios) ---
class ClientServiceBase(BaseModel):
    router_host: str
    service_type: str
    pppoe_username: Optional[str] = None
    router_secret_id: Optional[str] = None
    profile_name: Optional[str] = None
    plan_id: Optional[int] = None
    ip_address: Optional[str] = None
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
    mes_correspondiente: str
    metodo_pago: Optional[str] = None
    notas: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: int
    client_id: int
    fecha_pago: datetime
    model_config = ConfigDict(from_attributes=True)