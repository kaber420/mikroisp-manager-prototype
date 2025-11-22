# app/db/plans_db.py
import sqlite3
from typing import List, Dict, Any
from .base import get_db_connection

def get_all_plans() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    # --- CORRECCIÓN CRÍTICA ---
    # 1. Se cambia 'r.id' por 'r.rowid' (identificador interno de SQLite).
    # 2. Se mantiene 'r.hostname' que es el nombre correcto de la columna.
    cursor = conn.execute("""
        SELECT p.*, r.hostname as router_name 
        FROM plans p
        LEFT JOIN routers r ON p.router_id = r.rowid
        ORDER BY r.hostname, p.name
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_plans_by_router(router_id: int) -> List[Dict[str, Any]]:
    """Útil para cargar el dropdown de planes cuando seleccionas un router"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM plans WHERE router_id = ? ORDER BY name", (router_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_plan(plan_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO plans (router_id, name, max_limit, parent_queue, comment) VALUES (?, ?, ?, ?, ?)",
            (plan_data['router_id'], plan_data['name'], plan_data['max_limit'], plan_data.get('parent_queue'), plan_data.get('comment'))
        )
        new_id = cursor.lastrowid
        conn.commit()
        return {**plan_data, "id": new_id}
    finally:
        conn.close()

def get_plan_by_id(plan_id: int):
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def delete_plan(plan_id: int):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()