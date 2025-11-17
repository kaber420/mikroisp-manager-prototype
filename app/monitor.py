# app/monitor.py
import time
import logging
import requests # Nuevo import necesario
import os       # Nuevo import necesario
from concurrent.futures import ThreadPoolExecutor

from .services.monitor_service import MonitorService
from .db.settings_db import get_setting

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Monitor] - %(threadName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

MAX_WORKERS = 10

# --- FUNCIÓN NUEVA: Notificar a la API ---
def notify_api_update():
    """
    Envía una señal HTTP a la API para que actualice los WebSockets.
    Se ejecuta al finalizar cada ciclo de escaneo.
    """
    try:
        # Leemos el puerto del entorno o usamos 8000 por defecto
        port = os.getenv("UVICORN_PORT", "8000")
        # Llamamos al endpoint interno que creamos en main.py
        url = f"http://127.0.0.1:{port}/api/internal/notify-monitor-update"
        requests.post(url, timeout=2)
    except Exception:
        # Si falla (ej. la API se está reiniciando), no detenemos el monitor
        pass

def run_monitor():
    """
    Bucle principal del monitor. Delega la lógica a MonitorService y notifica a la API.
    """
    monitor_service = MonitorService()
    logging.info("Monitor iniciado (Motor Refactorizado + Event Driven).")

    while True:
        try:
            logging.info("--- Iniciando ciclo de escaneo ---")
            devices = monitor_service.get_active_devices()
            
            aps = devices['aps']
            routers = devices['routers']
            
            if not aps and not routers:
                logging.info("No hay dispositivos para monitorear.")
            else:
                # 1. Procesar dispositivos en paralelo (Bloqueante hasta que terminen)
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    if aps:
                        executor.map(monitor_service.check_ap, aps)
                    if routers:
                        executor.map(monitor_service.check_router, routers)
                
                # 2. Notificar a la API que hay datos frescos (¡ESTO FALTABA!)
                logging.info("Ciclo terminado. Notificando a la API para actualización en tiempo real...")
                notify_api_update()

            # 3. Esperar siguiente ciclo
            interval_str = get_setting('default_monitor_interval')
            try:
                monitor_interval = int(interval_str) if interval_str and interval_str.isdigit() else 300
            except (ValueError, TypeError):
                monitor_interval = 300
            
            time.sleep(monitor_interval)
            
        except KeyboardInterrupt:
            logging.info("Monitor detenido.")
            break
        except Exception as e:
            logging.exception(f"Error en el bucle del monitor: {e}")
            time.sleep(60)