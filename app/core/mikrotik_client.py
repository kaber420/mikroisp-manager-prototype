# app/core/mikrotik_client.py

import routeros_api
import ssl
import time
from typing import Dict, Any, List, Optional
from routeros_api.api import RouterOsApi 

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

def provision_router_api_ssl(admin_api: RouterOsApi, host: str, new_api_user: str, new_api_password: str) -> Dict[str, str]:
    """
    Configura el router para conexiones API-SSL seguras y crea un usuario de API dedicado.
    """
    try:
        user_group_name = "api_full_access"
        group_resource = admin_api.get_resource('/user/group')
        group_list = group_resource.get(name=user_group_name)
        current_policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
        
        if not group_list:
            group_resource.add(name=user_group_name, policy=current_policy)
        else:
            group_resource.set(id=_get_id(group_list[0]), policy=current_policy)
            
        user_resource = admin_api.get_resource('/user')
        if not (user_list := user_resource.get(name=new_api_user)):
            user_resource.add(name=new_api_user, password=new_api_password, group=user_group_name)
        else:
            user_resource.set(id=_get_id(user_list[0]), password=new_api_password, group=user_group_name)

        cert_name = "api_ssl_cert"
        cert_resource = admin_api.get_resource('/certificate')
        if existing_cert_list := cert_resource.get(name=cert_name):
            cert_resource.remove(id=_get_id(existing_cert_list[0]))
            time.sleep(1)
            
        cert_resource.add(name=cert_name, common_name=host, days_valid='3650')
        time.sleep(2)
        
        if not (new_cert_list := cert_resource.get(name=cert_name)): 
            raise Exception("No se encontró el certificado para firmarlo después de crearlo.")
        
        cert_resource.call('sign', {'id': _get_id(new_cert_list[0])})
        time.sleep(3)

        service_resource = admin_api.get_resource('/ip/service')
        if not (api_ssl_service_list := service_resource.get(name='api-ssl')):
            raise Exception("El servicio 'api-ssl' no fue encontrado en el router.")
        
        service_resource.set(id=_get_id(api_ssl_service_list[0]), certificate=cert_name, disabled='no')
        
        return {"status": "success", "message": "Router aprovisionado con API-SSL y usuario."}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error interno: {e}"}

def get_system_resources(api: RouterOsApi) -> Dict[str, Any]:
    resource_info = api.get_resource("/system/resource").get()
    identity_info = api.get_resource("/system/identity").get()
    data = {}
    if resource_info: data.update(resource_info[0])
    if identity_info: data.update(identity_info[0])
    return data

def get_interfaces(api: RouterOsApi) -> List[Dict[str, Any]]:
    try:
        return [iface for iface in api.get_resource("/interface").get() if iface.get('type') in ['ether', 'bridge', 'vlan'] and iface.get('name') != 'none']
    except Exception as e:
        import logging; logging.error(f"Error en get_interfaces: {e}"); return []

