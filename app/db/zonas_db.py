# app/db/zonas_db.py
import sqlite3
import os
from typing import List, Dict, Any, Optional
from .base import get_db_connection
from ..core.security import encrypt_data, decrypt_data

# --- Funciones de Zonas (CRUD Básico) ---

def create_zona(nombre: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("INSERT INTO zonas (nombre) VALUES (?)", (nombre,))
        new_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"El nombre de la zona '{nombre}' ya existe.")
    finally:
        conn.close()
    return {"id": new_id, "nombre": nombre}

def get_all_zonas() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT id, nombre FROM zonas ORDER BY nombre")
    zonas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return zonas

def update_zona_details(zona_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    
    if 'notas_sensibles' in updates and updates['notas_sensibles'] is not None:
        updates['notas_sensibles'] = encrypt_data(updates['notas_sensibles'])

    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(zona_id)
    
    try:
        cursor = conn.execute(f"UPDATE zonas SET {set_clause} WHERE id = ?", tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            return None
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("El nombre de la zona ya existe.")
    finally:
        conn.close()
    return get_zona_by_id(zona_id)

def delete_zona(zona_id: int) -> int:
    conn = get_db_connection()
    cursor_check_aps = conn.execute("SELECT 1 FROM aps WHERE zona_id = ?", (zona_id,))
    if cursor_check_aps.fetchone():
        conn.close()
        raise ValueError("No se puede eliminar la zona porque contiene APs.")
    cursor_check_routers = conn.execute("SELECT 1 FROM routers WHERE zona_id = ?", (zona_id,))
    if cursor_check_routers.fetchone():
        conn.close()
        raise ValueError("No se puede eliminar la zona porque contiene Routers.")

    cursor_delete = conn.execute("DELETE FROM zonas WHERE id = ?", (zona_id,))
    conn.commit()
    rowcount = cursor_delete.rowcount
    conn.close()
    return rowcount

def get_zona_by_id(zona_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zonas WHERE id = ?", (zona_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if data.get('notas_sensibles'):
        data['notas_sensibles'] = decrypt_data(data['notas_sensibles'])
    return data

# --- Funciones de Infraestructura ---

def get_infra_by_zona_id(zona_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_infraestructura WHERE zona_id = ?", (zona_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_or_create_infra(zona_id: int, infra_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    existing_infra = get_infra_by_zona_id(zona_id)
    
    if existing_infra:
        set_clause = ", ".join([f"{key} = ?" for key in infra_data.keys()])
        values = list(infra_data.values())
        values.append(zona_id)
        conn.execute(f"UPDATE zona_infraestructura SET {set_clause} WHERE zona_id = ?", tuple(values))
    else:
        columns = ", ".join(infra_data.keys())
        placeholders = ", ".join(["?"] * len(infra_data))
        values = list(infra_data.values())
        conn.execute(f"INSERT INTO zona_infraestructura (zona_id, {columns}) VALUES (?, {placeholders})", (zona_id, *values))
        
    conn.commit()
    conn.close()
    return get_infra_by_zona_id(zona_id)

# --- Funciones de Documentos ---

def get_docs_by_zona_id(zona_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_documentos WHERE zona_id = ? ORDER BY creado_en DESC", (zona_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def add_document(doc_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO zona_documentos (zona_id, tipo, nombre_original, nombre_guardado, descripcion)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_data['zona_id'], doc_data['tipo'], doc_data['nombre_original'], doc_data['nombre_guardado'], doc_data['descripcion'])
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    new_doc = get_document_by_id(new_id)
    if not new_doc:
         raise ValueError("No se pudo recuperar el documento después de la creación.")
    return new_doc

def get_document_by_id(doc_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM zona_documentos WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_document(doc_id: int) -> int:
    doc_info = get_document_by_id(doc_id)
    if doc_info:
        file_path = os.path.join("uploads", "zonas", str(doc_info['zona_id']), doc_info['nombre_guardado'])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM zona_documentos WHERE id = ?", (doc_id,))
    rowcount = cursor.rowcount
    conn.commit()
    conn.close()
    return rowcount