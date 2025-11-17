# app/services/billing_service.py
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..db import payments_db, clients_db, settings_db
from .router_service import RouterService

logger = logging.getLogger(__name__)

class BillingService:
    
    def reactivate_client_services(self, client_id: int, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra un pago y, SI ES NECESARIO, reactiva el servicio en el router.
        """
        # 1. Obtener estado actual del cliente
        client = clients_db.get_client_by_id(client_id)
        if not client:
            raise ValueError(f"Cliente {client_id} no encontrado.")
            
        previous_status = client.get('service_status')

        # 2. Registrar el pago (Siempre se hace)
        new_payment = payments_db.create_payment(client_id, payment_data)
        logger.info(f"Pago registrado (ID: {new_payment['id']}) para el cliente {client_id}.")
        
        # 3. Actualizar estado a 'active' en BD (Siempre se hace)
        clients_db.update_client(client_id, {"service_status": "active"})
        
        # 4. Reactivación TÉCNICA (Solo si estaba suspendido o cancelado)
        # Si estaba 'pendiente' o 'active', ya tiene internet, no tocamos el router.
        if previous_status in ['suspended', 'cancelled']:
            logger.info(f"El cliente estaba '{previous_status}'. Iniciando reactivación técnica en router...")
            services = clients_db.get_services_for_client(client_id)
            
            activation_errors = []
            if services:
                for service in services:
                    if service['service_type'] == 'pppoe' and service['router_secret_id']:
                        try:
                            # Instanciamos el RouterService
                            router_service = RouterService(service['router_host'])
                            router_service.set_pppoe_secret_status(
                                secret_id=service['router_secret_id'], 
                                disable=False
                            )
                            logger.info(f"Servicio PPPoE reactivado para {service['pppoe_username']}")
                        except Exception as e:
                            logger.error(f"Error reactivando servicio {service['id']}: {e}")
                            activation_errors.append(str(e))
            
            if activation_errors:
                # Dejar nota en el pago si hubo error técnico
                notas = new_payment.get('notas', '') or ''
                payments_db.update_payment_notes(new_payment['id'], f"{notas}\nWARN: Fallo reactivación técnica.".strip())
        else:
            logger.info(f"El cliente estaba '{previous_status}'. No se requiere acción en el router.")

        return new_payment

    def process_daily_suspensions(self) -> Dict[str, int]:
        """
        Revisa a TODOS los clientes y actualiza su estado (Active/Pendiente/Suspended).
        """
        logger.info("Iniciando auditoría de estados de facturación...")
        
        try:
            days_before = int(settings_db.get_setting('days_before_due') or 5)
        except ValueError:
            days_before = 5

        today = datetime.now().date()
        all_clients = clients_db.get_all_clients_with_cpe_count()
        stats = {"active": 0, "pendiente": 0, "suspended": 0, "processed": 0}

        for client in all_clients:
            if client['service_status'] == 'cancelled':
                continue
            
            cid = client['id']
            billing_day = client['billing_day']
            
            if not billing_day: 
                continue

            try:
                due_date = today.replace(day=billing_day)
            except ValueError:
                due_date = today.replace(day=28)

            # El ciclo de cobro suele ser "el mes actual" para servicios recurrentes
            cycle_str = due_date.strftime('%Y-%m')
            has_paid = payments_db.check_payment_exists(cid, cycle_str)
            
            new_status = client['service_status']
            should_suspend_technically = False

            if has_paid:
                if new_status != 'active':
                    new_status = 'active'
                    # Si pagó, reactivamos técnicamente por si acaso estaba cortado
                    # (Aunque reactivate_client_services ya lo hace al recibir el pago, esto es un "double check" nocturno)
                    self._ensure_service_enabled(cid)
            else:
                # Calcular diferencia de días
                days_diff = (due_date - today).days
                
                if days_diff < 0: 
                    # Se pasó la fecha -> SUSPENDER
                    if new_status != 'suspended':
                        new_status = 'suspended'
                        should_suspend_technically = True
                
                elif days_diff <= days_before:
                    # Faltan X días -> PENDIENTE
                    if new_status != 'suspended': 
                        new_status = 'pendiente'
                
                else:
                    # Faltan muchos días -> ACTIVO (asumiendo ciclo anterior ok)
                    if new_status == 'pendiente':
                        new_status = 'active'

            if new_status != client['service_status']:
                clients_db.update_client(cid, {"service_status": new_status})
                if should_suspend_technically:
                    self._suspend_technically(cid)

            stats[new_status] = stats.get(new_status, 0) + 1
            stats['processed'] += 1

        return stats

    def _suspend_technically(self, client_id: int):
        """Helper para suspender todos los servicios de un cliente."""
        services = clients_db.get_services_for_client(client_id)
        for service in services:
            try:
                if service['suspension_method'] == 'pppoe_secret_disable':
                    RouterService(service['router_host']).set_pppoe_secret_status(
                        secret_id=service['router_secret_id'], disable=True
                    )
            except Exception as e:
                logger.error(f"Error suspendiendo servicio {service['id']}: {e}")

    def _ensure_service_enabled(self, client_id: int):
        """Helper para asegurar que el servicio esté activo (útil para el barrido nocturno)."""
        services = clients_db.get_services_for_client(client_id)
        for service in services:
            try:
                if service['service_type'] == 'pppoe' and service['router_secret_id']:
                    # Solo activamos si no está activo, pero RouterOS maneja la idempotencia bien
                    RouterService(service['router_host']).set_pppoe_secret_status(
                        secret_id=service['router_secret_id'], disable=False
                    )
            except Exception as e:
                logger.error(f"Error asegurando servicio activo {service['id']}: {e}")