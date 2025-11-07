import sqlite3
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .base import get_db_connection

# --- Modelos Pydantic específicos de la DB ---
# Es una buena práctica tener modelos para lo que entra y sale de la DB.
class UserInDB(BaseModel):
    username: str
    hashed_password: str
    disabled: bool = False

# --- Funciones de Acceso a Datos ---
def get_user_by_username(username: str) -> Optional[UserInDB]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if user_row:
            return UserInDB(**dict(user_row))
        return None
    finally:
        conn.close()

def get_all_users() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT username, role, telegram_chat_id, receive_alerts, receive_announcements, disabled FROM users ORDER BY username"
        )
        users = [dict(row) for row in cursor.fetchall()]
        return users
    finally:
        conn.close()

def create_user(username: str, hashed_password: str, role: str = 'admin') -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        try:
            conn.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hashed_password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"El usuario '{username}' ya existe.")
    finally:
        conn.close()

    # Devuelve los datos del nuevo usuario (sin la contraseña)
    return {
        "username": username,
        "role": role,
        "disabled": False,
        "telegram_chat_id": None,
        "receive_alerts": False,
        "receive_announcements": False
    }

def update_user(username: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not updates:
        return None

    conn = get_db_connection()
    try:
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(username)

        query = f"UPDATE users SET {set_clause} WHERE username = ?"

        cursor = conn.execute(query, tuple(values))
        conn.commit()

        # Algunos adaptadores devuelven -1 si no está disponible; comprobamos usando una nueva SELECT si es necesario
        if getattr(cursor, "rowcount", None) == 0:
            return None

        # Después de actualizar, obtener los datos actualizados para devolverlos
        cursor = conn.execute(
            "SELECT username, role, telegram_chat_id, receive_alerts, receive_announcements, disabled FROM users WHERE username = ?",
            (username,)
        )
        updated_user = cursor.fetchone()
        return dict(updated_user) if updated_user else None
    finally:
        conn.close()

def delete_user(username: str) -> bool:
    """Elimina un usuario de la base de datos. Devuelve True si se eliminó, False si no se encontró."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        rowcount = cursor.rowcount
        return rowcount > 0
    finally:
        conn.close()

def get_users_for_notification(notification_type: str) -> List[str]:
    if notification_type not in ['alert', 'announcement']:
        return []

    column_to_check = 'receive_alerts' if notification_type == 'alert' else 'receive_announcements'

    conn = get_db_connection()
    try:
        # En SQLite los booleanos suelen representarse como 1/0
        query = f"SELECT telegram_chat_id FROM users WHERE {column_to_check} = 1 AND telegram_chat_id IS NOT NULL AND disabled = 0"
        cursor = conn.execute(query)
        chat_ids = [row['telegram_chat_id'] for row in cursor.fetchall()]
        return chat_ids
    finally:
        conn.close()

