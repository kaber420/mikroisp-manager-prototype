# app/utils/device_clients/ppp.py (o la ruta correcta en tu proyecto)

from typing import List, Dict, Any, Optional # <-- IMPORTACIÓN ACTUALIZADA
from routeros_api.api import RouterOsApi
from .base import find_resource_id

def get_pppoe_servers(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/interface/pppoe-server/server").get()

def get_ppp_profiles(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/ppp/profile").get()

# --- INICIO DE LA FUNCIÓN MODIFICADA ---
def create_service_plan(api: RouterOsApi, 
                        plan_name: str, 
                        local_address: str, 
                        rate_limit: str,
                        parent_queue: str,
                        comment: str,
                        pool_range: Optional[str] = None,
                        remote_address: Optional[str] = None):
    """
    Crea un plan (IP Pool y PPP Profile).
    - Si se pasa 'pool_range', crea un nuevo pool.
    - Si se pasa 'remote_address', usa un pool existente.
    """
    try:
        plan_slug = plan_name.lower().replace(" ", "-")
        profile_name = f"profile-{plan_slug}"
        
        pool_res = api.get_resource("/ip/pool")
        profile_res = api.get_resource("/ppp/profile")
        
        profile_comment = f"Profile for Plan: {plan_name} ({comment})"
            
        if not profile_res.get(name=profile_name):
            profile_data = {
                'name': profile_name,
                'local_address': local_address,
                # 'remote_address' se añadirá abajo
                'dns_server': "8.8.8.8,1.1.1.1",
                'comment': profile_comment,
                'queue-type': "cake-ul/cake-dl"
            }

            # --- INICIO DE LA NUEVA LÓGICA DE POOL ---
            if pool_range:
                # Opción A: Se envió un rango. Creamos un pool nuevo.
                pool_name = f"pool-{plan_slug}" # Nombre autogenerado
                pool_comment = f"Pool for Plan: {plan_name} ({comment})"
                
                if not pool_res.get(name=pool_name):
                    pool_res.add(name=pool_name, ranges=pool_range, comment=pool_comment)
                
                profile_data['remote_address'] = pool_name # Usamos el pool recién creado
            
            elif remote_address:
                # Opción B: Se envió un nombre de pool. Lo usamos directamente.
                profile_data['remote_address'] = remote_address
            
            else:
                # Error si el frontend no envió ninguno (Pydantic ya debería haberlo atrapado)
                raise ValueError("Se requiere 'pool_range' (para crear) o 'remote_address' (para usar uno existente).")
            # --- FIN DE LA NUEVA LÓGICA DE POOL ---

            if rate_limit and rate_limit != '0':
                profile_data['rate-limit'] = rate_limit
            if parent_queue and parent_queue != 'none':
                profile_data['parent-queue'] = parent_queue

            profile_res.add(**profile_data)
        
        return {"status": "success", "message": f"Plan (Perfil y Pool) '{plan_name}' creado."}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
# --- FIN DE LA FUNCIÓN MODIFICADA ---

def remove_service_plan(api: RouterOsApi, plan_name: str) -> Dict[str, bool]:
    """
    Elimina un plan de servicio (perfil PPP y, opcionalmente, su pool de IP asociado).
    Maneja nombres de planes que ya vienen con el prefijo 'profile-'.
    """
    # Si el nombre del plan ya viene con el prefijo, úsalo directamente.
    # Si no, constrúyelo. Esto hace que la función sea más robusta.
    if plan_name.startswith('profile-'):
        profile_name = plan_name
    else:
        plan_slug = plan_name.lower().replace(" ", "-")
        profile_name = f"profile-{plan_slug}"

    # El nombre del pool se deriva del nombre del perfil, quitando el prefijo.
    pool_name = f"pool-{profile_name.replace('profile-', '')}"
    
    results = {}
    
    # Eliminar el perfil PPP
    profile_resource = api.get_resource('/ppp/profile')
    if profile_id := find_resource_id(profile_resource, name=profile_name):
        profile_resource.remove(id=profile_id)
        results['profile'] = True
    
    # Eliminar el pool de IP asociado
    pool_resource = api.get_resource('/ip/pool')
    if pool_id := find_resource_id(pool_resource, name=pool_name):
        pool_resource.remove(id=pool_id)
        results['pool'] = True
        
    return results

def add_pppoe_server(api: RouterOsApi, service_name: str, interface: str, default_profile: str):
    server_res = api.get_resource("/interface/pppoe-server/server")
    if not server_res.get(interface=interface):
        return server_res.add(**{'service-name': service_name, 'interface': interface, 'default-profile': default_profile, 'authentication': "mschap2", 'disabled': "no"})
    return {"status": "warning", "message": "PPPoE server on this interface already exists."}

def remove_pppoe_server(api: RouterOsApi, service_name: str) -> bool:
    if resource_id := find_resource_id(api.get_resource('/interface/pppoe-server/server'), service_name=service_name):
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