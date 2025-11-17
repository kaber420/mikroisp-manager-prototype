# app/services/monitor_service.py
import logging
from typing import Dict, Any

from ..utils.device_clients.ap_client import UbiquitiClient
from ..services.router_service import RouterService, RouterConnectionError, RouterCommandError, RouterNotProvisionedError
from ..utils.alerter import send_telegram_alert
from ..db.aps_db import get_ap_status, update_ap_status, get_ap_by_host_with_stats, get_enabled_aps_for_monitor
from ..db.router_db import get_router_status, update_router_status, get_enabled_routers_from_db, get_router_by_host
from ..db.stats_db import save_full_snapshot

logger = logging.getLogger(__name__)

class MonitorService:
    
    def get_active_devices(self):
        """Recupera todos los dispositivos habilitados para monitorear."""
        return {
            "aps": get_enabled_aps_for_monitor(),
            "routers": get_enabled_routers_from_db()
        }

    def check_ap(self, ap_config: Dict[str, Any]):
        """Verifica el estado de un AP, guarda estadísticas y envía alertas si cambia."""
        host = ap_config["host"]
        logger.info(f"--- Verificando AP en {host} ---")
        
        try:
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
                logger.info(f"Estado de '{hostname}' ({host}): ONLINE")
                
                save_full_snapshot(host, status_data)
                update_ap_status(host, current_status, data=status_data)
                
                if previous_status == 'offline':
                    message = f"✅ *AP RECUPERADO*\n\nEl AP *{hostname}* (`{host}`) ha vuelto a estar en línea."
                    send_telegram_alert(message)
            else:
                self._handle_offline_ap(host, previous_status)

        except Exception as e:
            logger.error(f"Error procesando AP {host}: {e}")
            # Asumimos offline si falla drásticamente la conexión
            self._handle_offline_ap(host, get_ap_status(host))

    def _handle_offline_ap(self, host: str, previous_status: str):
        logger.warning(f"Estado de {host}: OFFLINE")
        update_ap_status(host, 'offline')
        
        if previous_status != 'offline':
            ap_info = get_ap_by_host_with_stats(host)
            hostname = ap_info.get('hostname') if (ap_info and ap_info.get('hostname')) else host
            message = f"❌ *ALERTA: AP CAÍDO*\n\nNo se pudo establecer conexión con el AP *{hostname}* (`{host}`)."
            send_telegram_alert(message)

    def check_router(self, router_config: Dict[str, Any]):
        """Verifica el estado de un Router, actualiza recursos y envía alertas."""
        host = router_config["host"]
        logger.info(f"--- Verificando Router en {host} ---")
        
        status_data = None
        try:
            router_service = RouterService(host)
            status_data = router_service.get_system_resources()
            
        except (RouterConnectionError, RouterCommandError, RouterNotProvisionedError) as e:
            logger.warning(f"No se pudo obtener el estado del Router {host}: {e}")
            status_data = None
        except Exception as e:
            logger.error(f"Error inesperado en Router {host}: {e}")
            status_data = None
        
        previous_status = get_router_status(host)
        
        if status_data:
            current_status = 'online'
            hostname = status_data.get("name", host)
            logger.info(f"Estado de Router '{hostname}' ({host}): ONLINE")
            
            update_router_status(host, current_status, data=status_data)
            
            if previous_status == 'offline':
                message = f"✅ *ROUTER RECUPERADO*\n\nEl Router *{hostname}* (`{host}`) ha vuelto a estar en línea."
                send_telegram_alert(message)
        else:
            current_status = 'offline'
            logger.warning(f"Estado de Router {host}: OFFLINE")
            
            update_router_status(host, current_status)
            
            if previous_status != 'offline':
                router_info = get_router_by_host(host)
                hostname = router_info.get('hostname') if (router_info and router_info.get('hostname')) else host
                
                message = f"❌ *ALERTA: ROUTER CAÍDO*\n\nNo se pudo establecer conexión API-SSL con el Router *{hostname}* (`{host}`)."
                send_telegram_alert(message)