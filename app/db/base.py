# app/db/base.py
import sqlite3
import os
from datetime import datetime
from typing import Optional  # <-- CORRECCIÓN: Importación añadida

# --- Constantes de la Base de Datos ---
INVENTORY_DB_FILE = "inventory.sqlite"

# --- Funciones de Conexión ---
def get_db_connection() -> sqlite3.Connection:
    """
    Establece una conexión con la base de datos de inventario
    y configura el row_factory para acceder a las columnas por nombre.
    """
    conn = sqlite3.connect(INVENTORY_DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_stats_db_connection() -> Optional[sqlite3.Connection]:
    """
    Establece una conexión con la base de datos de estadísticas del mes actual.
    Devuelve None si el archivo no existe.
    """
    now = datetime.utcnow()
    stats_db_file = f"stats_{now.strftime('%Y_%m')}.sqlite"
    
    if not os.path.exists(stats_db_file):
        return None
        
    conn = sqlite3.connect(stats_db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn