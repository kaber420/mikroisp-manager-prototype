# database.py

import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

# --- Constantes de la Base de Datos ---
INVENTORY_DB_FILE = "inventory.sqlite"

# --- Funciones de Configuración ---

def get_db_connection(db_file: str) -> sqlite3.Connection:
    """Establece una conexión con una base de datos y configura el row_factory."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

def _get_current_stats_db_file() -> str:
    """Genera el nombre del archivo de la BD de stats para el mes actual."""
    now = datetime.utcnow()
    return f"stats_{now.strftime('%Y_%m')}.sqlite"

def setup_databases():
    """
    Función principal de inicialización. Crea o actualiza la estructura de AMBAS bases de datos.
    """
    print("Configurando la base de datos de inventario (inventory.sqlite)...")
    _setup_inventory_db()
    print("Configurando la base de datos de estadísticas mensuales...")
    _setup_stats_db()
    print("Configuración de bases de datos completada.")

def _setup_inventory_db():
    """Crea las tablas en la base de datos de inventario si no existen."""
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    default_settings = [
        ('telegram_bot_token', ''),
        ('telegram_chat_id', ''),
        ('default_monitor_interval', '300'),
        ('dashboard_refresh_interval', '60')
    ]
    cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        hashed_password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        telegram_chat_id TEXT,
        receive_alerts BOOLEAN NOT NULL DEFAULT FALSE,
        receive_announcements BOOLEAN NOT NULL DEFAULT FALSE,
        disabled BOOLEAN NOT NULL DEFAULT FALSE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zonas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aps (
        host TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        zona_id INTEGER,
        is_enabled BOOLEAN DEFAULT TRUE,
        monitor_interval INTEGER,
        mac TEXT, 
        hostname TEXT, 
        model TEXT, 
        firmware TEXT,
        last_status TEXT, 
        first_seen DATETIME, 
        last_seen DATETIME, 
        last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """)
    
    # --- CAMBIO 1: Nueva tabla 'clients' para los datos de las personas (Clientes) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone_number TEXT,
        whatsapp_number TEXT,
        email TEXT,
        telegram_contact TEXT,
        coordinates TEXT,
        notes TEXT,
        service_status TEXT NOT NULL DEFAULT 'active',
        suspension_method TEXT,
        billing_day INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # --- CAMBIO 2: La antigua tabla 'clients' ahora es 'cpes' y está vinculada a 'clients' ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpes (
        mac TEXT PRIMARY KEY, 
        hostname TEXT, 
        model TEXT, 
        firmware TEXT, 
        ip_address TEXT,
        client_id INTEGER, -- Clave foránea para vincular un CPE a un Cliente (persona)
        first_seen DATETIME, 
        last_seen DATETIME,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
    )
    """)
    
    # --- INICIO DE NUEVO BLOQUE: Tabla de Routers MikroTik ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routers (
        host TEXT PRIMARY KEY,
        api_port INTEGER DEFAULT 8728,    -- Puerto para API (inicialmente 8728 sin SSL)
        api_ssl_port INTEGER DEFAULT 8729, -- Puerto para API-SSL (después de aprovisionar)
        username TEXT NOT NULL,           -- Inicia como 'admin', luego se actualiza a 'api-user'
        password TEXT NOT NULL,           -- Inicia como pass de 'admin', luego se actualiza
        zona_id INTEGER,
        is_enabled BOOLEAN DEFAULT TRUE,
        hostname TEXT,
        model TEXT,
        firmware TEXT,
        last_status TEXT,
        last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """)
    # --- FIN DE NUEVO BLOQUE ---
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aps_zona ON aps (zona_id);")
    # --- CAMBIO 3: Actualizado el nombre del índice para la nueva tabla 'cpes' y eliminado el obsoleto ---
    cursor.execute("DROP INDEX IF EXISTS idx_clients_ip;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpes_ip ON cpes (ip_address);")
    
    conn.commit()
    conn.close()

