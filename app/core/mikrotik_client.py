# app/core/mikrotik_client.py

import routeros_api
import ssl
import time
from typing import Dict, Any, List, Optional
from routeros_api.api import RouterOsApi 

# --- FUNCIÓN DE AYUDA ROBUSTA PARA OBTENER EL ID ---
def _get_id(resource_dict: Dict[str, Any]) -> str:
    """
    Obtiene de forma segura el ID de un recurso devuelto por la API de MikroTik,
    probando tanto la clave 'id' como '.id'.
    """
    if 'id' in resource_dict:
        return resource_dict['id']
    if '.id' in resource_dict:
        return resource_dict['.id']
    raise KeyError(f"No se pudo encontrar una clave de ID ('id' o '.id') en el recurso: {resource_dict}")

#
# 1. LÓGICA DE CONEXIÓN (ELIMINADA)
#
# --- LA FUNCIÓN 'get_api_connection' SE HA ELIMINADO ---
# La lógica de conexión (Pool) ahora se manejará directamente en
# los archivos que la necesitan (api/routers_api.py y monitor.py)
# para asegurar que el 'pool' que se abre, se cierra.
#

#
# 2. LÓGICA DE APROVISIONAMIENTO (Sin cambios)
#
def provision_router_api_ssl(admin_api: RouterOsApi, host: str, new_api_user: str, new_api_password: str) -> Dict[str, str]:
    try:
        # --- Paso 1: Grupo y Usuario ---
        user_group_name = "api_full_access"
        group_resource = admin_api.get_resource('/user/group')
        group_list = group_resource.get(name=user_group_name)
        
        current_policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,!telnet,!ftp,!reboot,!winbox,!web,!rest-api"

        if not group_list:
            group_resource.add(name=user_group_name, policy=current_policy)
        else:
            group_id = _get_id(group_list[0])
            group_resource.set(id=group_id, policy=current_policy)
            
        user_resource = admin_api.get_resource('/user')
        user_list = user_resource.get(name=new_api_user)
        if not user_list:
            user_resource.add(name=new_api_user, password=new_api_password, group=user_group_name)
        else:
            user_id = _get_id(user_list[0])
            user_resource.set(id=user_id, password=new_api_password, group=user_group_name)

        # --- Paso 2: Certificado SSL ---
        cert_name = "api_ssl_cert"
        cert_resource = admin_api.get_resource('/certificate')
        existing_cert_list = cert_resource.get(name=cert_name)
        if existing_cert_list:
            cert_id_to_remove = _get_id(existing_cert_list[0])
            cert_resource.remove(id=cert_id_to_remove)
            time.sleep(1)
            
        cert_resource.add(name=cert_name, common_name=host, days_valid='3650')
        time.sleep(2)
        new_cert_list = cert_resource.get(name=cert_name)
        if not new_cert_list: 
            raise Exception("No se encontró el certificado para firmarlo después de crearlo.")
        
        new_cert_id = _get_id(new_cert_list[0])
        cert_resource.call('sign', {'id': new_cert_id})
        time.sleep(3)

        # --- Paso 3: Asignar Servicio ---
        service_resource = admin_api.get_resource('/ip/service')
        api_ssl_service_list = service_resource.get(name='api-ssl')
        if not api_ssl_service_list:
            raise Exception("El servicio 'api-ssl' no fue encontrado en el router.")
        
        api_ssl_service_id = _get_id(api_ssl_service_list[0])
        service_resource.set(id=api_ssl_service_id, certificate=cert_name, disabled='no')
        
        return {"status": "success", "message": "Router aprovisionado con API-SSL y usuario."}
    
    except Exception as e:
        import traceback
        print("--- ERROR DETALLADO EN MIKROTIK_CLIENT ---")
        traceback.print_exc()
        print("-----------------------------------------")
        return {"status": "error", "message": f"Error interno: {e}"}

