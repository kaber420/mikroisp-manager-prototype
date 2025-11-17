# app/db/router_db.py
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# --- CAMBIO: Importación actualizada para usar 'base.py' ---
from .base import get_db_connection
# --- CAMBIO: Importar las funciones de cifrado ---
from ..utils.security import encrypt_data, decrypt_data

# --- Funciones CRUD para la API ---

def get_router_by_host(host: str) -> Optional[Dict[str, Any]]:
    """Obtiene todos los datos de un router por su host."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT * FROM routers WHERE host = ?", (host,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        # --- CAMBIO: Descifrar la contraseña antes de devolverla ---
        data = dict(row)
        data['password'] = decrypt_data(data['password'])
        return data
        
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.get_router_by_host para {host}: {e}")
        return None

def get_all_routers() -> List[Dict[str, Any]]:
    """Obtiene todos los routers de la base de datos."""
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """SELECT host, username, zona_id, api_port, api_ssl_port, is_enabled, 
                      hostname, model, firmware, last_status 
               FROM routers ORDER BY host"""
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.get_all_routers: {e}")
        return []

def create_router_in_db(router_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserta un nuevo router en la base de datos."""
    conn = get_db_connection()
    try:
        # --- CAMBIO: Cifrar la contraseña ---
        encrypted_password = encrypt_data(router_data['password'])
        
        conn.execute(
            """INSERT INTO routers (host, username, password, zona_id, api_port, is_enabled) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                router_data['host'], router_data['username'], encrypted_password, # <-- Usar variable cifrada
                router_data['zona_id'], router_data['api_port'], router_data['is_enabled']
            )
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Router host (IP) '{router_data['host']}' ya existe. Error: {e}")
    finally:
        conn.close()
    
    new_router = get_router_by_host(router_data['host'])
    if not new_router:
        raise ValueError("No se pudo recuperar el router después de la creación.")
    return new_router

def update_router_in_db(host: str, updates: Dict[str, Any]) -> int:
    """
    Función genérica para actualizar cualquier campo de un router.
    Devuelve el número de filas afectadas.
    """
    if not updates:
        return 0
        
    # --- CAMBIO: Cifrar la contraseña si se está actualizando ---
    if 'password' in updates and updates['password']:
        updates['password'] = encrypt_data(updates['password'])
        
    conn = get_db_connection()
    try:
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(host)
        
        query = f"UPDATE routers SET {set_clause} WHERE host = ?"
        cursor = conn.execute(query, tuple(values))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.update_router_in_db para {host}: {e}")
        return 0
    finally:
        conn.close()

def delete_router_from_db(host: str) -> int:
    """Elimina un router de la base de datos. Devuelve el número de filas afectadas."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM routers WHERE host = ?", (host,))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.delete_router_from_db para {host}: {e}")
        return 0
    finally:
        conn.close()

# --- Funciones para el Monitor (Refactorizadas) ---

def get_router_status(host: str) -> Optional[str]:
    """
    Obtiene el 'last_status' de un router específico desde la base de datos.
    """
    conn = get_db_connection() # Usamos una conexión ligera solo para el status
    try:
        cursor = conn.execute("SELECT last_status FROM routers WHERE host = ?", (host,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def update_router_status(host: str, status: str, data: Optional[Dict[str, Any]] = None):
    """
    Actualiza el estado de un router en la base de datos.
    Si el estado es 'online', también actualiza el hostname, modelo y firmware.
    (Esta función ahora usa 'update_router_in_db')
    """
    try:
        now = datetime.utcnow()
        update_data = {"last_status": status, "last_checked": now}
        
        if status == 'online' and data:
            update_data["hostname"] = data.get("name")
            update_data["model"] = data.get("board-name")
            update_data["firmware"] = data.get("version")
        
        update_router_in_db(host, update_data)
        
    except Exception as e:
        logging.error(f"Error en router_db.update_router_status para {host}: {e}")

def get_enabled_routers_from_db() -> List[Dict[str, Any]]:
    """
    Obtiene la lista de Routers activos y aprovisionados desde la BD.
    """
    routers_to_monitor = []
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """SELECT host, username, password, api_ssl_port 
               FROM routers 
               WHERE is_enabled = TRUE AND api_port = api_ssl_port"""
        )
        for row in cursor.fetchall():
            # --- CAMBIO: Descifrar la contraseña ---
            data = dict(row)
            data['password'] = decrypt_data(data['password'])
            routers_to_monitor.append(data)
            
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"No se pudo obtener la lista de Routers de la base de datos: {e}")
    return routers_to_monitor