# app/db/aps_db.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from .base import get_db_connection
# --- CAMBIO: Importar las funciones de cifrado ---
from ..utils.security import encrypt_data, decrypt_data # <-- LÍNEA CAMBIADA

# --- NUEVA FUNCIÓN (Movida desde monitor.py y mejorada) ---
def get_enabled_aps_for_monitor() -> list:
    """
    Obtiene la lista de APs activos desde la BD y descifra sus contraseñas.
    """
    aps_to_monitor = []
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT host, username, password FROM aps WHERE is_enabled = TRUE")
        
        for row in cursor.fetchall():
            creds = dict(row)
            # --- CAMBIO: Descifrar la contraseña ---
            creds['password'] = decrypt_data(creds['password'])
            aps_to_monitor.append(creds)
            
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"No se pudo obtener la lista de APs de la base de datos: {e}")
    return aps_to_monitor

# --- Funciones para el Monitor ---
def get_ap_status(host: str) -> Optional[str]:
    """Obtiene el último estado conocido de un AP."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_status FROM aps WHERE host = ?", (host,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_ap_status(host: str, status: str, data: Optional[Dict[str, Any]] = None):
    """Actualiza el estado de un AP, y opcionalmente sus metadatos si está online."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    
    if status == 'online' and data:
        host_info = data.get("host", {})
        interfaces = data.get("interfaces", [{}, {}])
        mac = interfaces[1].get("hwaddr") if len(interfaces) > 1 else None
        cursor.execute("""
        UPDATE aps 
        SET mac = ?, hostname = ?, model = ?, firmware = ?, last_status = ?, last_seen = ?, last_checked = ?
        WHERE host = ?
        """, (
            mac, host_info.get("hostname"), host_info.get("devmodel"), 
            host_info.get("fwversion"), status, now, now, host
        ))
    else: # AP está offline o no hay datos
        cursor.execute("UPDATE aps SET last_status = ?, last_checked = ? WHERE host = ?", (status, now, host))
        
    conn.commit()
    conn.close()

# --- Funciones para la API (Modificadas) ---
def get_ap_credentials(host: str) -> Optional[Dict[str, Any]]:
    """Obtiene el usuario y la contraseña de un AP para la conexión en vivo."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT username, password FROM aps WHERE host = ?", (host,))
    creds = cursor.fetchone()
    conn.close()
    
    if not creds:
        return None
    
    creds_dict = dict(creds)
    # --- CAMBIO: Descifrar la contraseña ---
    creds_dict['password'] = decrypt_data(creds_dict['password'])
    return creds_dict

def create_ap_in_db(ap_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserta un nuevo AP en la base de datos."""
    conn = get_db_connection()
    try:
        # --- CAMBIO: Cifrar la contraseña antes de guardarla ---
        encrypted_password = encrypt_data(ap_data['password'])
        
        conn.execute(
            "INSERT INTO aps (host, username, password, zona_id, is_enabled, monitor_interval, first_seen) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                ap_data['host'], ap_data['username'], encrypted_password, # <-- Usar variable cifrada
                ap_data['zona_id'], ap_data['is_enabled'], ap_data['monitor_interval']
            )
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Host duplicado o zona_id inválida. Error: {e}")
    finally:
        conn.close()
    
    new_ap = get_ap_by_host_with_stats(ap_data['host'])
    if not new_ap:
        raise ValueError("No se pudo recuperar el AP después de la creación.")
    return new_ap

def get_all_aps_with_stats() -> List[Dict[str, Any]]:
    """Obtiene todos los APs, uniendo los datos de estado más recientes de la DB de estadísticas."""
    conn = get_db_connection()
    stats_db_file = f"stats_{datetime.utcnow().strftime('%Y_%m')}.sqlite"
    
    if os.path.exists(stats_db_file):
        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
            query = """
                WITH LatestStats AS (
                    SELECT 
                        ap_host, client_count, airtime_total_usage,
                        ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                    FROM stats_db.ap_stats_history
                )
                SELECT a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage
                FROM aps AS a
                LEFT JOIN zonas AS z ON a.zona_id = z.id
                LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
                ORDER BY a.host;
            """
        except sqlite3.OperationalError:
            query = "SELECT a.*, z.nombre as zona_nombre, NULL as client_count, NULL as airtime_total_usage FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id ORDER BY a.host;"
    else:
        query = "SELECT a.*, z.nombre as zona_nombre, NULL as client_count, NULL as airtime_total_usage FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id ORDER BY a.host;"

    cursor = conn.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_ap_by_host_with_stats(host: str) -> Optional[Dict[str, Any]]:
    """Obtiene un AP específico, uniendo sus datos de estado más recientes."""
    conn = get_db_connection()
    stats_db_file = f"stats_{datetime.utcnow().strftime('%Y_%m')}.sqlite"

    if os.path.exists(stats_db_file):
        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
            query = """
                WITH LatestStats AS (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                    FROM stats_db.ap_stats_history
                    WHERE ap_host = ?
                )
                SELECT 
                    a.*, z.nombre as zona_nombre, s.client_count, s.airtime_total_usage, s.airtime_tx_usage, 
                    s.airtime_rx_usage, s.total_throughput_tx, s.total_throughput_rx, s.noise_floor, s.chanbw, 
                    s.frequency, s.essid, s.total_tx_bytes, s.total_rx_bytes, s.gps_lat, s.gps_lon, s.gps_sats
                FROM aps AS a
                LEFT JOIN zonas AS z ON a.zona_id = z.id
                LEFT JOIN LatestStats AS s ON a.host = s.ap_host AND s.rn = 1
                WHERE a.host = ?;
            """
            cursor = conn.execute(query, (host, host))
        except sqlite3.OperationalError:
            query = "SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id WHERE a.host = ?"
            cursor = conn.execute(query, (host,))
    else:
        query = "SELECT a.*, z.nombre as zona_nombre FROM aps a LEFT JOIN zonas z ON a.zona_id = z.id WHERE a.host = ?"
        cursor = conn.execute(query, (host,))
        
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_ap_in_db(host: str, updates: Dict[str, Any]) -> int:
    """Actualiza un AP en la base de datos y devuelve el número de filas afectadas."""
    conn = get_db_connection()
    
    # --- CAMBIO: Cifrar la contraseña si se está actualizando ---
    if 'password' in updates and updates['password']:
        updates['password'] = encrypt_data(updates['password'])
    
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(host)
    
    cursor = conn.execute(f"UPDATE aps SET {set_clause} WHERE host = ?", tuple(values))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount

def delete_ap_from_db(host: str) -> int:
    """Elimina un AP de la base de datos y devuelve el número de filas afectadas."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM aps WHERE host = ?", (host,))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount