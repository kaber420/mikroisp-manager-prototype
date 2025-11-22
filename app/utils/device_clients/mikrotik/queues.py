from typing import List, Dict, Any, Optional
from routeros_api.api import RouterOsApi

def get_simple_queues(api: RouterOsApi) -> List[Dict[str, Any]]: 
    return api.get_resource("/queue/simple").get()

def add_simple_queue(api: RouterOsApi,
                     name: str,
                     target: str,
                     max_limit: str,
                     parent: Optional[str] = None,
                     comment: Optional[str] = None,
                     dst: Optional[str] = None,
                     is_parent: bool = False) -> Dict[str, str]:
    """
    Crea una nueva Cola Simple soportando Parent y la etiqueta [PARENT].
    """
    simple_q_res = api.get_resource("/queue/simple")

    # Verificar si existe por nombre (para evitar duplicados/errores)
    if simple_q_res.get(name=name):
        raise ValueError(f"Una cola simple con el nombre '{name}' ya existe.")

    # Generar comentario base
    final_comment = comment or f"Managed by µMonitor: {name}"

    # Añadir etiqueta si es una cola padre
    if is_parent:
        final_comment += " [PARENT]"

    queue_data = {
        "name": name,
        "target": target,
        "max-limit": max_limit,
        "comment": final_comment
    }

    if dst:
        queue_data["dst"] = dst

    if parent and parent != 'none':
        queue_data["parent"] = parent

    simple_q_res.add(**queue_data)

    return {"status": "success", "message": f"Cola simple '{name}' creada exitosamente."}

def remove_simple_queue(api: RouterOsApi, queue_id: str) -> None:
    """
    Elimina una cola simple, con una salvaguarda para las colas padre.
    """
    simple_q_res = api.get_resource('/queue/simple')
    
    # Obtener la cola para verificar el comentario
    queue_to_delete = simple_q_res.get(id=queue_id)
    
    if not queue_to_delete:
        raise ValueError(f"No se encontró una cola simple con el ID '{queue_id}'.")
        
    # Extraer el comentario (puede ser una lista)
    comment = queue_to_delete[0].get('comment', '')

    # Salvaguarda para no borrar colas de infraestructura
    if '[PARENT]' in comment:
        raise PermissionError("No se puede eliminar una cola marcada como [PARENT] desde esta interfaz.")
        
    simple_q_res.remove(id=queue_id)