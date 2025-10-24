# monitor.py

import time
# import argparse <- Ya no es necesario
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor

from ap_client import UbiquitiClient
from database import setup_databases, get_ap_status, update_ap_status, save_full_snapshot, get_setting
from alerter import send_telegram_alert

# --- Constantes ---
MAX_WORKERS = 10

def get_enabled_aps_from_db() -> list:
    """
    Obtiene la lista de APs activos desde la base de datos de inventario.
    """
    aps_to_monitor = []
    try:
        conn = sqlite3.connect("inventory.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT host, username, password FROM aps WHERE is_enabled = TRUE")
        for row in cursor.fetchall():
            aps_to_monitor.append(dict(row))
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"No se pudo obtener la lista de APs de la base de datos: {e}")
    return aps_to_monitor

def process_ap(ap_config: dict):
    """
    Realiza el proceso completo de verificación para un solo AP.
    Esta función está diseñada para ser ejecutada en un hilo separado.
    """
    host = ap_config["host"]
    # Usamos logging.info para la salida estándar del proceso
    logging.info(f"--- Verificando AP en {host} ---")
    
    client = UbiquitiClient(
        host=host,
        username=ap_config["username"],
        password=ap_config["password"]
    )
    
    # Se ha modificado ap_client para que los errores de conexión no detengan el programa,
    # sino que se logueen internamente. get_status_data devolverá None.
    status_data = client.get_status_data()
    previous_status = get_ap_status(host)
    
    if status_data:
        current_status = 'online'
        hostname = status_data.get("host", {}).get("hostname", host)
        logging.info(f"Estado de '{hostname}' ({host}): ONLINE")
        
        save_full_snapshot(host, status_data)
        update_ap_status(host, current_status, data=status_data)
        
        if previous_status == 'offline':
            message = (f"✅ *AP RECUPERADO*\n\n"
                       f"El AP *{hostname}* (`{host}`) ha vuelto a estar en línea.")
            send_telegram_alert(message)
    else:
        current_status = 'offline'
        logging.warning(f"Estado de {host}: OFFLINE")
        
        update_ap_status(host, current_status)
        
        if previous_status != 'offline':
            # Para el mensaje de AP caído, obtenemos el hostname de la base de datos si es posible
            conn = sqlite3.connect("inventory.sqlite")
            cursor = conn.execute("SELECT hostname FROM aps WHERE host = ?", (host,))
            row = cursor.fetchone()
            conn.close()
            hostname = row[0] if row and row[0] else host
            
            message = (f"❌ *ALERTA: AP CAÍDO*\n\n"
                       f"No se pudo establecer conexión con el AP *{hostname}* (`{host}`).")
            send_telegram_alert(message)

def main_loop():
    """
    Bucle principal que obtiene la lista de APs y utiliza un ThreadPoolExecutor
    para procesarlos en paralelo.
    """
    logging.info("Iniciando nuevo ciclo de monitoreo...")
    
    aps_to_check = get_enabled_aps_from_db()
    if not aps_to_check:
        logging.warning("No se encontraron APs activos en la base de datos para monitorear.")
        return

    logging.info(f"Se encontraron {len(aps_to_check)} APs activos. Procesando en paralelo (hasta {MAX_WORKERS} a la vez)...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_ap, aps_to_check)

def run_monitor():
    """
    Función que envuelve el bucle infinito para el monitoreo continuo.
    Esta es la función que será llamada por el lanzador principal.
    """
    # --- MODIFICACIÓN IMPORTANTE ---
    # La configuración del logging se realiza aquí para asegurar que este
    # proceso tenga su propia configuración de logging cuando es lanzado.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [Monitor] - %(threadName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.info("Iniciando sistema de monitoreo de APs...")
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
            # Esta interrupción ahora será manejada por main.py, pero la dejamos por si acaso
            logging.info("Señal de interrupción recibida en el proceso de monitoreo.")
            break
        except Exception as e:
            logging.exception(f"Ocurrió un error inesperado en el bucle principal: {e}")
            logging.info("El sistema intentará continuar después de una breve pausa.")
            time.sleep(60)

# --- BLOQUE ELIMINADO ---
# El bloque `if __name__ == "__main__":` ha sido eliminado.
# La ejecución ahora es manejada exclusivamente por `main.py`.