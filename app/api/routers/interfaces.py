from fastapi import APIRouter, Depends
from ...services.router_service import get_router_service, RouterService
from .models import VlanCreate, VlanUpdate, BridgeCreate, BridgeUpdate

router = APIRouter()

@router.post("/vlans")
def add_vlan(
    vlan_data: VlanCreate,
    service: RouterService = Depends(get_router_service)
):
    return service.add_vlan(
        name=vlan_data.name,
        vlan_id=str(vlan_data.vlan_id),
        interface=vlan_data.interface,
        comment=vlan_data.comment
    )

@router.put("/vlans/{vlan_id}")
def update_vlan(
    vlan_id: str,
    vlan_data: VlanUpdate,
    service: RouterService = Depends(get_router_service)
):
    return service.update_vlan(
        vlan_id=vlan_id,
        name=vlan_data.name,
        new_vlan_id=str(vlan_data.vlan_id),
        interface=vlan_data.interface
    )

@router.post("/bridges")
def add_bridge(
    bridge_data: BridgeCreate,
    service: RouterService = Depends(get_router_service)
):
    return service.add_bridge(
        name=bridge_data.name,
        ports=bridge_data.ports,
        comment=bridge_data.comment
    )

@router.put("/bridges/{bridge_id}")
def update_bridge(
    bridge_id: str,
    bridge_data: BridgeUpdate,
    service: RouterService = Depends(get_router_service)
):
    return service.update_bridge(
        bridge_id=bridge_id,
        name=bridge_data.name,
        ports=bridge_data.ports
    )
