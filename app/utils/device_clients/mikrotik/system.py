import time
from typing import Dict, Any, List
from routeros_api.api import RouterOsApi
from .base import get_id
import logging # <-- Asegúrate de que esta importación esté

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
            group_resource.set(id=get_id(group_list[0]), policy=current_policy)
            
        user_resource = admin_api.get_resource('/user')
        if not (user_list := user_resource.get(name=new_api_user)):
            user_resource.add(name=new_api_user, password=new_api_password, group=user_group_name)
        else:
            user_resource.set(id=get_id(user_list[0]), password=new_api_password, group=user_group_name)

        cert_name = "api_ssl_cert"
        cert_resource = admin_api.get_resource('/certificate')
        if existing_cert_list := cert_resource.get(name=cert_name):
            cert_resource.remove(id=get_id(existing_cert_list[0]))
            time.sleep(1)
            
        cert_resource.add(name=cert_name, common_name=host, days_valid='3650')
        time.sleep(2)
        
        if not (new_cert_list := cert_resource.get(name=cert_name)): 
            raise Exception("No se encontró el certificado para firmarlo después de crearlo.")
        
        cert_resource.call('sign', {'id': get_id(new_cert_list[0])})
        time.sleep(3)

        service_resource = admin_api.get_resource('/ip/service')
        if not (api_ssl_service_list := service_resource.get(name='api-ssl')):
            raise Exception("El servicio 'api-ssl' no fue encontrado en el router.")
        
        service_resource.set(id=get_id(api_ssl_service_list[0]), certificate=cert_name, disabled='no')
        
        return {"status": "success", "message": "Router aprovisionado con API-SSL y usuario."}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error interno: {e}"}

def get_system_resources(api: RouterOsApi) -> Dict[str, Any]:
    resource_info = api.get_resource("/system/resource").get()
    identity_info = api.get_resource("/system/identity").get()
    routerboard_info = api.get_resource("/system/routerboard").get()
    license_info = api.get_resource("/system/license").get()
    health_info = api.get_resource("/system/health").get()
    
    data = {}
    
    # From /system/resource
    if resource_info:
        res = resource_info[0]
        data['uptime'] = res.get('uptime')
        data['version'] = res.get('version')
        data['cpu-load'] = res.get('cpu-load')
        data['total-memory'] = res.get('total-memory')
        data['free-memory'] = res.get('free-memory')
        # Normalizar el espacio en disco.
        # Algunos dispositivos usan 'hdd-space', otros 'disk-space'.
        # Usamos .get(key, ...) para encadenar las búsquedas.
        total_disk = res.get('total-hdd-space', res.get('total-disk-space'))
        free_disk = res.get('free-hdd-space', res.get('free-disk-space'))
        
        data['total-disk'] = total_disk
        data['free-disk'] = free_disk
        data['board-name'] = res.get('board-name')
        data['platform'] = res.get('platform', res.get('architecture-name'))
        data['cpu'] = res.get('cpu')
        data['cpu-count'] = res.get('cpu-count')
        data['cpu-frequency'] = res.get('cpu-frequency')

    # From /system/identity
    if identity_info:
        data['name'] = identity_info[0].get('name')

    # From /system/routerboard
    if routerboard_info:
        rb = routerboard_info[0]
        # 'model' from routerboard is often more accurate than 'board-name'
        data['model'] = rb.get('model', data.get('board-name'))
        data['serial-number'] = rb.get('serial-number')

    # From /system/license
    if license_info:
        data['nlevel'] = license_info[0].get('nlevel')

    # From /system/health
    if health_info:
        # MikroTik devuelve health en dos formatos posibles:
        # Formato A (Plano): [{'voltage': '24.5', 'temperature': '30'}]
        # Formato B (Modular/Tu Router): [{'name': 'voltage', 'value': '24'}, {'name': 'cpu-temperature', 'value': '53'}]
        
        for sensor in health_info:
            # Lógica para Formato B (Modular - Tu caso)
            if 'name' in sensor and 'value' in sensor:
                name = sensor['name']
                value = sensor['value']
                
                if name == 'voltage':
                    data['voltage'] = value
                elif name == 'temperature':
                    data['temperature'] = value
                elif name in ['cpu-temperature', 'cpu-temp']:
                    data['cpu-temperature'] = value
            
            # Lógica para Formato A (Plano - Otros routers)
            else:
                # Puede venir todo en el primer elemento o separado, iteramos igual
                if 'voltage' in sensor: data['voltage'] = sensor['voltage']
                if 'temperature' in sensor: data['temperature'] = sensor['temperature']
                if 'cpu-temperature' in sensor: data['cpu-temperature'] = sensor['cpu-temperature']
                if 'cpu-temp' in sensor: data['cpu-temperature'] = sensor['cpu-temp']

    return data

def get_interfaces(api: RouterOsApi) -> List[Dict[str, Any]]:
    try:
        # Añadido 'wlan' y 'pppoe-in' para que coincida con el frontend
        types_to_get = ['ether', 'bridge', 'vlan', 'wlan', 'bonding', 'loopback', 'pppoe-in']
        return [iface for iface in api.get_resource("/interface").get() if iface.get('type') in types_to_get and iface.get('name') != 'none']
    except Exception as e:
        logging.error(f"Error en get_interfaces: {e}"); return []

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


# --- ¡FUNCIONES CORREGIDAS! ---

def get_interface_resource_path(interface_type: str, for_remove: bool = False) -> str:
    """Devuelve la ruta de API correcta para un tipo de interfaz."""
    # Para 'set' (disable/enable), el path genérico /interface SIEMPRE funciona.
    if not for_remove:
        return "/interface"
    
    # Para 'remove', solo tipos específicos son válidos
    if interface_type in ['bridge', 'vlan', 'bonding']:
        return f"/interface/{interface_type}"
    
    # Si se intenta 'remove' un 'ether' o 'wlan', esto fallará.
    return "/interface"


def set_interface_status(api: RouterOsApi, interface_id: str, disabled: bool, interface_type: str):
    """Habilita o deshabilita una interfaz por su ID."""
    # Usamos el path genérico '/interface' que funciona para 'set' en todos los tipos.
    path = get_interface_resource_path(interface_type, for_remove=False) 
    
    # Usamos .call('set') para evitar que la librería traduzca 'id' a '.id'
    api.get_resource(path).call('set', {
        'id': interface_id, 
        'disabled': 'yes' if disabled else 'no'
    })

def remove_interface(api: RouterOsApi, interface_id: str, interface_type: str):
    """Elimina una interfaz (ej. vlan, bridge) por su ID."""
    if interface_type not in ['vlan', 'bridge', 'bonding']:
        raise ValueError(f"No se permite eliminar interfaces de tipo '{interface_type}'")
    
    # Obtenemos el path correcto (ej. /interface/vlan)
    path = get_interface_resource_path(interface_type, for_remove=True)
    
    # Usamos .call('remove') para evitar que la librería traduzca 'id' a '.id'
    api.get_resource(path).call('remove', {'id': interface_id})