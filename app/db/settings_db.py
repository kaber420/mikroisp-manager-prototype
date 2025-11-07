# app/db/settings_db.py
from .base import get_db_connection

def get_all_settings() -> dict:
    """Obtiene toda la configuración de la base de datos."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings

def update_settings(settings_to_update: dict):
    """Actualiza una o más configuraciones en la base de datos."""
    conn = get_db_connection()
    update_data = [(value, key) for key, value in settings_to_update.items()]
    conn.executemany("UPDATE settings SET value = ? WHERE key = ?", update_data)
    conn.commit()
    conn.close()

def get_setting(key: str) -> str | None:
    """Obtiene el valor de una clave de configuración específica."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None