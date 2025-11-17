# app/services/client_service.py
from typing import List, Dict, Any, Optional
from ..db import clients_db, payments_db

class ClientService:
    def __init__(self):
        pass

    def get_all_clients(self) -> List[Dict[str, Any]]:
        return clients_db.get_all_clients_with_cpe_count()

    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            new_client = clients_db.create_client(client_data)
            return new_client
        except Exception as e:
            # Re-lanzar como una excepción de negocio
            raise ValueError(f"Database error: {e}")

    def update_client(self, client_id: int, client_update: Dict[str, Any]) -> Dict[str, Any]:
        if not client_update:
            raise ValueError("No fields to update provided.")
        
        updated_client = clients_db.update_client(client_id, client_update)
        if not updated_client:
            raise FileNotFoundError("Client not found.")
        return updated_client

    def delete_client(self, client_id: int):
        deleted_rows = clients_db.delete_client(client_id)
        if deleted_rows == 0:
            raise FileNotFoundError("Client not found to delete.")

    def get_cpes_for_client(self, client_id: int) -> List[Dict[str, Any]]:
        return clients_db.get_cpes_for_client(client_id)

    # --- Métodos de Servicio ---
    def create_client_service(self, client_id: int, service_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            new_service = clients_db.create_client_service(client_id, service_data)
            return new_service
        except ValueError as e:
            if "UNIQUE constraint failed: client_services.pppoe_username" in str(e):
                raise ValueError(f"El nombre de usuario PPPoE '{service_data.get('pppoe_username')}' ya existe.")
            raise e # Re-lanza otros ValueErrors (ej. DB error)

    def get_client_services(self, client_id: int) -> List[Dict[str, Any]]:
        return clients_db.get_services_for_client(client_id)

    # --- Métodos de Pagos ---
    def get_payment_history(self, client_id: int) -> List[Dict[str, Any]]:
        return payments_db.get_payments_for_client(client_id)