# app/billing_engine.py
import time
import logging
from datetime import datetime

from .db import settings_db
from .services.billing_service import BillingService

# Configuración del Logger
logger = logging.getLogger("BillingEngine")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [BillingEngine] - %(message)s'))
    logger.addHandler(handler)

def run_billing_engine():
    """
    Orquestador que ejecuta las suspensiones diarias utilizando BillingService.
    """
    logger.info("Motor de Facturación iniciado (Refactorizado).")
    # Instanciamos el servicio una sola vez (o dentro del loop si prefieres stateless total)
    billing_service = BillingService()
    last_run_date = None

    while True:
        try:
            run_hour_str = settings_db.get_setting('suspension_run_hour') or "02:00"
            now = datetime.now()
            current_date = now.date()
            
            # Construir la fecha/hora de ejecución para hoy
            try:
                run_time_today = datetime.strptime(f"{current_date} {run_hour_str}", "%Y-%m-%d %H:%M")
            except ValueError:
                logger.error(f"Formato de hora inválido en configuración: {run_hour_str}. Usando 02:00.")
                run_time_today = datetime.strptime(f"{current_date} 02:00", "%Y-%m-%d %H:%M")

            # Ejecutar si ya pasó la hora y no se ha ejecutado hoy
            if now >= run_time_today and current_date != last_run_date:
                logger.info(f"--- EJECUTANDO AUDITORÍA DE ESTADOS ({current_date}) ---")
                
                # Llamamos a la lógica inteligente que creaste en BillingService
                stats = billing_service.process_daily_suspensions()
                
                logger.info(f"--- FIN DEL PROCESO. Resumen: {stats} ---")
                
                last_run_date = current_date

            # Verificar la hora cada 30 minutos para no saturar el CPU
            time.sleep(1800) 
            
        except KeyboardInterrupt:
            logger.info("Motor detenido manualmente.")
            break
        except Exception as e:
            logger.critical(f"Error crítico en el motor de facturación: {e}", exc_info=True)
            time.sleep(60)