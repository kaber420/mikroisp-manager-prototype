# database.py - Versión Optimizada con Lazy Initialization

import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from threading import Lock
import time

# --- Constantes de la Base de Datos ---
INVENTORY_DB_FILE = "inventory.sqlite"

# --- Pool de Conexiones Thread-Safe con Lazy Initialization ---
class ConnectionPool:
    """Pool de conexiones SQLite thread-safe con inicialización perezosa."""
    
    def __init__(self, db_file: str, pool_size: int = 10):
        self.db_file = db_file
        self.pool_size = pool_size
        self.connections = []
        self.lock = Lock()
        self._initialized = False
    
    def _create_connection(self) -> sqlite3.Connection:
        """Crea una conexión optimizada con PRAGMAs de rendimiento."""
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # Optimizaciones críticas de SQLite
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB de cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        conn.execute("PRAGMA page_size=4096")
        
        return conn
    
    def _initialize_pool(self):
        """Inicializa el pool con conexiones (lazy)."""
        if self._initialized:
            return
            
        with self.lock:
            if self._initialized:  # Double-check
                return
            
            for _ in range(self.pool_size):
                self.connections.append(self._create_connection())
            self._initialized = True
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener una conexión del pool."""
        # Lazy initialization
        if not self._initialized:
            self._initialize_pool()
        
        conn = None
        with self.lock:
            if self.connections:
                conn = self.connections.pop()
        
        if conn is None:
            # Si el pool está vacío, crear una conexión temporal
            conn = self._create_connection()
            temp_conn = True
        else:
            temp_conn = False
        
        try:
            yield conn
        finally:
            if not temp_conn:
                with self.lock:
                    self.connections.append(conn)
            else:
                conn.close()
    
    def close_all(self):
        """Cierra todas las conexiones del pool."""
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()
            self._initialized = False


# --- Gestor de Conexiones para Stats con ATTACH permanente y Lazy Init ---
class StatsConnectionManager:
    """Gestiona conexiones a la base de datos de stats con ATTACH automático y lazy init."""
    
    def __init__(self):
        self.pool = None
        self.current_month = None
        self.lock = Lock()
    
    def _get_current_month(self) -> str:
        """Obtiene el identificador del mes actual."""
        return datetime.utcnow().strftime('%Y_%m')
    
    def _ensure_pool(self):
        """Asegura que el pool esté inicializado (lazy)."""
        current = self._get_current_month()
        
        with self.lock:
            if self.pool is None or self.current_month != current:
                # Cerrar el pool anterior si existe
                if self.pool:
                    self.pool.close_all()
                
                # Crear nuevo pool para el mes actual
                stats_file = f"stats_{current}.sqlite"
                self.pool = ConnectionPool(stats_file, pool_size=10)
                self.current_month = current
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener una conexión con ATTACH."""
        self._ensure_pool()
        
        with self.pool.get_connection() as conn:
            # Verificar/hacer ATTACH
            try:
                conn.execute("SELECT 1 FROM inv_db.sqlite_master LIMIT 1")
            except sqlite3.OperationalError:
                # Re-attach si es necesario
                try:
                    conn.execute(f"ATTACH DATABASE '{INVENTORY_DB_FILE}' AS inv_db")
                except sqlite3.OperationalError:
                    pass  # Ya está attached
            yield conn


# --- Instancias Globales con Lazy Initialization ---
class LazyConnectionPool:
    """Wrapper para inicialización perezosa del pool."""
    def __init__(self):
        self._pool = None
        self._lock = Lock()
    
    def _ensure_initialized(self):
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    self._pool = ConnectionPool(INVENTORY_DB_FILE, pool_size=15)
    
    def get_connection(self):
        self._ensure_initialized()
        return self._pool.get_connection()
    
    def close_all(self):
        if self._pool:
            self._pool.close_all()


class LazyStatsManager:
    """Wrapper para inicialización perezosa del stats manager."""
    def __init__(self):
        self._manager = None
        self._lock = Lock()
    
    def _ensure_initialized(self):
        if self._manager is None:
            with self._lock:
                if self._manager is None:
                    self._manager = StatsConnectionManager()
    
    def get_connection(self):
        self._ensure_initialized()
        return self._manager.get_connection()
    
    def close_all(self):
        if self._manager and self._manager.pool:
            self._manager.pool.close_all()


# Instancias globales LAZY
inventory_pool = LazyConnectionPool()
stats_manager = LazyStatsManager()

