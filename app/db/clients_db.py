# app/db/clients_db.py
import sqlite3
from typing import List, Dict, Any, Optional
from .base import get_db_connection

def get_all_clients_with_cpe_count() -> List[Dict[str, Any]]:
    """Obtiene todos los clientes con su conteo de CPEs asociados."""
    conn = get_db_connection()
    query = """
        SELECT c.*, COUNT(p.mac) as cpe_count
        FROM clients c
        LEFT JOIN cpes p ON c.id = p.client_id
        GROUP BY c.id
        ORDER BY c.name;
    """
    cursor = conn.execute(query)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo cliente en la base de datos y lo devuelve."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO clients (name, address, phone_number, whatsapp_number, email, service_status, suspension_method, billing_day, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                client_data.get('name'), client_data.get('address'), client_data.get('phone_number'),
                client_data.get('whatsapp_number'), client_data.get('email'), client_data.get('service_status'),
                client_data.get('suspension_method'), client_data.get('billing_day'), client_data.get('notes')
            )
        )
        new_client_id = cursor.lastrowid
        conn.commit()

        cursor = conn.execute("SELECT c.*, 0 as cpe_count FROM clients c WHERE c.id = ?", (new_client_id,))
        new_client_row = cursor.fetchone()
        if not new_client_row:
             raise ValueError("No se pudo recuperar el cliente después de la creación.")
        return dict(new_client_row)
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_client(client_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza un cliente y devuelve sus datos actualizados."""
    conn = get_db_connection()
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(client_id)
    
    cursor = conn.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", tuple(values))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return None
        
    cursor = conn.execute("SELECT c.*, (SELECT COUNT(*) FROM cpes WHERE client_id = c.id) as cpe_count FROM clients c WHERE c.id = ?", (client_id,))
    updated_client_row = cursor.fetchone()
    conn.close()
    if not updated_client_row:
        return None
    return dict(updated_client_row)

def delete_client(client_id: int) -> int:
    """Elimina un cliente y desasigna sus CPEs. Devuelve el número de filas eliminadas."""
    conn = get_db_connection()
    try:
        # Primero desasignar CPEs
        conn.execute("UPDATE cpes SET client_id = NULL WHERE client_id = ?", (client_id,))
        # Luego eliminar el cliente
        cursor = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_cpes_for_client(client_id: int) -> List[Dict[str, Any]]:
    """Obtiene los CPEs asignados a un cliente específico."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT mac, hostname FROM cpes WHERE client_id = ?", (client_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows