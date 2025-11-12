# app/core/router_service.py
import ssl
import logging
from typing import Dict, Any, List
from routeros_api import RouterOsApiPool
from fastapi import Depends, HTTPException, status

from ..db import router_db
from ..core import mikrotik_client

logger = logging.getLogger(__name__)

# --- Excepciones personalizadas del Servicio ---
class RouterConnectionError(Exception):
    pass
class RouterCommandError(Exception):
    pass
class RouterNotProvisionedError(Exception):
    pass

class RouterService:
    """
    Servicio para interactuar con un router específico.
    Maneja la autenticación, pool de conexiones y ejecución de comandos.
    """
    
    def __init__(self, host: str):
        self.host = host
        self.creds = router_db.get_router_by_host(host)
        
        if not self.creds:
            raise RouterConnectionError(f"Router {host} no encontrado en la DB.")
            
        if self.creds['api_port'] != self.creds['api_ssl_port']:
             raise RouterNotProvisionedError(f"Router {host} no está aprovisionado. El servicio no puede conectar.")
        
        self.pool = self._create_pool()

    def _create_pool(self) -> RouterOsApiPool:
        """Crea y devuelve un pool de conexiones SSL."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # --- LÍNEA CORREGIDA ---
        # Se ha eliminado el argumento 'timeout=15'
        return RouterOsApiPool(
            self.host,
            username=self.creds['username'],
            password=self.creds['password'],
            port=self.creds['api_ssl_port'],
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True
        )

    def _execute_command(self, func, *args, **kwargs) -> Any:
        """Wrapper para ejecutar un comando de mikrotik_client manejando la conexión."""
        api = None
        try:
            api = self.pool.get_api()
            return func(api, *args, **kwargs) 
        except Exception as e:
            logger.error(f"Error de comando en {self.host} ({func.__name__}): {e}")
            raise RouterCommandError(f"Error en {self.host}: {e}")
        finally:
            # Desconectamos el pool después de cada comando para este servicio simple
            if self.pool:
                self.pool.disconnect()

    # --- Métodos de Servicio (API Pública del Servicio) ---

    def set_pppoe_secret_status(self, secret_id: str, disable: bool):
        return self._execute_command(mikrotik_client.enable_disable_pppoe_secret, secret_id=secret_id, disable=disable)

    def get_pppoe_secrets(self, username: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(mikrotik_client.get_pppoe_secrets, username=username)

    def get_pppoe_active_connections(self, name: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(mikrotik_client.get_pppoe_active_connections, name=name)

    def create_pppoe_secret(self, **kwargs) -> Dict[str, Any]:
        return self._execute_command(mikrotik_client.create_pppoe_secret, **kwargs)

    def update_pppoe_secret(self, secret_id: str, **kwargs) -> Dict[str, Any]:
        return self._execute_command(mikrotik_client.update_pppoe_secret, secret_id, **kwargs)

    def remove_pppoe_secret(self, secret_id: str) -> None:
        return self._execute_command(mikrotik_client.remove_pppoe_secret, secret_id)

    def get_system_resources(self) -> Dict[str, Any]:
        return self._execute_command(mikrotik_client.get_system_resources)

    def create_service_plan(self, **kwargs):
        return self._execute_command(mikrotik_client.create_service_plan, **kwargs)

    def add_simple_queue(self, **kwargs):
        return self._execute_command(mikrotik_client.add_simple_queue, **kwargs)
        
    def add_ip_address(self, **kwargs):
        return self._execute_command(mikrotik_client.add_ip_address, **kwargs)

    def add_nat_masquerade(self, **kwargs):
        return self._execute_command(mikrotik_client.add_nat_masquerade, **kwargs)

    def add_pppoe_server(self, **kwargs):
        return self._execute_command(mikrotik_client.add_pppoe_server, **kwargs)

    def remove_ip_address(self, address: str):
        return self._execute_command(mikrotik_client.remove_ip_address, address=address)

    def remove_nat_rule(self, comment: str):
        return self._execute_command(mikrotik_client.remove_nat_rule, comment=comment)

    def remove_pppoe_server(self, service_name: str):
        return self._execute_command(mikrotik_client.remove_pppoe_server, service_name=service_name)

    def remove_service_plan(self, plan_name: str):
        return self._execute_command(mikrotik_client.remove_service_plan, plan_name=plan_name)
    
    def remove_simple_queue(self, queue_id: str):
        return self._execute_command(mikrotik_client.remove_simple_queue, queue_id=queue_id)

    def get_backup_files(self):
        return self._execute_command(mikrotik_client.get_backup_files)

    def create_backup(self, backup_name: str):
        return self._execute_command(mikrotik_client.create_backup, backup_name=backup_name)

    def create_export_script(self, script_name: str):
        return self._execute_command(mikrotik_client.create_export_script, script_name=script_name)

    def remove_file(self, file_id: str):
        return self._execute_command(mikrotik_client.remove_file, file_id=file_id)

    def get_router_users(self):
        return self._execute_command(mikrotik_client.get_router_users)

    def add_router_user(self, **kwargs):
        return self._execute_command(mikrotik_client.add_router_user, **kwargs)

    def remove_router_user(self, user_id: str):
        return self._execute_command(mikrotik_client.remove_router_user, user_id=user_id)

    def get_full_details(self) -> Dict[str, Any]:
        """Obtiene una vista completa de la configuración."""
        api = None
        try:
            api = self.pool.get_api()
            details = {
                "interfaces": mikrotik_client.get_interfaces(api),
                "ip_addresses": mikrotik_client.get_ip_addresses(api),
                "nat_rules": mikrotik_client.get_nat_rules(api),
                "pppoe_servers": mikrotik_client.get_pppoe_servers(api),
                "ppp_profiles": mikrotik_client.get_ppp_profiles(api),
                "simple_queues": mikrotik_client.get_simple_queues(api),
                "ip_pools": mikrotik_client.get_ip_pools(api),
            }
            return details
        except Exception as e:
            raise RouterCommandError(f"Error en {self.host} (get_full_details): {e}")
        finally:
            if self.pool:
                self.pool.disconnect()

# --- Inyector de Dependencia de FastAPI ---
def get_router_service(host: str) -> RouterService:
    """Inyector de dependencias que crea una instancia de RouterService."""
    try:
        return RouterService(host)
    except (RouterConnectionError, RouterNotProvisionedError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))