# Cache para Settings
_settings_cache = {"data": None, "timestamp": 0, "lock": Lock()}
SETTINGS_CACHE_TTL = 60  # segundos


def init_connection_pools():
    """
    Función legacy para compatibilidad. Ya no es necesaria gracias a lazy init,
    pero se mantiene para no romper código existente.
    """
    # Ya no hace nada, la inicialización es automática
    pass


def _get_current_stats_db_file() -> str:
    """Genera el nombre del archivo de la BD de stats para el mes actual."""
    now = datetime.utcnow()
    return f"stats_{now.strftime('%Y_%m')}.sqlite"


def get_db_connection(db_file: str) -> sqlite3.Connection:
    """
    DEPRECADO: Mantener solo por compatibilidad.
    """
    conn = sqlite3.connect(db_file, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


# --- Funciones de Configuración de Bases de Datos ---

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
    conn = sqlite3.connect(INVENTORY_DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpes (
        mac TEXT PRIMARY KEY, 
        hostname TEXT, 
        model TEXT, 
        firmware TEXT, 
        ip_address TEXT,
        client_id INTEGER,
        first_seen DATETIME, 
        last_seen DATETIME,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
    )
    """)
    
    # Índices optimizados
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_aps_zona ON aps (zona_id)",
        "CREATE INDEX IF NOT EXISTS idx_aps_enabled ON aps (is_enabled) WHERE is_enabled = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_aps_last_status ON aps (last_status)",
        "CREATE INDEX IF NOT EXISTS idx_cpes_ip ON cpes (ip_address)",
        "CREATE INDEX IF NOT EXISTS idx_cpes_client ON cpes (client_id)",
        "CREATE INDEX IF NOT EXISTS idx_clients_status ON clients (service_status)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    conn.close()


def _setup_stats_db():
    """Crea las tablas en la base de datos de estadísticas del mes actual si no existen."""
    stats_db_file = _get_current_stats_db_file()
    conn = sqlite3.connect(stats_db_file)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ap_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        ap_host TEXT NOT NULL,
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpe_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        ap_host TEXT NOT NULL,
        cpe_mac TEXT NOT NULL,
        cpe_hostname TEXT,
        ip_address TEXT,
        signal INTEGER,
        signal_chain0 INTEGER,
        signal_chain1 INTEGER,
        noisefloor INTEGER,
        cpe_tx_power INTEGER,
        distance INTEGER,
        dl_capacity INTEGER,
        ul_capacity INTEGER,
        airmax_cinr_rx REAL,
        airmax_usage_rx REAL,
        airmax_cinr_tx REAL,
        airmax_usage_tx REAL,
        throughput_rx_kbps INTEGER,
        throughput_tx_kbps INTEGER,
        total_rx_bytes INTEGER,
        total_tx_bytes INTEGER,
        cpe_uptime INTEGER,
        eth_plugged BOOLEAN,
        eth_speed INTEGER,
        eth_cable_len INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disconnection_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        ap_host TEXT NOT NULL,
        cpe_mac TEXT NOT NULL,
        cpe_hostname TEXT,
        reason_code INTEGER,
        connection_duration INTEGER
    )
    """)
    
    # Índices críticos para performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_ap_stats_timestamp_host ON ap_stats_history(ap_host, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ap_stats_timestamp ON ap_stats_history(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_cpe_stats_timestamp_mac ON cpe_stats_history(cpe_mac, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_cpe_stats_ap_timestamp ON cpe_stats_history(ap_host, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_cpe_stats_timestamp ON cpe_stats_history(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_cpe_stats_ip ON cpe_stats_history(ip_address)",
        "CREATE INDEX IF NOT EXISTS idx_disconnection_timestamp ON disconnection_events(timestamp DESC)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    conn.close()


# --- Funciones de Settings con Cache ---

def get_all_settings() -> dict:
    """Obtiene todos los settings con cache de 60 segundos."""
    now = time.time()
    
    with _settings_cache["lock"]:
        if (_settings_cache["data"] is None or 
            now - _settings_cache["timestamp"] > SETTINGS_CACHE_TTL):
            
            with inventory_pool.get_connection() as conn:
                cursor = conn.execute("SELECT key, value FROM settings")
                _settings_cache["data"] = {row['key']: row['value'] for row in cursor.fetchall()}
                _settings_cache["timestamp"] = now
        
        return _settings_cache["data"].copy()


def update_settings(settings_to_update: dict):
    """Actualiza settings y limpia el cache."""
    with inventory_pool.get_connection() as conn:
        update_data = [(value, key) for key, value in settings_to_update.items()]
        conn.executemany("UPDATE settings SET value = ? WHERE key = ?", update_data)
        conn.commit()
    
    # Limpiar cache
    with _settings_cache["lock"]:
        _settings_cache["data"] = None


def get_setting(key: str) -> str | None:
    """Obtiene un setting específico usando el cache."""
    settings = get_all_settings()
    return settings.get(key)


# --- Funciones de APs ---

def get_ap_status(host: str) -> str | None:
    """Obtiene el status de un AP."""
    with inventory_pool.get_connection() as conn:
        cursor = conn.execute("SELECT last_status FROM aps WHERE host = ?", (host,))
        result = cursor.fetchone()
        return result['last_status'] if result else None


def update_ap_status(host: str, status: str, data: dict = None):
    """Actualiza el status de un AP con transacción optimizada."""
    with inventory_pool.get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = datetime.utcnow()
            
            if status == 'online' and data:
                host_info = data.get("host", {})
                interfaces = data.get("interfaces", [{}, {}])
                mac = interfaces[1].get("hwaddr") if len(interfaces) > 1 else None
                
                conn.execute("""
                UPDATE aps 
                SET mac = ?, hostname = ?, model = ?, firmware = ?, 
                    last_status = ?, last_seen = ?, last_checked = ?
                WHERE host = ?
                """, (
                    mac, host_info.get("hostname"), host_info.get("devmodel"),
                    host_info.get("fwversion"), status, now, now, host
                ))
            else:
                conn.execute(
                    "UPDATE aps SET last_status = ?, last_checked = ? WHERE host = ?",
                    (status, now, host)
                )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise


# --- Funciones de Guardado de Stats (OPTIMIZADAS) ---

def save_full_snapshot(ap_host: str, data: dict):
    """
    Función central que guarda un snapshot completo de datos con batch inserts optimizados.
    """
    if not data:
        return
    
    # Actualizar inventario de CPEs
    _update_cpe_inventory(data)
    
    # Obtener conexión con ATTACH ya configurado
    with stats_manager.get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        
        try:
            cursor = conn.cursor()
            timestamp = datetime.utcnow()
            ap_hostname = data.get("host", {}).get("hostname", ap_host)

            # Datos del AP
            wireless_info = data.get("wireless", {})
            throughput_info = wireless_info.get("throughput", {})
            polling_info = wireless_info.get("polling", {})
            ath0_status = data.get("interfaces", [{}, {}])[1].get("status", {})
            gps_info = data.get("gps", {})
            
            # Insert de stats del AP
            cursor.execute("""
                INSERT INTO ap_stats_history (
                    timestamp, ap_host, uptime, cpuload, freeram, client_count, noise_floor,
                    total_throughput_tx, total_throughput_rx, airtime_total_usage, 
                    airtime_tx_usage, airtime_rx_usage, frequency, chanbw, essid,
                    total_tx_bytes, total_rx_bytes, gps_lat, gps_lon, gps_sats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, ap_host, data.get("host", {}).get("uptime"),
                data.get("host", {}).get("cpuload"), data.get("host", {}).get("freeram"),
                wireless_info.get("count"), wireless_info.get("noisef"),
                throughput_info.get("tx"), throughput_info.get("rx"),
                polling_info.get("use"), polling_info.get("tx_use"), polling_info.get("rx_use"),
                wireless_info.get("frequency"), wireless_info.get("chanbw"),
                wireless_info.get("essid"), ath0_status.get("tx_bytes"),
                ath0_status.get("rx_bytes"), gps_info.get("lat"),
                gps_info.get("lon"), gps_info.get("sats")
            ))

            # BATCH INSERT para CPEs
            cpe_data_batch = []
            for cpe in wireless_info.get("sta", []):
                remote = cpe.get("remote", {})
                stats = cpe.get("stats", {})
                airmax = cpe.get("airmax", {})
                eth_info = remote.get("ethlist", [{}])[0]
                chainrssi = cpe.get('chainrssi', [None, None, None])

                cpe_data_batch.append((
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
            
            if cpe_data_batch:
                cursor.executemany("""
                    INSERT INTO cpe_stats_history (
                        timestamp, ap_host, cpe_mac, cpe_hostname, ip_address, signal, 
                        signal_chain0, signal_chain1, noisefloor, cpe_tx_power, distance, 
                        dl_capacity, ul_capacity, airmax_cinr_rx, airmax_usage_rx, 
                        airmax_cinr_tx, airmax_usage_tx, throughput_rx_kbps, throughput_tx_kbps, 
                        total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed, eth_cable_len
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, cpe_data_batch)
            
            # BATCH INSERT para eventos de desconexión
            disconnection_data = []
            for event in wireless_info.get("sta_disconnected", []):
                disconnection_data.append((
                    timestamp, ap_host, event.get("mac"), event.get("hostname"),
                    event.get("reason_code"), event.get("disconnect_duration")
                ))
            
            if disconnection_data:
                cursor.executemany("""
                    INSERT INTO disconnection_events 
                    (timestamp, ap_host, cpe_mac, cpe_hostname, reason_code, connection_duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, disconnection_data)

            conn.commit()
            print(f"✓ Datos de '{ap_hostname}' ({len(cpe_data_batch)} CPEs) guardados correctamente.")
            
        except Exception as e:
            conn.rollback()
            print(f"✗ Error guardando datos de '{ap_host}': {e}")
            raise


def _update_cpe_inventory(data: dict):
    """Actualiza la tabla de inventario de CPEs con batch upsert."""
    cpe_updates = []
    now = datetime.utcnow()
    
    for cpe in data.get("wireless", {}).get("sta", []):
        remote = cpe.get("remote", {})
        cpe_updates.append((
            cpe.get("mac"), remote.get("hostname"), remote.get("platform"),
            cpe.get("version"), cpe.get("lastip"), now, now
        ))
    
    if not cpe_updates:
        return
    
    with inventory_pool.get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.executemany("""
                INSERT INTO cpes (mac, hostname, model, firmware, ip_address, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mac) DO UPDATE SET
                    hostname = excluded.hostname,
                    model = excluded.model,
                    firmware = excluded.firmware,
                    ip_address = excluded.ip_address,
                    last_seen = excluded.last_seen
            """, cpe_updates)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise


# --- Funciones de Gestión de Usuarios ---

def get_all_users() -> List[Dict[str, Any]]:
    """Obtiene una lista de todos los usuarios de la base de datos (sin la contraseña)."""
    with inventory_pool.get_connection() as conn:
        cursor = conn.execute("""
            SELECT username, role, telegram_chat_id, receive_alerts, 
                   receive_announcements, disabled 
            FROM users 
            ORDER BY username
        """)
        return [dict(row) for row in cursor.fetchall()]


def create_user_in_db(username: str, hashed_password: str, role: str = 'admin') -> Dict[str, Any]:
    """Crea un nuevo usuario en la base de datos."""
    with inventory_pool.get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hashed_password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"El usuario '{username}' ya existe.")
    
    return {
        "username": username, "role": role, "disabled": False,
        "telegram_chat_id": None, "receive_alerts": False, "receive_announcements": False
    }


def update_user_in_db(username: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza los datos de un usuario."""
    if not updates:
        return None

    with inventory_pool.get_connection() as conn:
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(username)
        
        cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE username = ?", tuple(values))
        conn.commit()
        
        if cursor.rowcount == 0:
            return None
        
        cursor = conn.execute("""
            SELECT username, role, telegram_chat_id, receive_alerts, 
                   receive_announcements, disabled 
            FROM users 
            WHERE username = ?
        """, (username,))
        
        updated_user = cursor.fetchone()
        return dict(updated_user) if updated_user else None


def delete_user_from_db(username: str) -> bool:
    """Elimina un usuario de la base de datos."""
    with inventory_pool.get_connection() as conn:
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return cursor.rowcount > 0


def get_users_for_notification(notification_type: str) -> List[str]:
    """
    Obtiene los telegram_chat_id de los usuarios que han optado por recibir notificaciones.
    """
    if notification_type not in ['alert', 'announcement']:
        return []

    column_to_check = 'receive_alerts' if notification_type == 'alert' else 'receive_announcements'
    
    with inventory_pool.get_connection() as conn:
        query = f"""
            SELECT telegram_chat_id 
            FROM users 
            WHERE {column_to_check} = TRUE 
              AND telegram_chat_id IS NOT NULL 
              AND disabled = FALSE
        """
        cursor = conn.execute(query)
        return [row['telegram_chat_id'] for row in cursor.fetchall()]