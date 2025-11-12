# app/monitor.py

import time
import logging
from concurrent.futures import ThreadPoolExecutor

# --- IMPORTACIONES MODULARIZADAS ---
from .core.ap_client import UbiquitiClient
# ¡Importamos el nuevo servicio y sus errores!
from .core.router_service import RouterService, RouterConnectionError, RouterCommandError, RouterNotProvisionedError
from .core.alerter import send_telegram_alert

from .db.settings_db import get_setting
from .db.aps_db import get_ap_status, update_ap_status, get_enabled_aps_for_monitor, get_ap_by_host_with_stats
from .db.stats_db import save_full_snapshot
from .db.router_db import get_router_status, update_router_status, get_enabled_routers_from_db, get_router_by_host

# --- Constantes ---
MAX_WORKERS = 10

# --- FUNCIÓN REFACTORIZADA ---
def process_router(router_config: dict):
    """
    Verifica un solo Router MikroTik utilizando el RouterService para consistencia.
    """
    host = router_config["host"]
    logging.info(f"--- Verificando Router en {host} ---")
    
    status_data = None
    try:
        # Usamos nuestro nuevo servicio centralizado
        router_service = RouterService(host)
        status_data = router_service.get_system_resources()
        
    except (RouterConnectionError, RouterCommandError, RouterNotProvisionedError) as e:
        logging.warning(f"No se pudo obtener el estado del Router {host}: {e}")
        status_data = None
    
    # --- El resto de la lógica no cambia ---
    previous_status = get_router_status(host)
    
    if status_data:
        current_status = 'online'
        hostname = status_data.get("name", host)
        logging.info(f"Estado de Router '{hostname}' ({host}): ONLINE")
        
        # El servicio ya actualiza la DB, pero lo hacemos de nuevo
        # para asegurarnos de que el 'last_status' y 'last_checked' queden registrados
        update_router_status(host, current_status, data=status_data)
        
        if previous_status == 'offline':
            message = f"✅ *ROUTER RECUPERADO*\n\nEl Router *{hostname}* (`{host}`) ha vuelto a estar en línea."
            send_telegram_alert(message)
    else:
        current_status = 'offline'
        logging.warning(f"Estado de Router {host}: OFFLINE")
        
        update_router_status(host, current_status)
        
        if previous_status != 'offline':
            router_info = get_router_by_host(host)
            hostname = router_info.get('hostname') if (router_info and router_info.get('hostname')) else host
            
            message = f"❌ *ALERTA: ROUTER CAÍDO*\n\nNo se pudo establecer conexión API-SSL con el Router *{hostname}* (`{host}`)."
            send_telegram_alert(message)


def process_ap(ap_config: dict):
    """
    Realiza el proceso completo de verificación para un solo AP.
    (Esta función no cambia)
    """
    host = ap_config["host"]
    logging.info(f"--- Verificando AP en {host} ---")
    
    client = UbiquitiClient(
        host=host,
        username=ap_config["username"],
        password=ap_config["password"]
    )
    
    status_data = client.get_status_data()
    previous_status = get_ap_status(host)
    
    if status_data:
        current_status = 'online'
        hostname = status_data.get("host", {}).get("hostname", host)
        logging.info(f"Estado de '{hostname}' ({host}): ONLINE")
        
        save_full_snapshot(host, status_data)
        update_ap_status(host, current_status, data=status_data)
        
        if previous_status == 'offline':
            message = f"✅ *AP RECUPERADO*\n\nEl AP *{hostname}* (`{host}`) ha vuelto a estar en línea."
            send_telegram_alert(message)
    else:
        current_status = 'offline'
        logging.warning(f"Estado de {host}: OFFLINE")
        
        update_ap_status(host, current_status)
        
        if previous_status != 'offline':
            ap_info = get_ap_by_host_with_stats(host)
            hostname = ap_info.get('hostname') if (ap_info and ap_info.get('hostname')) else host
            
            message = f"❌ *ALERTA: AP CAÍDO*\n\nNo se pudo establecer conexión con el AP *{hostname}* (`{host}`)."
            send_telegram_alert(message)

def main_loop():
    """Bucle principal que obtiene la lista de APs y Routers y los procesa."""
    logging.info("Iniciando nuevo ciclo de monitoreo...")
    
    aps_to_check = get_enabled_aps_for_monitor()
    routers_to_check = get_enabled_routers_from_db()
    
    if not aps_to_check and not routers_to_check:
        logging.warning("No se encontraron dispositivos (APs o Routers) activos para monitorear.")
        return

    logging.info(f"Se encontraron {len(aps_to_check)} APs y {len(routers_to_check)} Routers activos. Procesando en paralelo...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        if aps_to_check:
            executor.map(process_ap, aps_to_check)
        if routers_to_check:
            executor.map(process_router, routers_to_check)

def run_monitor():
    """Función que envuelve el bucle infinito para el monitoreo continuo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [Monitor] - %(threadName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.info("Iniciando sistema de monitoreo (APs y Routers)...")
    while True:
        try:
            main_loop()

            interval_str = get_setting('default_monitor_interval')
            try:
                monitor_interval = int(interval_str) if interval_str and interval_str.isdigit() else 300
            except (ValueError, TypeError):
                monitor_interval = 300
            
            logging.info(f"Ciclo de monitoreo completado. Esperando {monitor_interval} segundos...")
            time.sleep(monitor_interval)
            
        except KeyboardInterrupt:
            logging.info("Señal de interrupción recibida en el proceso de monitoreo.")
            break
        except Exception as e:
            logging.exception(f"Ocurrió un error inesperado en el bucle principal: {e}")
            logging.info("El sistema intentará continuar después de una breve pausa.")
            time.sleep(60)