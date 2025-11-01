# mikrotik_client.py
import routeros_api
import ssl
import time
from typing import Dict, Any
from routeros_api.api import RouterOsApi # <-- AÑADIDO PARA CORREGIR EL TYPE HINT

#
# 1. LÓGICA DE CONEXIÓN (EXTRAÍDA DE TU SCRIPT)
#

def get_api_connection(host: str, user: str, password: str, port: int, use_ssl: bool = True) -> RouterOsApi:
    """
    Se conecta al router. Esta es una versión simplificada de tu
    función connect_to_router() para ser usada por otras funciones.
    """
    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connection = routeros_api.connect(
                host=host, username=user, password=password, port=port,
                use_ssl=True, ssl_context=ssl_context, plaintext_login=True 
            )
        else:
            # Conexión para el aprovisionamiento inicial
            connection = routeros_api.connect(
                host=host, username=user, password=password, port=port, plaintext_login=True
            )
        return connection
    except Exception as e:
        # En lugar de imprimir, lanzamos una excepción para que el endpoint la capture
        raise Exception(f"Error de conexión API: {e}")

#
# 2. LÓGICA DE APROVISIONAMIENTO (EXTRAÍDA DE TU SCRIPT)
#
def provision_router_api_ssl(admin_api: RouterOsApi, host: str, new_api_user: str, new_api_password: str) -> Dict[str, str]:
    """
    Esta es tu función configure_ssl_and_user(), refactorizada.
    Recibe una conexión 'admin_api' (sin SSL) y crea el nuevo usuario y el SSL.
    """
    try:
        # --- Paso 1: Grupo y Usuario (Lógica de tu script) ---
        user_group_name = "api_full_access"
        group_resource = admin_api.get_resource('/user/group')
        if not group_resource.get(name=user_group_name):
            policy = "read,write,api,test,password,sensitive,policy"
            group_resource.add(name=user_group_name, policy=policy)
            
        user_resource = admin_api.get_resource('/user')
        if not user_resource.get(name=new_api_user):
            user_resource.add(name=new_api_user, password=new_api_password, group=user_group_name)
        else:
            # Si el usuario ya existe, solo actualizamos su contraseña
            user_id = user_resource.get(name=new_api_user)[0]['id']
            user_resource.set(id=user_id, password=new_api_password, group=user_group_name)


        # --- Paso 2: Certificado SSL (Lógica de tu script) ---
        cert_name = "api_ssl_cert"
        cert_resource = admin_api.get_resource('/certificate')
        existing_cert = cert_resource.get(name=cert_name)
        if existing_cert:
            cert_resource.remove(id=existing_cert[0]['id'])
            time.sleep(1)
            
        cert_resource.add(name=cert_name, common_name=host, days_valid='3650')
        time.sleep(2)
        new_cert = cert_resource.get(name=cert_name)
        if not new_cert: raise Exception("No se encontró el certificado para firmarlo.")
        cert_resource.call('sign', {'id': new_cert[0]['id']})
        time.sleep(3) # Esperar a que el certificado se firme

        # --- Paso 3: Asignar Servicio (Lógica de tu script) ---
        service_resource = admin_api.get_resource('/ip/service')
        api_ssl_service = service_resource.get(name='api-ssl')[0]
        service_resource.set(id=api_ssl_service['id'], certificate=cert_name, disabled='no')
        
        # En lugar de imprimir, devolvemos un diccionario de éxito
        return {"status": "success", "message": "Router aprovisionado con API-SSL y usuario."}
    
    except Exception as e:
        # En lugar de imprimir, devolvemos un diccionario de error
        return {"status": "error", "message": str(e)}

#
# 3. LÓGICA DE OPERACIONES (EXTRAÍDA DE TUS SUBMENÚS)
#
def get_system_resources(api: RouterOsApi) -> Dict[str, Any]:
    """
    Obtiene los recursos del sistema. (Ejemplo de operación 'read')
    """
    resource_info = api.get_resource("/system/resource").get()
    identity_info = api.get_resource("/system/identity").get()
    
    data = {}
    if resource_info:
        data.update(resource_info[0])
    if identity_info:
        data.update(identity_info[0])
        
    return data

