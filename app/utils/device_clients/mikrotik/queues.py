from typing import List, Dict, Any, Optional
from routeros_api.api import RouterOsApi

def get_simple_queues(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/queue/simple").get()

def add_simple_queue(api: RouterOsApi, name: str, target: str, max_limit: str, comment: Optional[str] = None, dst: Optional[str] = None) -> Dict[str, str]:
    """
    Crea una nueva Cola Simple.
    """
    simple_q_res = api.get_resource("/queue/simple")
    if simple_q_res.get(name=name):
        raise ValueError(f"Una cola simple con el nombre '{name}' ya existe.")
    
    queue_data = {
        "name": name,
        "target": target,
        "max_limit": max_limit,
        "comment": comment or f"Managed by µMonitor: {name}"
    }
    
    if dst:
        queue_data["dst"] = dst
    
    simple_q_res.add(**queue_data)
    
    return {"status": "success", "message": f"Cola simple '{name}' creada exitosamente."}

def remove_simple_queue(api: RouterOsApi, queue_id: str) -> None:
    api.get_resource('/queue/simple').remove(id=queue_id)