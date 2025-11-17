from typing import Dict, Any, Optional

def get_id(resource_dict: Dict[str, Any]) -> str:
    """
    Obtiene de forma segura el ID de un recurso devuelto por la API de MikroTik,
    probando tanto la clave 'id' como '.id'.
    """
    if 'id' in resource_dict:
        return resource_dict['id']
    if '.id' in resource_dict:
        return resource_dict['.id']
    raise KeyError(f"No se pudo encontrar una clave de ID ('id' o '.id') en el recurso: {resource_dict}")

def find_resource_id(api_resource, **kwargs) -> Optional[str]:
    """
    Busca un recurso por parámetros (ej. name='algo') y devuelve su ID.
    """
    try:
        if resources := api_resource.get(**kwargs):
            return get_id(resources[0])
        return None
    except Exception as e:
        print(f"Error buscando recurso con {kwargs}: {e}")
        return None