def install_core_config(api: RouterOsApi, selected_interface: str) -> Dict[str, str]:
    """
    Esta es la lógica de tu función install_core_config(), refactorizada.
    """
    try:
        # Recursos (Lógica de tu script)
        pool_resource = api.get_resource("/ip/pool")
        ppp_profile_resource = api.get_resource("/ppp/profile")
        queue_type_resource = api.get_resource("/queue/type")
        mangle_resource = api.get_resource("/ip/firewall/mangle")
        tree_resource = api.get_resource("/queue/tree")
        simple_queue_resource = api.get_resource("/queue/simple")
        ppp_server_resource = api.get_resource("/ppp/pppoe-server/server")

        # --- Eliminar recursos existentes --- (Lógica de tu script)
        for pool_name in ["pool-plata", "pool-oro", "pool-cake"]:
            existing_pools = pool_resource.get(name=pool_name)
            if existing_pools: pool_resource.remove(id=existing_pools[0]['.id'])
        
        for profile_name in ["profile-plata", "profile-oro", "profile-cake", "profile-isp-default"]:
            existing_profiles = ppp_profile_resource.get(name=profile_name)
            if existing_profiles: ppp_profile_resource.remove(id=existing_profiles[0]['.id'])

        for qtype_name in ["pcq-plata-down", "pcq-plata-up", "pcq-oro-down", "pcq-oro-up", "cake-upload", "cake-download"]:
            existing_qtypes = queue_type_resource.get(name=qtype_name)
            if existing_qtypes: queue_type_resource.remove(id=existing_qtypes[0]['.id'])

        for tree_name in ["GLOBAL_PCQ_DOWN", "GLOBAL_PCQ_UP", "plan-plata-down", "plan-plata-up", "plan-oro-down", "plan-oro-up"]:
            existing_trees = tree_resource.get(name=tree_name)
            if existing_trees: tree_resource.remove(id=existing_trees[0]['.id'])

        for q_name in ["Pool_Total_CAKE"]:
            existing_simple = simple_queue_resource.get(name=q_name)
            if existing_simple: simple_queue_resource.remove(id=existing_simple[0]['.id'])

        for conn_mark in ["conn-plata", "conn-oro"]:
            existing_mangle_conn = mangle_resource.get(new_connection_mark=conn_mark)
            for m in existing_mangle_conn: mangle_resource.remove(id=m['.id'])
                
        for pkt_mark in ["pkt-plata-down", "pkt-plata-up", "pkt-oro-down", "pkt-oro-up"]:
            existing_mangle_pkt = mangle_resource.get(new_packet_mark=pkt_mark)
            for m in existing_mangle_pkt: mangle_resource.remove(id=m['.id'])

        existing_server = ppp_server_resource.get(service_name="Servicio_ISP")
        if existing_server: ppp_server_resource.remove(id=existing_server[0]['.id'])

        # --- Crear nueva configuración --- (Lógica de tu script)
        pool_resource.add(name="pool-plata", ranges="10.50.51.100-10.50.51.254")
        pool_resource.add(name="pool-oro", ranges="10.50.52.100-10.50.52.254")
        pool_resource.add(name="pool-cake", ranges="10.50.53.100-10.50.53.254")
        ppp_profile_resource.add(name="profile-isp-default", dns_server="8.8.8.8,1.1.1.1", local_address="10.50.50.1", use_encryption="yes")
        queue_type_resource.add(name="pcq-plata-down", kind="pcq", pcq_rate="15M", pcq_classifier="dst-address")
        queue_type_resource.add(name="pcq-plata-up", kind="pcq", pcq_rate="4M", pcq_classifier="src-address")
        queue_type_resource.add(name="pcq-oro-down", kind="pcq", pcq_rate="25M", pcq_classifier="dst-address")
        queue_type_resource.add(name="pcq-oro-up", kind="pcq", pcq_rate="6M", pcq_classifier="src-address")
        ppp_profile_resource.add(name="profile-plata", dns_server="8.8.8.8,1.1.1.1", local_address="10.50.50.1", use_encryption="yes", remote_address="pool-plata")
        ppp_profile_resource.add(name="profile-oro", dns_server="8.8.8.8,1.1.1.1", local_address="10.50.50.1", use_encryption="yes", remote_address="pool-oro")
        ppp_profile_resource.add(name="profile-cake", dns_server="8.8.8.8,1.1.1.1", local_address="10.50.50.1", use_encryption="yes", remote_address="pool-cake")
        mangle_resource.add(action="mark-connection", chain="prerouting", new_connection_mark="conn-plata", passthrough="yes", src_address="10.50.51.0/24")
        mangle_resource.add(action="mark-packet", chain="prerouting", connection_mark="conn-plata", new_packet_mark="pkt-plata-down", passthrough="no")
        mangle_resource.add(action="mark-packet", chain="postrouting", connection_mark="conn-plata", new_packet_mark="pkt-plata-up", passthrough="no", out_interface="!bridge-LAN")
        mangle_resource.add(action="mark-connection", chain="prerouting", new_connection_mark="conn-oro", passthrough="yes", src_address="10.50.52.0/24")
        mangle_resource.add(action="mark-packet", chain="prerouting", connection_mark="conn-oro", new_packet_mark="pkt-oro-down", passthrough="no")
        mangle_resource.add(action="mark-packet", chain="postrouting", connection_mark="conn-oro", new_packet_mark="pkt-oro-up", passthrough="no", out_interface="!bridge-LAN")
        tree_resource.add(name="GLOBAL_PCQ_DOWN", parent="global", max_limit="250M")
        tree_resource.add(name="GLOBAL_PCQ_UP", parent="global", max_limit="55M")
        tree_resource.add(name="plan-plata-down", parent="GLOBAL_PCQ_DOWN", packet_mark="pkt-plata-down", queue="pcq-plata-down")
        tree_resource.add(name="plan-plata-up", parent="GLOBAL_PCQ_UP", packet_mark="pkt-plata-up", queue="pcq-plata-up")
        tree_resource.add(name="plan-oro-down", parent="GLOBAL_PCQ_DOWN", packet_mark="pkt-oro-down", queue="pcq-oro-down")
        tree_resource.add(name="plan-oro-up", parent="GLOBAL_PCQ_UP", packet_mark="pkt-oro-up", queue="pcq-oro-up")
        queue_type_resource.add(name="cake-upload", kind="cake", cake_flow_isolation="triple-isolate")
        queue_type_resource.add(name="cake-download", kind="cake", cake_flow_isolation="triple-isolate")
        simple_queue_resource.add(name="Pool_Total_CAKE", max_limit="100M/45M", queue="default-small/default-small", target="10.50.53.0/24")
        ppp_server_resource.add(authentication="mschap2", disabled="no", interface=selected_interface, service_name="Servicio_ISP")
        
        return {"status": "success", "message": "Configuración Core de Servicio instalada."}
    except Exception as e:
        return {"status": "error", "message": f"Error al instalar la configuración core: {e}"}

# (Aquí se añadirían más funciones refactorizadas de tus otros submenús, 
# como add_pppoe_client, add_static_client, get_users, etc.)