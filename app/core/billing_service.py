# app/core/billing_service.py
import logging
from typing import Dict, Any, List

from ..db import payments_db, clients_db
from ..core.router_service import RouterService, RouterConnectionError, RouterCommandError

logger = logging.getLogger(__name__)

def reactivate_client_services(client_id: int, payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lógica de negocio para la reactivación instantánea.
    1. Registra el pago.
    2. Actualiza el estado del cliente a 'active'.
    3. DA LA ORDEN al RouterService de reactivar.
    """
    
    # Pasos 1 y 2 sin cambios
    new_payment = payments_db.create_payment(client_id, payment_data)
    logger.info(f"Pago registrado (ID: {new_payment['id']}) para el cliente {client_id}.")
    clients_db.update_client(client_id, {"service_status": "active"})
    logger.info(f"Estado del cliente {client_id} actualizado a 'active'.")

    # Paso 3: Reactivar servicios (Refactorizado)
    services = clients_db.get_services_for_client(client_id)
    if not services:
        logger.warning(f"El cliente {client_id} no tiene servicios de red para reactivar.")
        return new_payment

    activation_errors: List[str] = []

    for service in services:
        if service['service_type'] == 'pppoe' and service['router_secret_id']:
            try:
                logger.info(f"Dando orden a RouterService para reactivar {service['pppoe_username']} en {service['router_host']}")
                
                # ¡La magia! Instanciamos el servicio y le damos la orden.
                router_service = RouterService(service['router_host'])
                router_service.set_pppoe_secret_status(
                    secret_id=service['router_secret_id'], 
                    disable=False
                )
                
                logger.info(f"¡Éxito! RouterService reactivó {service['pppoe_username']}.")

            except (ValueError, RouterConnectionError, RouterCommandError) as e:
                error_msg = str(e)
                logger.error(f"No se pudo reactivar el servicio {service['id']} para el cliente {client_id}: {error_msg}")
                activation_errors.append(error_msg)

    if activation_errors:
        notas_actuales = new_payment.get('notas', '') or ''
        error_info = "ADVERTENCIA: El pago se registró pero falló la reactivación automática de uno o más servicios. Revisar logs."
        nuevas_notas = f"{notas_actuales}\n{error_info}".strip()
        payments_db.update_payment_notes(new_payment['id'], nuevas_notas)
    
    return new_payment