def _setup_stats_db():
    """Crea las tablas en la base de datos de estadísticas del mes actual si no existen."""
    stats_db_file = _get_current_stats_db_file()
    conn = get_db_connection(stats_db_file)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ap_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        ap_host TEXT,
        uptime INTEGER,
        cpuload REAL,
        freeram INTEGER,
        client_count INTEGER,
        noise_floor INTEGER,
        total_throughput_tx INTEGER,
        total_throughput_rx INTEGER,
        airtime_total_usage INTEGER,
        airtime_tx_usage INTEGER,
        airtime_rx_usage INTEGER,
        frequency INTEGER,
        chanbw INTEGER,
        essid TEXT,
        total_tx_bytes INTEGER,
        total_rx_bytes INTEGER,
        gps_lat REAL,
        gps_lon REAL,
        gps_sats INTEGER
    )
    """)
    
    # --- CAMBIO 4: Renombrada la tabla 'client_stats_history' a 'cpe_stats_history' y sus columnas ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpe_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT, cpe_mac TEXT,
        cpe_hostname TEXT, ip_address TEXT, signal INTEGER, signal_chain0 INTEGER, signal_chain1 INTEGER,
        noisefloor INTEGER, cpe_tx_power INTEGER, distance INTEGER,
        dl_capacity INTEGER, ul_capacity INTEGER,
        airmax_cinr_rx REAL, airmax_usage_rx REAL, airmax_cinr_tx REAL, airmax_usage_tx REAL,
        throughput_rx_kbps INTEGER, throughput_tx_kbps INTEGER, total_rx_bytes INTEGER,
        total_tx_bytes INTEGER, cpe_uptime INTEGER,
        eth_plugged BOOLEAN, eth_speed INTEGER, eth_cable_len INTEGER
    )
    """)

    # --- CAMBIO 5: Actualizadas las columnas en la tabla de desconexiones ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disconnection_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT,
        cpe_mac TEXT, cpe_hostname TEXT, reason_code INTEGER, connection_duration INTEGER
    )
    """)
    
    # --- CAMBIO 6: Actualizado el nombre del índice y eliminado el antiguo obsoleto ---
    cursor.execute("DROP INDEX IF EXISTS idx_client_stats_mac;")
    cursor.execute("DROP INDEX IF EXISTS idx_client_stats_ip;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_mac ON cpe_stats_history (cpe_mac);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_ip ON cpe_stats_history (ip_address);")
    
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings

def update_settings(settings_to_update: dict):
    conn = get_db_connection(INVENTORY_DB_FILE)
    update_data = [(value, key) for key, value in settings_to_update.items()]
    conn.executemany("UPDATE settings SET value = ? WHERE key = ?", update_data)
    conn.commit()
    conn.close()

def get_setting(key: str) -> str | None:
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None


def get_ap_status(host: str) -> str | None:
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT last_status FROM aps WHERE host = ?", (host,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_ap_status(host: str, status: str, data: dict = None):
    conn = get_db_connection(INVENTORY_DB_FILE)
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
            mac, host_info.get("hostname"),
            host_info.get("devmodel"), host_info.get("fwversion"), status, now, now, host
        ))
    else: # AP está offline
        cursor.execute("UPDATE aps SET last_status = ?, last_checked = ? WHERE host = ?", (status, now, host))
        
    conn.commit()
    conn.close()

def save_full_snapshot(ap_host: str, data: dict):
    """
    Función central que guarda un snapshot completo de datos. Ahora con la nueva estructura.
    """
    if not data: return
    
    # --- CAMBIO 7: Llamada a la función renombrada ---
    _update_cpe_inventory(data)
    
    stats_db_file = _get_current_stats_db_file()
    _setup_stats_db()
    
    conn = get_db_connection(stats_db_file)
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    ap_hostname = data.get("host", {}).get("hostname", ap_host)

    wireless_info = data.get("wireless", {})
    throughput_info = wireless_info.get("throughput", {})
    polling_info = wireless_info.get("polling", {})
    ath0_status = data.get("interfaces", [{}, {}])[1].get("status", {})
    gps_info = data.get("gps", {})
    
    cursor.execute("""
        INSERT INTO ap_stats_history (
            timestamp, ap_host, uptime, cpuload, freeram, client_count, noise_floor,
            total_throughput_tx, total_throughput_rx, airtime_total_usage, 
            airtime_tx_usage, airtime_rx_usage, frequency, chanbw, essid,
            total_tx_bytes, total_rx_bytes, gps_lat, gps_lon, gps_sats
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, ap_host, data.get("host", {}).get("uptime"), data.get("host", {}).get("cpuload"),
        data.get("host", {}).get("freeram"), wireless_info.get("count"), wireless_info.get("noisef"),
        throughput_info.get("tx"), throughput_info.get("rx"),
        polling_info.get("use"), polling_info.get("tx_use"), polling_info.get("rx_use"),
        wireless_info.get("frequency"), wireless_info.get("chanbw"), wireless_info.get("essid"),
        ath0_status.get("tx_bytes"), ath0_status.get("rx_bytes"),
        gps_info.get("lat"), gps_info.get("lon"), gps_info.get("sats")
    ))

    # --- CAMBIO 8: Actualizada la lógica para insertar en 'cpe_stats_history' ---
    for cpe in wireless_info.get("sta", []):
        remote = cpe.get("remote", {})
        stats = cpe.get("stats", {})
        airmax = cpe.get("airmax", {})
        eth_info = remote.get("ethlist", [{}])[0]
        chainrssi = cpe.get('chainrssi', [None, None, None])

        cursor.execute("""
            INSERT INTO cpe_stats_history (
                timestamp, ap_host, cpe_mac, cpe_hostname, ip_address, signal, 
                signal_chain0, signal_chain1, noisefloor, cpe_tx_power, distance, 
                dl_capacity, ul_capacity, airmax_cinr_rx, airmax_usage_rx, 
                airmax_cinr_tx, airmax_usage_tx, throughput_rx_kbps, throughput_tx_kbps, 
                total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed, eth_cable_len
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, ap_host, cpe.get("mac"), remote.get("hostname"),
            cpe.get("lastip"), cpe.get("signal"), chainrssi[0], chainrssi[1], 
            cpe.get("noisefloor"), remote.get("tx_power"), cpe.get("distance"),
            airmax.get("dl_capacity"), airmax.get("ul_capacity"),
            airmax.get('rx', {}).get('cinr'), airmax.get('rx', {}).get('usage'), 
            airmax.get('tx', {}).get('cinr'), airmax.get('tx', {}).get('usage'), 
            remote.get('rx_throughput'), remote.get('tx_throughput'), 
            stats.get('rx_bytes'), stats.get('tx_bytes'), remote.get('uptime'), 
            eth_info.get('plugged'), eth_info.get('speed'), eth_info.get('cable_len')
        ))
        
    for event in wireless_info.get("sta_disconnected", []):
        cursor.execute("""
            INSERT INTO disconnection_events (timestamp, ap_host, cpe_mac, cpe_hostname, reason_code, connection_duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp, ap_host, event.get("mac"), event.get("hostname"),
            event.get("reason_code"), event.get("disconnect_duration")
        ))

    conn.commit()
    conn.close()
    print(f"Datos de '{ap_hostname}' y sus CPEs guardados en '{stats_db_file}'.")


# --- CAMBIO 9: Función renombrada y su lógica actualizada para la tabla 'cpes' ---
def _update_cpe_inventory(data: dict):
    """Actualiza la tabla de inventario de CPEs (dispositivos)."""
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.cursor()
    now = datetime.utcnow()
    
    for cpe in data.get("wireless", {}).get("sta", []):
        remote = cpe.get("remote", {})
        cursor.execute("""
        INSERT INTO cpes (mac, hostname, model, firmware, ip_address, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            hostname = excluded.hostname, model = excluded.model,
            firmware = excluded.firmware, ip_address = excluded.ip_address,
            last_seen = excluded.last_seen
        """, (
            cpe.get("mac"), remote.get("hostname"), remote.get("platform"),
            cpe.get("version"), cpe.get("lastip"), now, now
        ))
    conn.commit()
    conn.close()

# --- Bloque de funciones de gestión de usuarios ---

def get_all_users() -> List[Dict[str, Any]]:
    """Obtiene una lista de todos los usuarios de la base de datos (sin la contraseña)."""
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.execute("SELECT username, role, telegram_chat_id, receive_alerts, receive_announcements, disabled FROM users ORDER BY username")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def create_user_in_db(username: str, hashed_password: str, role: str = 'admin') -> Dict[str, Any]:
    """Crea un nuevo usuario en la base de datos."""
    conn = get_db_connection(INVENTORY_DB_FILE)
    try:
        conn.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
            (username, hashed_password, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"El usuario '{username}' ya existe.")
    finally:
        if conn:
            conn.close()
    
    # Devuelve los datos del nuevo usuario (sin la contraseña)
    return { "username": username, "role": role, "disabled": False, 
             "telegram_chat_id": None, "receive_alerts": False, "receive_announcements": False }

def update_user_in_db(username: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza los datos de un usuario. 'updates' es un diccionario con los campos a cambiar."""
    if not updates:
        return None

    conn = get_db_connection(INVENTORY_DB_FILE)
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(username)
    
    query = f"UPDATE users SET {set_clause} WHERE username = ?"
    
    cursor = conn.execute(query, tuple(values))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return None
    
    cursor = conn.execute("SELECT username, role, telegram_chat_id, receive_alerts, receive_announcements, disabled FROM users WHERE username = ?", (username,))
    updated_user = cursor.fetchone()
    conn.close()
    return dict(updated_user) if updated_user else None

def delete_user_from_db(username: str) -> bool:
    """Elimina un usuario de la base de datos. Devuelve True si se eliminó, False si no se encontró."""
    conn = get_db_connection(INVENTORY_DB_FILE)
    cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount > 0

def get_users_for_notification(notification_type: str) -> List[str]:
    """
    Obtiene los telegram_chat_id de los usuarios que han optado por recibir un tipo específico de notificación.
    """
    if notification_type not in ['alert', 'announcement']:
        return []

    column_to_check = 'receive_alerts' if notification_type == 'alert' else 'receive_announcements'
    
    conn = get_db_connection(INVENTORY_DB_FILE)
    query = f"SELECT telegram_chat_id FROM users WHERE {column_to_check} = TRUE AND telegram_chat_id IS NOT NULL AND disabled = FALSE"
    cursor = conn.execute(query)
    
    chat_ids = [row['telegram_chat_id'] for row in cursor.fetchall()]
    conn.close()
    return chat_ids