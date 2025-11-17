# app/api/clients/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...auth import User, get_current_active_user

# --- IMPORTACIONES CORREGIDAS ---
# Importamos la CLASE BillingService, no el módulo entero
from ...services.billing_service import BillingService 
# Usamos un alias para evitar conflicto de nombres con el modelo
from ...services.client_service import ClientService as ClientManagerService

from .models import (
    Client, ClientCreate, ClientUpdate, AssignedCPE,
    ClientService, ClientServiceCreate,
    Payment, PaymentCreate
)

router = APIRouter()

# Inyector de dependencias para ClientManagerService
def get_client_service() -> ClientManagerService:
    return ClientManagerService()

# --- Endpoints de Clientes ---

@router.get("/clients", response_model=List[Client])
def api_get_all_clients(
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_all_clients()

@router.post("/clients", response_model=Client, status_code=status.HTTP_201_CREATED)
def api_create_client(
    client: ClientCreate, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        new_client = service.create_client(client.model_dump())
        return new_client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/clients/{client_id}", response_model=Client)
def api_update_client(
    client_id: int, 
    client_update: ClientUpdate, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    update_fields = client_update.model_dump(exclude_unset=True)
    try:
        updated_client = service.update_client(client_id, update_fields)
        return updated_client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client(
    client_id: int, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        service.delete_client(client_id)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/clients/{client_id}/cpes", response_model=List[AssignedCPE])
def api_get_cpes_for_client(
    client_id: int, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_cpes_for_client(client_id)

# --- Endpoints de Servicios de Red ---

@router.post("/clients/{client_id}/services", response_model=ClientService, status_code=status.HTTP_201_CREATED)
def api_create_client_service(
    client_id: int, 
    service_data: ClientServiceCreate, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        new_service = service.create_client_service(client_id, service_data.model_dump())
        return new_service
    except ValueError as e:
        if "ya existe" in str(e):
             raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/clients/{client_id}/services", response_model=List[ClientService])
def api_get_client_services(
    client_id: int, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_client_services(client_id)

# --- Endpoints de Pagos ---

@router.post("/clients/{client_id}/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
def api_register_payment_and_reactivate(
    client_id: int, 
    payment: PaymentCreate, 
    current_user: User = Depends(get_current_active_user)
):
    """
    Registra un pago y ejecuta la lógica de reactivación (si aplica).
    """
    try:
        # 1. Instanciar la clase BillingService
        billing_service = BillingService()
        
        # 2. Llamar al método de la instancia
        new_payment = billing_service.reactivate_client_services(
            client_id=client_id, 
            payment_data=payment.model_dump()
        )
        return new_payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Loguear el error real en la consola del servidor
        print(f"Error crítico en pagos: {e}") 
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

@router.get("/clients/{client_id}/payments", response_model=List[Payment])
def api_get_payment_history(
    client_id: int, 
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_payment_history(client_id)