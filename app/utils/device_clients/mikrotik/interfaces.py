from routeros_api.api import RouterOsApi
from typing import List, Dict, Any

class MikrotikInterfaceManager:
    def __init__(self, api: RouterOsApi):
        self.api = api

    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str) -> Dict[str, Any]:
        vlan_resource = self.api.get_resource('/interface/vlan')
        vlan_resource.add(
            name=name,
            vlan_id=vlan_id,
            interface=interface,
            comment=comment
        )
        return vlan_resource.get(name=name)[0]

    def update_vlan(self, vlan_id: str, name: str, new_vlan_id: str, interface: str) -> Dict[str, Any]:
        vlan_resource = self.api.get_resource('/interface/vlan')
        vlan_resource.set(
            id=vlan_id,
            name=name,
            vlan_id=new_vlan_id,
            interface=interface
        )
        return vlan_resource.get(id=vlan_id)[0]

    def add_bridge(self, name: str, comment: str) -> Dict[str, Any]:
        bridge_resource = self.api.get_resource('/interface/bridge')
        bridge_resource.add(
            name=name,
            comment=comment
        )
        return bridge_resource.get(name=name)[0]

    def update_bridge(self, bridge_id: str, name: str) -> Dict[str, Any]:
        bridge_resource = self.api.get_resource('/interface/bridge')
        bridge_resource.set(
            id=bridge_id,
            name=name
        )
        return bridge_resource.get(id=bridge_id)[0]

    def set_bridge_ports(self, bridge_name: str, ports: List[str]):
        bridge_port_resource = self.api.get_resource('/interface/bridge/port')
        
        # Remove existing ports
        for port in bridge_port_resource.get(bridge=bridge_name):
            bridge_port_resource.remove(id=port['.id'])
            
        # Add new ports
        for port_name in ports:
            bridge_port_resource.add(
                bridge=bridge_name,
                interface=port_name
            )

    def get_bridge_ports(self) -> List[Dict[str, Any]]:
        return self.api.get_resource('/interface/bridge/port').get()
