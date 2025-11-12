# app/billing_engine.py
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Importaciones de la base de datos y el nuevo servicio de router
from .db import settings_db, clients_db, payments_db
from .core.router_service import RouterService, RouterConnectionError, RouterCommandError, RouterNotProvisionedError

# Configuración del Logger para este motor
logger = logging.getLogger("BillingEngine")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [BillingEngine] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

def get_clients_to_suspend() -> List[Dict[str, Any]]:
    """
    Obtiene una lista de clientes que deben ser suspendidos.
    Lógica: Clientes 'activos' cuyo día de facturación fue ayer
    y no tienen un pago registrado para el ciclo de facturación de ayer.
    """
    clients_to_suspend = []
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        billing_day_to_check = yesterday.day
        billing_cycle = yesterday.strftime('%Y-%m')

        logger.info(f"Verificando clientes con día de pago [Día {billing_day_to_check}] para el ciclo [Mes {billing_cycle}].")

        potential_clients = clients_db.get_active_clients_by_billing_day(billing_day_to_check)
        if not potential_clients:
            logger.info(f"No se encontraron clientes activos con día de pago {billing_day_to_check}.")
            return []

        for client in potential_clients:
            client_id = client['id']
            has_paid = payments_db.check_payment_exists(client_id, billing_cycle)
            
            if not has_paid:
                logger.warning(f"¡Cliente MOROSO encontrado! ID: {client_id}, Nombre: {client['name']}")
                clients_to_suspend.append(client)
            else:
                logger.info(f"Cliente {client_id} está al día.")
        
        return clients_to_suspend

    except Exception as e:
        logger.error(f"Error crítico al obtener la lista de clientes a suspender: {e}", exc_info=True)
        return []

def suspend_client_service(service: Dict[str, Any]):
    """
    Ejecuta la lógica de suspensión para un único servicio de cliente,
    utilizando el RouterService para interactuar con el hardware.
    """
    client_id = service['client_id']
    method = service['suspension_method']
    
    logger.info(f"Ejecutando suspensión (Método: {method}) para el servicio {service['id']} del cliente {client_id}.")

    if method == 'pppoe_secret_disable':
        if not service['router_secret_id'] or not service['router_host']:
            raise ValueError(f"Datos incompletos para suspensión PPPoE (Falta secret_id o host) en el servicio {service['id']}.")

        try:
            logger.info(f"Dando orden a RouterService para suspender {service['pppoe_username']} en {service['router_host']}")
            
            # Instanciamos el servicio y le damos la orden
            router_service = RouterService(service['router_host'])
            router_service.set_pppoe_secret_status(
                secret_id=service['router_secret_id'], 
                disable=True
            )
            
            logger.info(f"¡Éxito! Servicio PPPoE (User: {service['pppoe_username']}) suspendido en {service['router_host']}.")
        
        except (ValueError, RouterConnectionError, RouterCommandError, RouterNotProvisionedError) as e:
            # Capturamos los errores limpios del servicio y los relanzamos para el bucle principal
            raise Exception(f"Fallo de RouterService al suspender en {service['router_host']}: {e}")
    
    else:
        logger.error(f"Método de suspensión '{method}' desconocido para el servicio {service['id']}.")


def run_billing_engine():
    """
    Bucle principal del motor de facturación.
    Se ejecuta una vez al día a la hora configurada.
    """
    logger.info("Motor de Facturación y Suspensión iniciado.")
    last_run_date = None

    while True:
        try:
            run_hour_str = settings_db.get_setting('suspension_run_hour') or "02:00"
            now = datetime.now()
            current_date = now.date()
            run_time_today = datetime.strptime(f"{current_date} {run_hour_str}", "%Y-%m-%d %H:%M")

            if now >= run_time_today and current_date != last_run_date:
                logger.info(f"--- INICIANDO CICLO DE SUSPENSIÓN DIARIA ({current_date}) ---")
                
                clients_to_suspend = get_clients_to_suspend()
                
                if not clients_to_suspend:
                    logger.info("No se encontraron clientes para suspender. Ciclo finalizado.")
                
                for client in clients_to_suspend:
                    client_id = client['id']
                    logger.info(f"Procesando suspensión para el Cliente ID: {client_id} (Nombre: {client['name']})")
                    
                    services = clients_db.get_services_for_client(client_id)
                    if not services:
                        logger.warning(f"El cliente {client_id} no tiene servicios de red. Marcando como suspendido igualmente.")
                        clients_db.update_client(client_id, {"service_status": "suspended"})
                        continue
                    
                    has_errors = False
                    for service in services:
                        try:
                            suspend_client_service(service)
                        except Exception as e:
                            logger.error(f"Fallo al suspender el servicio {service['id']} para el cliente {client_id}: {e}", exc_info=True)
                            has_errors = True
                    
                    if not has_errors:
                        clients_db.update_client(client_id, {"service_status": "suspended"})
                        logger.info(f"Cliente {client_id} marcado como 'suspended' en la base de datos.")
                    else:
                        logger.error(f"NO se pudo suspender uno o más servicios del cliente {client_id}. El estado NO se cambiará a 'suspended' para revisión manual.")

                logger.info("--- CICLO DE SUSPENSIÓN DIARIA FINALIZADO ---")
                last_run_date = current_date

            time.sleep(1800) # Comprobamos la hora cada 30 minutos
            
        except KeyboardInterrupt:
            logger.info("Motor de facturación detenido manualmente.")
            break
        except Exception as e:
            logger.critical(f"Error inesperado en el bucle principal del motor de facturación: {e}", exc_info=True)
            logger.critical("El motor se reiniciará en 60 segundos.")
            time.sleep(60)