#
# 3. LÓGICA DE OPERACIONES (ADD/READ - Sin cambios)
#
def get_system_resources(api: RouterOsApi) -> Dict[str, Any]:
    resource_info = api.get_resource("/system/resource").get()
    identity_info = api.get_resource("/system/identity").get()
    data = {}
    if resource_info: data.update(resource_info[0])
    if identity_info: data.update(identity_info[0])
    return data

def install_core_config(api: RouterOsApi, selected_interface: str) -> Dict[str, str]:
    try:
        pool_resource = api.get_resource("/ip/pool")
        ppp_profile_resource = api.get_resource("/ppp/profile")
        queue_type_resource = api.get_resource("/queue/type")
        mangle_resource = api.get_resource("/ip/firewall/mangle")
        tree_resource = api.get_resource("/queue/tree")
        simple_queue_resource = api.get_resource("/queue/simple")
        ppp_server_resource = api.get_resource("/interface/pppoe-server/server")

        for pool_name in ["pool-plata", "pool-oro", "pool-cake"]:
            existing = pool_resource.get(name=pool_name)
            if existing: pool_resource.remove(id=_get_id(existing[0]))
        
        for profile_name in ["profile-plata", "profile-oro", "profile-cake", "profile-isp-default"]:
            existing = ppp_profile_resource.get(name=profile_name)
            if existing: ppp_profile_resource.remove(id=_get_id(existing[0]))

        for qtype_name in ["pcq-plata-down", "pcq-plata-up", "pcq-oro-down", "pcq-oro-up", "cake-upload", "cake-download"]:
            existing = queue_type_resource.get(name=qtype_name)
            if existing: queue_type_resource.remove(id=_get_id(existing[0]))

        for tree_name in ["GLOBAL_PCQ_DOWN", "GLOBAL_PCQ_UP", "plan-plata-down", "plan-plata-up", "plan-oro-down", "plan-oro-up"]:
            existing = tree_resource.get(name=tree_name)
            if existing: tree_resource.remove(id=_get_id(existing[0]))

        for q_name in ["Pool_Total_CAKE"]:
            existing = simple_queue_resource.get(name=q_name)
            if existing: simple_queue_resource.remove(id=_get_id(existing[0]))

        for conn_mark in ["conn-plata", "conn-oro"]:
            existing_mangle_conn = mangle_resource.get(new_connection_mark=conn_mark)
            for m in existing_mangle_conn: mangle_resource.remove(id=_get_id(m))
                
        for pkt_mark in ["pkt-plata-down", "pkt-plata-up", "pkt-oro-down", "pkt-oro-up"]:
            existing_mangle_pkt = mangle_resource.get(new_packet_mark=pkt_mark)
            for m in existing_mangle_pkt: mangle_resource.remove(id=_get_id(m))

        existing_server = ppp_server_resource.get(service_name="Servicio_ISP")
        if existing_server: ppp_server_resource.remove(id=_get_id(existing_server[0]))

        pool_resource.add(name="pool-plata", ranges="10.50.51.100-10.50.51.254")
        pool_resource.add(name="pool-oro", ranges="10.50.52.100-10.50.52.254")
        pool_resource.add(name="pool-cake", ranges="10.50.53.100-10.50.53.254")
        ppp_server_resource.add(authentication="mschap2", disabled="no", interface=selected_interface, service_name="Servicio_ISP")
        
        return {"status": "success", "message": "Configuración Core de Servicio instalada."}
    except Exception as e:
        return {"status": "error", "message": f"Error al instalar la configuración core: {e}"}

def get_interfaces(api: RouterOsApi) -> List[Dict[str, Any]]:
    try:
        all_interfaces = api.get_resource("/interface").get()
        filtered = [
            iface for iface in all_interfaces 
            if iface['type'] in ['ether', 'bridge', 'vlan'] and iface.get('name') != 'none'
        ]
        return filtered
    except Exception as e:
        import logging
        logging.error(f"Error en get_interfaces: {e}")
        return []

