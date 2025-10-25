# monitor.py - Versión Optimizada

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime

from ap_client import UbiquitiClient
from database import (
    inventory_pool,
    get_ap_status, 
    update_ap_status, 
    save_full_snapshot, 
    get_setting
)
from alerter import send_telegram_alert

# --- Constantes ---
MAX_WORKERS = 10
DEFAULT_MONITOR_INTERVAL = 300  # 5 minutos
ERROR_RETRY_DELAY = 60  # 1 minuto en caso de error

# Logger específico del módulo
logger = logging.getLogger(__name__)


class APMonitor:
    """
    Clase que encapsula la lógica de monitoreo de APs.
    Mejora la organización y facilita el testing.
    """
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self.stats = {
            "total_checked": 0,
            "online": 0,
            "offline": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def get_enabled_aps_from_db(self) -> List[Dict[str, str]]:
        """
        Obtiene la lista de APs activos desde la base de datos de inventario.
        Versión optimizada usando el connection pool.
        """
        aps_to_monitor = []
        
        try:
            with inventory_pool.get_connection() as conn:
                # Query optimizada con índice en is_enabled
                cursor = conn.execute(
                    """SELECT host, username, password, hostname 
                       FROM aps 
                       WHERE is_enabled = TRUE 
                       ORDER BY host"""
                )
                aps_to_monitor = [dict(row) for row in cursor.fetchall()]
                
            logger.info(f"✓ Obtenidos {len(aps_to_monitor)} APs activos para monitorear")
            
        except Exception as e:
            logger.error(f"❌ Error al obtener lista de APs: {e}", exc_info=True)
        
        return aps_to_monitor
    
    def process_ap(self, ap_config: Dict[str, str]) -> Dict[str, any]:
        """
        Realiza el proceso completo de verificación para un solo AP.
        Retorna un diccionario con el resultado del procesamiento.
        """
        host = ap_config["host"]
        hostname = ap_config.get("hostname") or host
        
        result = {
            "host": host,
            "hostname": hostname,
            "status": None,
            "previous_status": None,
            "success": False,
            "error": None,
            "processing_time": 0
        }
        
        start_time = time.time()
        
        try:
            logger.debug(f"Verificando AP {hostname} ({host})...")
            
            # Crear cliente para el AP
            client = UbiquitiClient(
                host=host,
                username=ap_config["username"],
                password=ap_config["password"]
            )
            
            # Obtener datos del AP
            status_data = client.get_status_data()
            previous_status = get_ap_status(host)
            
            result["previous_status"] = previous_status
            
            if status_data:
                # AP está ONLINE
                current_status = 'online'
                result["status"] = current_status
                result["success"] = True
                
                # Actualizar hostname si cambió
                api_hostname = status_data.get("host", {}).get("hostname", hostname)
                if api_hostname != hostname:
                    hostname = api_hostname
                    result["hostname"] = hostname
                
                logger.info(f"✓ {hostname} ({host}): ONLINE")
                
                # Guardar snapshot de datos
                save_full_snapshot(host, status_data)
                
                # Actualizar status en la base de datos
                update_ap_status(host, current_status, data=status_data)
                
                # Enviar alerta de recuperación si estaba offline
                if previous_status == 'offline':
                    self._send_recovery_alert(hostname, host)
                
            else:
                # AP está OFFLINE
                current_status = 'offline'
                result["status"] = current_status
                result["success"] = True  # El proceso fue exitoso, aunque el AP esté offline
                
                logger.warning(f"⚠️  {hostname} ({host}): OFFLINE")
                
                # Actualizar status en la base de datos
                update_ap_status(host, current_status)
                
                # Enviar alerta de caída si estaba online
                if previous_status != 'offline':
                    self._send_down_alert(hostname, host)
        
        except Exception as e:
            # Error durante el procesamiento
            result["error"] = str(e)
            logger.error(f"❌ Error procesando {hostname} ({host}): {e}")
        
        finally:
            result["processing_time"] = time.time() - start_time
        
        return result
    
    def _send_recovery_alert(self, hostname: str, host: str):
        """Envía una alerta de recuperación de AP."""
        try:
            message = (
                f"✅ *AP RECUPERADO*\n\n"
                f"El AP *{hostname}* (`{host}`) ha vuelto a estar en línea.\n"
                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram_alert(message)
            logger.info(f"📤 Alerta de recuperación enviada para {hostname}")
        except Exception as e:
            logger.error(f"Error enviando alerta de recuperación: {e}")
    
    def _send_down_alert(self, hostname: str, host: str):
        """Envía una alerta de caída de AP."""
        try:
            message = (
                f"❌ *ALERTA: AP CAÍDO*\n\n"
                f"No se pudo establecer conexión con el AP *{hostname}* (`{host}`).\n"
                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram_alert(message)
            logger.info(f"📤 Alerta de caída enviada para {hostname}")
        except Exception as e:
            logger.error(f"Error enviando alerta de caída: {e}")
    
    def _update_stats(self, result: Dict[str, any]):
        """Actualiza las estadísticas del ciclo de monitoreo."""
        self.stats["total_checked"] += 1
        
        if result["success"]:
            if result["status"] == 'online':
                self.stats["online"] += 1
            elif result["status"] == 'offline':
                self.stats["offline"] += 1
        else:
            self.stats["errors"] += 1
    
    def run_monitoring_cycle(self):
        """
        Ejecuta un ciclo completo de monitoreo de todos los APs activos.
        Versión optimizada con procesamiento paralelo y estadísticas.
        """
        logger.info("=" * 70)
        logger.info("🔄 INICIANDO NUEVO CICLO DE MONITOREO")
        logger.info("=" * 70)
        
        # Resetear estadísticas
        self.stats = {
            "total_checked": 0,
            "online": 0,
            "offline": 0,
            "errors": 0,
            "start_time": time.time(),
            "end_time": None
        }
        
        # Obtener lista de APs
        aps_to_check = self.get_enabled_aps_from_db()
        
        if not aps_to_check:
            logger.warning("⚠️  No se encontraron APs activos para monitorear")
            return
        
        logger.info(f"📡 Procesando {len(aps_to_check)} APs (max {self.max_workers} paralelos)...")
        
        # Procesar APs en paralelo usando ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar todas las tareas
            future_to_ap = {
                executor.submit(self.process_ap, ap): ap 
                for ap in aps_to_check
            }
            
            # Procesar resultados a medida que se completan
            for future in as_completed(future_to_ap):
                ap = future_to_ap[future]
                try:
                    result = future.result()
                    self._update_stats(result)
                except Exception as e:
                    logger.error(f"❌ Excepción inesperada procesando {ap['host']}: {e}")
                    self.stats["errors"] += 1
        
        # Finalizar estadísticas
        self.stats["end_time"] = time.time()
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        # Mostrar resumen
        logger.info("=" * 70)
        logger.info("📊 RESUMEN DEL CICLO DE MONITOREO")
        logger.info("-" * 70)
        logger.info(f"  Total verificados: {self.stats['total_checked']}")
        logger.info(f"  ✓ Online:          {self.stats['online']}")
        logger.info(f"  ⚠ Offline:         {self.stats['offline']}")
        logger.info(f"  ❌ Errores:        {self.stats['errors']}")
        logger.info(f"  ⏱️  Duración:       {duration:.2f} segundos")
        
        if self.stats['total_checked'] > 0:
            avg_time = duration / self.stats['total_checked']
            logger.info(f"  📈 Promedio/AP:    {avg_time:.2f} segundos")
        
        logger.info("=" * 70)
    
    def get_monitor_interval(self) -> int:
        """
        Obtiene el intervalo de monitoreo desde la configuración.
        Versión optimizada con cache implícito de get_setting().
        """
        try:
            interval_str = get_setting('default_monitor_interval')
            if interval_str and interval_str.isdigit():
                interval = int(interval_str)
                if interval > 0:
                    return interval
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️  Error obteniendo intervalo de monitoreo: {e}")
        
        logger.info(f"ℹ️  Usando intervalo por defecto: {DEFAULT_MONITOR_INTERVAL}s")
        return DEFAULT_MONITOR_INTERVAL


def run_monitor():
    """
    Función principal que ejecuta el bucle infinito de monitoreo.
    Esta función es llamada por main.py como proceso separado.
    """
    # Configurar logging para el proceso de monitoreo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [Monitor] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger.info("=" * 70)
    logger.info("🚀 SISTEMA DE MONITOREO DE APs INICIADO")
    logger.info("   (Pools con inicialización lazy automática)")
    logger.info("=" * 70)
    
    # Crear instancia del monitor (los pools se inicializan automáticamente al usarse)
    monitor = APMonitor(max_workers=MAX_WORKERS)
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            logger.info(f"\n🔢 Ciclo #{cycle_count}")
            
            # Ejecutar ciclo de monitoreo
            monitor.run_monitoring_cycle()
            
            # Obtener intervalo para el siguiente ciclo
            interval = monitor.get_monitor_interval()
            
            # Calcular tiempo hasta el próximo ciclo
            next_cycle_time = datetime.now().timestamp() + interval
            next_cycle_str = datetime.fromtimestamp(next_cycle_time).strftime('%H:%M:%S')
            
            logger.info(f"⏸️  Esperando {interval}s hasta el próximo ciclo (aprox. {next_cycle_str})...\n")
            time.sleep(interval)
        
        except KeyboardInterrupt:
            # Interrupción manual (manejada por main.py normalmente)
            logger.info("\n✋ Señal de interrupción recibida en el monitor")
            break
        
        except Exception as e:
            # Error inesperado - registrar y continuar después de una pausa
            logger.exception(f"❌ ERROR CRÍTICO en el bucle de monitoreo: {e}")
            logger.warning(f"⏸️  Pausando {ERROR_RETRY_DELAY}s antes de reintentar...")
            time.sleep(ERROR_RETRY_DELAY)
    
    logger.info("=" * 70)
    logger.info("🛑 SISTEMA DE MONITOREO DETENIDO")
    logger.info("=" * 70)


# --- Punto de entrada para testing ---
if __name__ == "__main__":
    """
    Permite ejecutar el monitor directamente para pruebas.
    En producción, se ejecuta desde main.py.
    """
    print("⚠️  MODO DE PRUEBA - Ejecutando monitor directamente")
    print("    En producción, usar: python main.py")
    print()
    
    from database import setup_databases, init_connection_pools
    
    # Configurar bases de datos y pools
    setup_databases()
    init_connection_pools()
    
    # Ejecutar monitor
    run_monitor()