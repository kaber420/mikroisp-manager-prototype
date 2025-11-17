from typing import List, Dict, Any
from routeros_api.api import RouterOsApi
from .base import find_resource_id

def get_ip_addresses(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/ip/address").get()

def get_ip_pools(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/ip/pool").get()

def add_ip_address(api: RouterOsApi, interface: str, address: str, comment: str): 
    return api.get_resource("/ip/address").add(interface=interface, address=address, comment=comment)

def remove_ip_address(api: RouterOsApi, address: str) -> bool:
    if resource_id := find_resource_id(api.get_resource('/ip/address'), address=address):
        api.get_resource('/ip/address').remove(id=resource_id)
        return True
    return False