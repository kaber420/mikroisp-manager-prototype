# app/services/client_service.py
from typing import List, Dict, Any, Optional
from ..db import clients_db, payments_db, plans_db
from ..services.router_service import get_router_service

class ClientService:
    def __init__(self):
        pass

    def get_all_clients(self) -> List[Dict[str, Any]]:
        return clients_db.get_all_clients_with_cpe_count()

    def get_client_by_id(self, client_id: int) -> Dict[str, Any]:
        """Obtiene un cliente específico por su ID."""
        client = clients_db.get_client_by_id(client_id)
        if not client:
            raise FileNotFoundError(f"Client {client_id} not found.")
        return client

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
            
            # Aplicar configuración en el router si es necesario
            if service_data.get('service_type') == 'simple_queue':
                self._apply_simple_queue_on_router(new_service, service_data)
                
            return new_service
        except ValueError as e:
            if "UNIQUE constraint failed: client_services.pppoe_username" in str(e):
                raise ValueError(f"El nombre de usuario PPPoE '{service_data.get('pppoe_username')}' ya existe.")
            raise e # Re-lanza otros ValueErrors (ej. DB error)

    def _apply_simple_queue_on_router(self, service_db_obj: Dict[str, Any], service_input: Dict[str, Any]):
        # A. Obtener el plan desde la DB
        plan_id = service_input.get('plan_id')
        if not plan_id:
            raise ValueError("Se requiere un plan_id para servicios de cola simple")
        
        plan = plans_db.get_plan_by_id(plan_id)
        if not plan:
             raise ValueError(f"Plan con ID {plan_id} no encontrado.")

        # B. Validar IP
        target_ip = service_input.get('ip_address')
        if not target_ip:
             raise ValueError("Se requiere una dirección IP (target) para servicios de cola simple")

        # C. Conectar al Router
        router_host = service_input['router_host']
        # Asumimos que get_router_service maneja la conexión y errores
        router_service = get_router_service(router_host)
        
        # D. Crear la Cola Simple
        # Usamos un nombre descriptivo único
        queue_name = f"cli_{service_db_obj['client_id']}_srv_{service_db_obj['id']}"
        
        router_service.add_simple_queue(
            name=queue_name,
            target=target_ip,
            max_limit=plan['max_limit'],
            parent=plan.get('parent_queue'),
            comment=f"Service {service_db_obj['id']} - Plan {plan['name']}"
        )

    def get_client_services(self, client_id: int) -> List[Dict[str, Any]]:
        return clients_db.get_services_for_client(client_id)

    # --- Métodos de Pagos ---
    def get_payment_history(self, client_id: int) -> List[Dict[str, Any]]:
        return payments_db.get_payments_for_client(client_id)