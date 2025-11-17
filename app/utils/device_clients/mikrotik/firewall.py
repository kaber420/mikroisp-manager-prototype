from typing import List, Dict, Any
from routeros_api.api import RouterOsApi
from .base import find_resource_id

def get_nat_rules(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/ip/firewall/nat").get()

def add_nat_masquerade(api: RouterOsApi, out_interface_or_list: str, comment: str):
    nat_res = api.get_resource("/ip/firewall/nat")
    if not nat_res.get(comment=comment):
        return nat_res.add(chain="srcnat", action="masquerade", out_interface=out_interface_or_list, comment=comment)
    return {"status": "warning", "message": "NAT rule with this comment already exists."}

def remove_nat_rule(api: RouterOsApi, comment: str) -> bool:
    if resource_id := find_resource_id(api.get_resource('/ip/firewall/nat'), comment=comment):
        api.get_resource('/ip/firewall/nat').remove(id=resource_id)
        return True
    return False 