def get_ip_addresses(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/ip/address").get()

def get_nat_rules(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/ip/firewall/nat").get()

def get_interface_lists(api: RouterOsApi) -> List[Dict[str, Any]]:
    lists = api.get_resource("/interface/list").get()
    members = api.get_resource("/interface/list/member").get()
    list_map = {}
    for member in members:
        list_name = member['list']
        if list_name not in list_map:
            list_map[list_name] = []
        list_map[list_name].append(member['interface'])
    for lst in lists:
        lst['members'] = list_map.get(lst['name'], [])
    return lists

def get_pppoe_servers(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/interface/pppoe-server/server").get()

def get_ppp_profiles(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/ppp/profile").get()

def get_simple_queues(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/queue/simple").get()

def get_ip_pools(api: RouterOsApi) -> List[Dict[str, Any]]:
    return api.get_resource("/ip/pool").get()

def create_service_plan(api: RouterOsApi, 
                        plan_name: str, 
                        bandwidth: str, 
                        pool_range: str, 
                        local_address: str, 
                        comment: str):
    try:
        pool_name = f"pool-{plan_name.lower()}"
        profile_name = f"profile-{plan_name.lower()}"
        parent_q_name = f"PARENT-{plan_name.upper()}"
        
        pool_res = api.get_resource("/ip/pool")
        qtype_res = api.get_resource("/queue/type")
        simple_q_res = api.get_resource("/queue/simple")
        profile_res = api.get_resource("/ppp/profile")

        if not pool_res.get(name=pool_name):
            pool_res.add(name=pool_name, ranges=pool_range)
        if not qtype_res.get(name="cake-dl"):
            qtype_res.add(name="cake-dl", kind="cake")
        if not qtype_res.get(name="cake-ul"):
            qtype_res.add(name="cake-ul", kind="cake")
        if not simple_q_res.get(name=parent_q_name):
            simple_q_res.add(
                name=parent_q_name,
                max_limit=bandwidth,
                comment=comment
            )
        if not profile_res.get(name=profile_name):
            profile_res.add(
                name=profile_name,
                local_address=local_address,
                remote_address=pool_name,
                parent_queue=parent_q_name,
                queue_type="cake-ul/cake-dl",
                dns_server="8.8.8.8,1.1.1.1",
                comment=comment
            )
        return {"status": "success", "message": f"Plan '{plan_name}' creado."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def add_ip_address(api: RouterOsApi, interface: str, address: str, comment: str):
    return api.get_resource("/ip/address").add(
        interface=interface,
        address=address,
        comment=comment
    )

def add_nat_masquerade(api: RouterOsApi, out_interface_or_list: str, comment: str):
    nat_res = api.get_resource("/ip/firewall/nat")
    rules = nat_res.get(comment=comment)
    if not rules:
        return nat_res.add(
            chain="srcnat",
            action="masquerade",
            out_interface=out_interface_or_list,
            comment=comment
        )
    return {"status": "warning", "message": "NAT rule with this comment already exists."}


def add_pppoe_server(api: RouterOsApi, service_name: str, interface: str, default_profile: str):
    server_res = api.get_resource("/interface/pppoe-server/server")
    if not server_res.get(interface=interface):
        return server_res.add(
            service_name=service_name,
            interface=interface,
            default_profile=default_profile,
            authentication="mschap2"
        )
    return {"status": "warning", "message": "PPPoE server on this interface already exists."}

# ---
# 4. LÓGICA DE OPERACIONES (DELETE - Sin cambios)
# ---
def _find_resource_id(api_resource, **kwargs) -> Optional[str]:
    if not kwargs:
        raise ValueError("Se requieren atributos para encontrar el recurso.")
    try:
        resources = api_resource.get(**kwargs)
        if not resources:
            return None
        return _get_id(resources[0])
    except Exception as e:
        print(f"Error buscando recurso con {kwargs}: {e}")
        return None

def remove_ip_address(api: RouterOsApi, address: str) -> bool:
    resource = api.get_resource('/ip/address')
    resource_id = _find_resource_id(resource, address=address)
    if resource_id:
        resource.remove(id=resource_id)
        return True
    return False

def remove_nat_rule(api: RouterOsApi, comment: str) -> bool:
    resource = api.get_resource('/ip/firewall/nat')
    resource_id = _find_resource_id(resource, comment=comment)
    if resource_id:
        resource.remove(id=resource_id)
        return True
    return False

def remove_pppoe_server(api: RouterOsApi, service_name: str) -> bool:
    resource = api.get_resource('/interface/pppoe-server/server')
    resource_id = _find_resource_id(resource, service_name=service_name)
    if resource_id:
        resource.remove(id=resource_id)
        return True
    return False

def remove_service_plan(api: RouterOsApi, plan_name: str) -> Dict[str, bool]:
    profile_res = api.get_resource('/ppp/profile')
    pool_res = api.get_resource('/ip/pool')
    simple_q_res = api.get_resource('/queue/simple')

    profile_name = f"profile-{plan_name.lower()}"
    pool_name = f"pool-{plan_name.lower()}"
    parent_q_name = f"PARENT-{plan_name.upper()}"

    results = {}
    
    profile_id = _find_resource_id(profile_res, name=profile_name)
    if profile_id:
        profile_res.remove(id=profile_id)
        results['profile'] = True
    
    pool_id = _find_resource_id(pool_res, name=pool_name)
    if pool_id:
        pool_res.remove(id=pool_id)
        results['pool'] = True

    queue_id = _find_resource_id(simple_q_res, name=parent_q_name)
    if queue_id:
        simple_q_res.remove(id=queue_id)
        results['queue'] = True

    return results

# ---
# 5. LÓGICA DE GESTIÓN DE PPPoE (¡NUEVO!)
# ---

def get_pppoe_secrets(api: RouterOsApi) -> List[Dict[str, Any]]:
    """
    Obtiene la lista completa de todos los 'secrets' (usuarios) PPPoE del router.
    """
    try:
        return api.get_resource('/ppp/secret').get()
    except Exception as e:
        print(f"Error al obtener pppoe secrets: {e}")
        return []

def get_pppoe_active_connections(api: RouterOsApi) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de todas las conexiones PPPoE activas en este momento.
    """
    try:
        return api.get_resource('/ppp/active').get()
    except Exception as e:
        print(f"Error al obtener pppoe active connections: {e}")
        return []

def create_pppoe_secret(api: RouterOsApi, username: str, password: str, profile: str, comment: str, service: str = 'pppoe') -> Dict[str, Any]:
    """
    Crea un nuevo 'secret' (usuario) PPPoE en el router.
    """
    resource = api.get_resource('/ppp/secret')
    
    # Verificar si el usuario ya existe
    existing = resource.get(name=username)
    if existing:
        raise ValueError(f"El usuario PPPoE '{username}' ya existe en este router.")
        
    return resource.add(
        name=username,
        password=password,
        profile=profile,
        service=service,
        comment=comment
    )

def update_pppoe_secret(api: RouterOsApi, secret_id: str, **kwargs) -> Dict[str, Any]:
    """
    Función genérica para actualizar cualquier propiedad de un secret.
    Ej: update_pppoe_secret(api, '*1', password='newpass', profile='newplan')
    """
    resource = api.get_resource('/ppp/secret')
    
    # 'id' es la clave correcta para el comando 'set'
    kwargs['id'] = secret_id
    
    return resource.set(**kwargs)

def enable_disable_pppoe_secret(api: RouterOsApi, secret_id: str, disable: bool = True) -> Dict[str, Any]:
    """
    Activa o desactiva (suspende) un 'secret' PPPoE.
    """
    status = 'yes' if disable else 'no'
    return update_pppoe_secret(api, secret_id, disabled=status)

def remove_pppoe_secret(api: RouterOsApi, secret_id: str) -> None:
    """
    Elimina un 'secret' PPPoE del router usando su .id.
    """
    resource = api.get_resource('/ppp/secret')
    
    # 'id' es la clave correcta para el comando 'remove'
    resource.remove(id=secret_id)
    return