def get_ip_addresses(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/ip/address").get()
def get_nat_rules(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/ip/firewall/nat").get()
def get_pppoe_servers(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/interface/pppoe-server/server").get()
def get_ppp_profiles(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/ppp/profile").get()
def get_simple_queues(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/queue/simple").get()
def get_ip_pools(api: RouterOsApi) -> List[Dict[str, Any]]: return api.get_resource("/ip/pool").get()

def add_simple_queue(api: RouterOsApi, name: str, max_limit: str, comment: str):
    """
    Crea una nueva Cola Simple Padre. No especifica queue-type para usar el
    HTB por defecto del router, ideal para agrupar tráfico.
    """
    simple_q_res = api.get_resource("/queue/simple")
    if simple_q_res.get(name=name):
        raise ValueError(f"Una cola simple con el nombre '{name}' ya existe.")
    
    return simple_q_res.add(
        name=name,
        target="0.0.0.0/0",
        max_limit=max_limit,
        comment=comment
    )

def create_service_plan(api: RouterOsApi, 
                        plan_name: str, 
                        pool_range: str, 
                        local_address: str, 
                        rate_limit: str,
                        parent_queue: str,
                        comment: str):
    """
    Crea un plan (IP Pool y PPP Profile). El perfil asigna el límite de velocidad
    del cliente, establece CAKE como el tipo de cola para la cola hijo dinámica,
    y la asocia a una cola padre existente.
    """
    try:
        plan_slug = plan_name.lower().replace(" ", "-")
        pool_name = f"pool-{plan_slug}"
        profile_name = f"profile-{plan_slug}"
        
        pool_comment = f"Pool for Plan: {plan_name} ({comment})"
        profile_comment = f"Profile for Plan: {plan_name} ({comment})"
        
        pool_res = api.get_resource("/ip/pool")
        profile_res = api.get_resource("/ppp/profile")
        
        if not pool_res.get(name=pool_name):
            pool_res.add(name=pool_name, ranges=pool_range, comment=pool_comment)
            
        if not profile_res.get(name=profile_name):
            profile_data = {
                'name': profile_name,
                'local_address': local_address,
                'remote_address': pool_name,
                'dns_server': "8.8.8.8,1.1.1.1",
                'comment': profile_comment,
                'queue-type': "cake-ul/cake-dl"
            }
            if rate_limit and rate_limit != '0':
                profile_data['rate-limit'] = rate_limit
            if parent_queue and parent_queue != 'none':
                profile_data['parent-queue'] = parent_queue

            profile_res.add(**profile_data)
        
        return {"status": "success", "message": f"Plan (Perfil y Pool) '{plan_name}' creado."}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _find_resource_id(api_resource, **kwargs) -> Optional[str]:
    try:
        if resources := api_resource.get(**kwargs):
            return _get_id(resources[0])
        return None
    except Exception as e:
        print(f"Error buscando recurso con {kwargs}: {e}")
        return None

def remove_simple_queue(api: RouterOsApi, queue_id: str) -> None:
    api.get_resource('/queue/simple').remove(id=queue_id)

def remove_service_plan(api: RouterOsApi, plan_name: str) -> Dict[str, bool]:
    plan_slug = plan_name.lower().replace(" ", "-")
    profile_name = f"profile-{plan_slug}"
    pool_name = f"pool-{plan_slug}"
    results = {}
    
    if profile_id := _find_resource_id(api.get_resource('/ppp/profile'), name=profile_name):
        api.get_resource('/ppp/profile').remove(id=profile_id)
        results['profile'] = True
    
    if pool_id := _find_resource_id(api.get_resource('/ip/pool'), name=pool_name):
        api.get_resource('/ip/pool').remove(id=pool_id)
        results['pool'] = True
    return results

def add_ip_address(api: RouterOsApi, interface: str, address: str, comment: str): 
    return api.get_resource("/ip/address").add(interface=interface, address=address, comment=comment)

def add_nat_masquerade(api: RouterOsApi, out_interface_or_list: str, comment: str):
    nat_res = api.get_resource("/ip/firewall/nat")
    if not nat_res.get(comment=comment):
        return nat_res.add(chain="srcnat", action="masquerade", out_interface=out_interface_or_list, comment=comment)
    return {"status": "warning", "message": "NAT rule with this comment already exists."}

def add_pppoe_server(api: RouterOsApi, service_name: str, interface: str, default_profile: str):
    server_res = api.get_resource("/interface/pppoe-server/server")
    if not server_res.get(interface=interface):
        return server_res.add(**{'service-name': service_name, 'interface': interface, 'default-profile': default_profile, 'authentication': "mschap2", 'disabled': "no"})
    return {"status": "warning", "message": "PPPoE server on this interface already exists."}

def remove_ip_address(api: RouterOsApi, address: str) -> bool:
    if resource_id := _find_resource_id(api.get_resource('/ip/address'), address=address):
        api.get_resource('/ip/address').remove(id=resource_id)
        return True
    return False

def remove_nat_rule(api: RouterOsApi, comment: str) -> bool:
    if resource_id := _find_resource_id(api.get_resource('/ip/firewall/nat'), comment=comment):
        api.get_resource('/ip/firewall/nat').remove(id=resource_id)
        return True
    return False

def remove_pppoe_server(api: RouterOsApi, service_name: str) -> bool:
    if resource_id := _find_resource_id(api.get_resource('/interface/pppoe-server/server'), service_name=service_name):
        api.get_resource('/interface/pppoe-server/server').remove(id=resource_id)
        return True
    return False

def get_pppoe_secrets(api: RouterOsApi, username: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        resource = api.get_resource('/ppp/secret')
        return resource.get(name=username) if username else resource.get()
    except Exception as e:
        print(f"Error al obtener pppoe secrets: {e}"); return []

def get_pppoe_active_connections(api: RouterOsApi, name: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        resource = api.get_resource('/ppp/active')
        return resource.get(name=name) if name else resource.get()
    except Exception as e:
        print(f"Error al obtener pppoe active connections: {e}"); return []

def create_pppoe_secret(api: RouterOsApi, username: str, password: str, profile: str, comment: str, service: str = 'pppoe') -> Dict[str, Any]:
    resource = api.get_resource('/ppp/secret')
    if resource.get(name=username):
        raise ValueError(f"El usuario PPPoE '{username}' ya existe.")
    resource.add(name=username, password=password, profile=profile, service=service, comment=comment)
    if not (new_secret_list := resource.get(name=username)):
        raise Exception(f"No se pudo encontrar el secret '{username}' después de su creación.")
    return new_secret_list[0]

def update_pppoe_secret(api: RouterOsApi, secret_id: str, **kwargs) -> Dict[str, Any]:
    resource = api.get_resource('/ppp/secret')
    kwargs['id'] = secret_id
    return resource.set(**kwargs)

def enable_disable_pppoe_secret(api: RouterOsApi, secret_id: str, disable: bool = True) -> Dict[str, Any]:
    return update_pppoe_secret(api, secret_id, disabled='yes' if disable else 'no')

def remove_pppoe_secret(api: RouterOsApi, secret_id: str) -> None:
    api.get_resource('/ppp/secret').remove(id=secret_id)

def get_backup_files(api: RouterOsApi) -> List[Dict[str, Any]]:
    try:
        return [f for f in api.get_resource('/file').get() if f.get('type') in ['backup', 'script']]
    except Exception as e:
        print(f"Error al obtener lista de archivos: {e}"); return []

def create_backup(api: RouterOsApi, backup_name: str) -> None: 
    api.get_resource('/system/backup').call('save', {'name': backup_name})

def create_export_script(api: RouterOsApi, script_name: str) -> None: 
    api.get_resource('/').call('export', {'file': script_name})

def remove_file(api: RouterOsApi, file_id: str) -> None: 
    api.get_resource('/file').remove(id=file_id)

def get_router_users(api: RouterOsApi) -> List[Dict[str, Any]]:
    try:
        return api.get_resource('/user').get()
    except Exception as e:
        print(f"Error al obtener usuarios del router: {e}"); return []

def add_router_user(api: RouterOsApi, username: str, password: str, group: str) -> Dict[str, Any]:
    resource = api.get_resource('/user')
    if resource.get(name=username):
        raise ValueError(f"El usuario '{username}' ya existe.")
    resource.add(name=username, password=password, group=group)
    if not (new_user_list := resource.get(name=username)):
        return {"name": username, "group": group, "disabled": "false"}
    return new_user_list[0]

def remove_router_user(api: RouterOsApi, user_id: str) -> None:
    api.get_resource('/user').remove(id=user_id)