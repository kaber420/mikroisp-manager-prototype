# app/services/router_service.py
import ssl
import logging
from typing import Dict, Any, List
from routeros_api import RouterOsApiPool
from fastapi import HTTPException, status

from ..db import router_db
# --- IMPORTACIONES ACTUALIZADAS ---
from ..utils.device_clients.mikrotik import system, ip, firewall, queues, ppp
from ..utils.device_clients.mikrotik.interfaces import MikrotikInterfaceManager

logger = logging.getLogger(__name__)

class RouterConnectionError(Exception): pass
class RouterCommandError(Exception): pass
class RouterNotProvisionedError(Exception): pass

class RouterService:
    """
    Servicio para interactuar con un router específico.
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
        """Wrapper para ejecutar un comando de los módulos mikrotik manejando la conexión."""
        api = None
        try:
            api = self.pool.get_api()
            return func(api, *args, **kwargs) 
        except Exception as e:
            logger.error(f"Error de comando en {self.host} ({func.__name__}): {e}")
            raise RouterCommandError(f"Error en {self.host}: {e}")
        finally:
            if self.pool:
                self.pool.disconnect()

    # --- MÉTODOS DELEGADOS A LOS NUEVOS MÓDULOS ---

    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        try:
            return manager.add_vlan(name, vlan_id, interface, comment)
        finally:
            self.pool.disconnect()

    def update_vlan(self, vlan_id: str, name: str, new_vlan_id: str, interface: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        try:
            return manager.update_vlan(vlan_id, name, new_vlan_id, interface)
        finally:
            self.pool.disconnect()

    def add_bridge(self, name: str, ports: List[str], comment: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        try:
            bridge = manager.add_bridge(name, comment)
            manager.set_bridge_ports(name, ports)
            return bridge
        finally:
            self.pool.disconnect()

    def update_bridge(self, bridge_id: str, name: str, ports: List[str]):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        try:
            bridge = manager.update_bridge(bridge_id, name)
            manager.set_bridge_ports(name, ports)
            return bridge
        finally:
            self.pool.disconnect()

    def set_pppoe_secret_status(self, secret_id: str, disable: bool):
        return self._execute_command(ppp.enable_disable_pppoe_secret, secret_id=secret_id, disable=disable)

    def get_pppoe_secrets(self, username: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(ppp.get_pppoe_secrets, username=username)

    def get_ppp_profiles(self) -> List[Dict[str, Any]]:
        """Obtiene solo la lista de perfiles PPP."""
        return self._execute_command(ppp.get_ppp_profiles)

    def get_pppoe_active_connections(self, name: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(ppp.get_pppoe_active_connections, name=name)

    def create_pppoe_secret(self, **kwargs) -> Dict[str, Any]:
        return self._execute_command(ppp.create_pppoe_secret, **kwargs)

    def update_pppoe_secret(self, secret_id: str, **kwargs) -> Dict[str, Any]:
        return self._execute_command(ppp.update_pppoe_secret, secret_id, **kwargs)

    def remove_pppoe_secret(self, secret_id: str) -> None:
        return self._execute_command(ppp.remove_pppoe_secret, secret_id)

    def get_system_resources(self) -> Dict[str, Any]:
        return self._execute_command(system.get_system_resources)

    def create_service_plan(self, **kwargs):
        return self._execute_command(ppp.create_service_plan, **kwargs)

    def add_simple_queue(self, **kwargs):
        return self._execute_command(queues.add_simple_queue, **kwargs)
        
    def add_ip_address(self, address: str, interface: str, comment: str):
        return self._execute_command(ip.add_ip_address, address=address, interface=interface, comment=comment)

    def add_nat_masquerade(self, **kwargs):
        return self._execute_command(firewall.add_nat_masquerade, **kwargs)

    def add_pppoe_server(self, **kwargs):
        return self._execute_command(ppp.add_pppoe_server, **kwargs)

    def remove_ip_address(self, address: str):
        return self._execute_command(ip.remove_ip_address, address=address)

    def remove_nat_rule(self, comment: str):
        return self._execute_command(firewall.remove_nat_rule, comment=comment)

    def remove_pppoe_server(self, service_name: str):
        return self._execute_command(ppp.remove_pppoe_server, service_name=service_name)

    def remove_service_plan(self, plan_name: str):
        return self._execute_command(ppp.remove_service_plan, plan_name=plan_name)
    
    def remove_simple_queue(self, queue_id: str):
        return self._execute_command(queues.remove_simple_queue, queue_id=queue_id)

    def get_backup_files(self):
        return self._execute_command(system.get_backup_files)

    def create_backup(self, backup_name: str):
        return self._execute_command(system.create_backup, backup_name=backup_name)

    def create_export_script(self, script_name: str):
        return self._execute_command(system.create_export_script, script_name=script_name)

    def remove_file(self, file_id: str):
        return self._execute_command(system.remove_file, file_id=file_id)

    def get_router_users(self):
        return self._execute_command(system.get_router_users)

    def add_router_user(self, **kwargs):
        return self._execute_command(system.add_router_user, **kwargs)

    def remove_router_user(self, user_id: str):
        return self._execute_command(system.remove_router_user, user_id=user_id)

    # --- ¡MÉTODOS MODIFICADOS AQUÍ! ---

    def set_interface_status(self, interface_id: str, disabled: bool, interface_type: str): # <-- AÑADIDO
        """Habilita o deshabilita una interfaz."""
        return self._execute_command(system.set_interface_status,
                                     interface_id=interface_id,
                                     disabled=disabled,
                                     interface_type=interface_type) # <-- AÑADIDO
    
    def remove_interface(self, interface_id: str, interface_type: str): # <-- AÑADIDO
        """Elimina una interfaz."""
        return self._execute_command(system.remove_interface,
                                     interface_id=interface_id,
                                     interface_type=interface_type) # <-- AÑADIDO

    # --- FIN DE MÉTODOS MODIFICADOS ---

    def get_full_details(self) -> Dict[str, Any]:
        """Obtiene una vista completa de la configuración."""
        api = None
        try:
            api = self.pool.get_api()
            interface_manager = MikrotikInterfaceManager(api)
            details = {
                "interfaces": system.get_interfaces(api),
                "ip_addresses": ip.get_ip_addresses(api),
                "nat_rules": firewall.get_nat_rules(api),
                "pppoe_servers": ppp.get_pppoe_servers(api),
                "ppp_profiles": ppp.get_ppp_profiles(api),
                "simple_queues": queues.get_simple_queues(api),
                "ip_pools": ip.get_ip_pools(api),
                "bridge_ports": interface_manager.get_bridge_ports(),
            }
            return details
        except Exception as e:
            raise RouterCommandError(f"Error en {self.host} (get_full_details): {e}")
        finally:
            if self.pool:
                self.pool.disconnect()

def get_router_service(host: str) -> RouterService:
    try:
        return RouterService(host)
    except (RouterConnectionError, RouterNotProvisionedError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))