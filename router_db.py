# router_db.py
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Importamos las funciones de conexión desde el database.py principal
from database import get_db_connection, INVENTORY_DB_FILE

def get_router_status(host: str) -> Optional[str]:
    """
    Obtiene el 'last_status' de un router específico desde la base de datos.
    """
    try:
        conn = get_db_connection(INVENTORY_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT last_status FROM routers WHERE host = ?", (host,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.get_router_status para {host}: {e}")
        return None

def update_router_status(host: str, status: str, data: Optional[Dict[str, Any]] = None):
    """
    Actualiza el estado de un router en la base de datos.
    Si el estado es 'online', también actualiza el hostname, modelo y firmware.
    """
    try:
        conn = get_db_connection(INVENTORY_DB_FILE)
        cursor = conn.cursor()
        now = datetime.utcnow()
        
        if status == 'online' and data:
            hostname = data.get("name")
            model = data.get("board-name") # Clave correcta de la API de MikroTik
            firmware = data.get("version")
            
            cursor.execute(
                """
                UPDATE routers 
                SET hostname = ?, model = ?, firmware = ?, last_status = ?, last_checked = ?
                WHERE host = ?
                """,
                (hostname, model, firmware, status, now, host)
            )
        else: # Router está offline o no hay datos
            cursor.execute(
                "UPDATE routers SET last_status = ?, last_checked = ? WHERE host = ?", 
                (status, now, host)
            )
            
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error en router_db.update_router_status para {host}: {e}")

def get_enabled_routers_from_db() -> List[Dict[str, Any]]:
    """
    Obtiene la lista de Routers activos y aprovisionados desde la BD.
    """
    routers_to_monitor = []
    try:
        conn = get_db_connection(INVENTORY_DB_FILE)
        # Solo monitorea routers que están habilitados Y ya aprovisionados (api_port == api_ssl_port)
        cursor = conn.execute(
            """SELECT host, username, password, api_ssl_port 
               FROM routers 
               WHERE is_enabled = TRUE AND api_port = api_ssl_port"""
        )
        for row in cursor.fetchall():
            routers_to_monitor.append(dict(row))
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"No se pudo obtener la lista de Routers de la base de datos: {e}")
    return routers_to_monitor