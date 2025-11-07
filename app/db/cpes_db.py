# app/db/cpes_db.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import get_db_connection

def get_unassigned_cpes() -> List[Dict[str, Any]]:
    """Obtiene una lista de todos los CPEs que no están asignados a ningún cliente."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE client_id IS NULL ORDER BY hostname")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_cpe_by_mac(mac: str) -> Optional[Dict[str, Any]]:
    """Obtiene un CPE por su dirección MAC."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT mac, hostname, client_id FROM cpes WHERE mac = ?", (mac,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def assign_cpe_to_client(mac: str, client_id: int) -> int:
    """Asigna un CPE a un cliente. Devuelve el número de filas afectadas."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("UPDATE cpes SET client_id = ? WHERE mac = ?", (client_id, mac))
        conn.commit()
        return cursor.rowcount
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("El Client ID no fue encontrado.")
    finally:
        conn.close()

def unassign_cpe(mac: str) -> int:
    """Desasigna un CPE de cualquier cliente. Devuelve el número de filas afectadas."""
    conn = get_db_connection()
    cursor = conn.execute("UPDATE cpes SET client_id = NULL WHERE mac = ?", (mac,))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount

def get_all_cpes_globally() -> List[Dict[str, Any]]:
    """
    Obtiene todos los CPEs con sus datos de estado más recientes y el nombre del AP al que están conectados.
    """
    conn = get_db_connection()
    stats_db_file = f"stats_{datetime.utcnow().strftime('%Y_%m')}.sqlite"
    
    if not os.path.exists(stats_db_file):
        conn.close()
        return []
        
    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
        query = """
            WITH LatestCPEStats AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                FROM stats_db.cpe_stats_history
            )
            SELECT s.*, a.hostname as ap_hostname
            FROM LatestCPEStats s
            LEFT JOIN aps a ON s.ap_host = a.host
            WHERE s.rn = 1
            ORDER BY s.cpe_hostname, s.cpe_mac;
        """
        cursor = conn.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.OperationalError as e:
        raise RuntimeError(f"Error al adjuntar la base de datos de estadísticas: {e}")
    finally:
        conn.close()