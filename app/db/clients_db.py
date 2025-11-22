# app/db/clients_db.py
import sqlite3
from typing import List, Dict, Any, Optional
from .base import get_db_connection

def get_all_clients_with_cpe_count() -> List[Dict[str, Any]]:
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

def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO clients (name, address, phone_number, whatsapp_number, email, service_status, billing_day, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                client_data.get('name'), client_data.get('address'), client_data.get('phone_number'),
                client_data.get('whatsapp_number'), client_data.get('email'), client_data.get('service_status'),
                client_data.get('billing_day'), client_data.get('notes')
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
    conn = get_db_connection()
    try:
        conn.execute("UPDATE cpes SET client_id = NULL WHERE client_id = ?", (client_id,))
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
    # --- CORRECCIÓN: Agregado 'ip_address' al SELECT ---
    cursor = conn.execute("SELECT mac, hostname, ip_address FROM cpes WHERE client_id = ?", (client_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# --- Funciones de Servicios ---

def get_client_service_by_id(service_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM client_services WHERE id = ?", (service_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_services_for_client(client_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM client_services WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_client_service(client_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserta un nuevo registro de servicio en la base de datos."""
    conn = get_db_connection()
    try:
        # --- CORRECCIÓN: Agregados campos 'plan_id' e 'ip_address' al INSERT ---
        cursor = conn.execute(
            """INSERT INTO client_services (client_id, router_host, service_type, pppoe_username, 
                                       router_secret_id, profile_name, suspension_method, plan_id, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id, data['router_host'], data['service_type'], data.get('pppoe_username'),
                data.get('router_secret_id'), data.get('profile_name'), data['suspension_method'],
                data.get('plan_id'), data.get('ip_address') # Nuevos campos
            )
        )
        new_service_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValueError(str(e))
    finally:
        conn.close()

    new_service = get_client_service_by_id(new_service_id)
    if not new_service:
        raise ValueError("No se pudo recuperar el servicio después de la creación.")
    return new_service

def get_active_clients_by_billing_day(day: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT id, name FROM clients WHERE service_status = 'active' AND billing_day = ?",
        (day,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows