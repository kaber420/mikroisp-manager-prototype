# app/db/init_db.py
import sqlite3
from datetime import datetime
from .base import get_db_connection, INVENTORY_DB_FILE

def _get_current_stats_db_file() -> str:
    now = datetime.utcnow()
    return f"stats_{now.strftime('%Y_%m')}.sqlite"

def setup_databases():
    print("Configurando la base de datos de inventario (inventory.sqlite)...")
    _setup_inventory_db()
    print("Configurando la base de datos de estadísticas mensuales...")
    _setup_stats_db()
    print("Configuración de bases de datos completada.")

def _setup_inventory_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- Tabla de Configuración (Settings) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    # --- VALORES POR DEFECTO ACTUALIZADOS ---
    default_settings = [
        ('telegram_bot_token', ''), ('telegram_chat_id', ''),
        ('default_monitor_interval', '300'), ('dashboard_refresh_interval', '60'),
        ('suspension_run_hour', '02:00') # <-- NUEVA SETTING AÑADIDA
    ]
    cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)
    
    # --- Tabla de Usuarios (Users) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, hashed_password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin',
        telegram_chat_id TEXT, receive_alerts BOOLEAN NOT NULL DEFAULT FALSE,
        receive_announcements BOOLEAN NOT NULL DEFAULT FALSE, disabled BOOLEAN NOT NULL DEFAULT FALSE
    )
    """)

    # --- Tablas de Zonas (Zonas) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zonas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    """)
    
    # Añadir nuevas columnas a 'zonas' de forma segura
    zona_columns = [col[1] for col in cursor.execute("PRAGMA table_info(zonas)").fetchall()]
    if 'direccion' not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN direccion TEXT;")
    if 'coordenadas_gps' not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN coordenadas_gps TEXT;")
    if 'notas_generales' not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN notas_generales TEXT;") # Para Markdown
    if 'notas_sensibles' not in zona_columns:
        cursor.execute("ALTER TABLE zonas ADD COLUMN notas_sensibles TEXT;") # Para datos cifrados

    # Nueva tabla para documentos/archivos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zona_documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zona_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('image', 'document', 'diagram')),
        nombre_original TEXT NOT NULL,
        nombre_guardado TEXT NOT NULL UNIQUE,
        descripcion TEXT,
        creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (zona_id) REFERENCES zonas(id) ON DELETE CASCADE
    );
    """)

    # Nueva tabla para datos de infraestructura
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zona_infraestructura (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zona_id INTEGER NOT NULL UNIQUE,
        direccion_ip_gestion TEXT,
        gateway_predeterminado TEXT,
        servidores_dns TEXT,
        vlans_utilizadas TEXT,
        equipos_criticos TEXT,
        proximo_mantenimiento DATE,
        FOREIGN KEY (zona_id) REFERENCES zonas(id) ON DELETE CASCADE
    );
    """)

    # --- Tablas de Dispositivos (APs, CPEs, Routers) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aps (
        host TEXT PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL, zona_id INTEGER,
        is_enabled BOOLEAN DEFAULT TRUE, monitor_interval INTEGER, mac TEXT, hostname TEXT, model TEXT, 
        firmware TEXT, last_status TEXT, first_seen DATETIME, last_seen DATETIME, last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """)
    
    # --- TABLA DE CLIENTES (MODIFICADA) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT, phone_number TEXT,
        whatsapp_number TEXT, email TEXT, telegram_contact TEXT, coordinates TEXT, notes TEXT,
        service_status TEXT NOT NULL DEFAULT 'active', 
        billing_day INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # (Se eliminó 'suspension_method TEXT' de esta tabla)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpes (
        mac TEXT PRIMARY KEY, hostname TEXT, model TEXT, firmware TEXT, ip_address TEXT, client_id INTEGER,
        first_seen DATETIME, last_seen DATETIME,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routers (
        host TEXT PRIMARY KEY, api_port INTEGER DEFAULT 8728, api_ssl_port INTEGER DEFAULT 8729,
        username TEXT NOT NULL, password TEXT NOT NULL, zona_id INTEGER, is_enabled BOOLEAN DEFAULT TRUE,
        hostname TEXT, model TEXT, firmware TEXT, last_status TEXT, last_checked DATETIME,
        FOREIGN KEY (zona_id) REFERENCES zonas (id) ON DELETE SET NULL
    )
    """)

    # --- INICIO DE NUEVAS TABLAS PARA CLIENTES Y FACTURACIÓN ---

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS client_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        router_host TEXT NOT NULL,
        service_type TEXT NOT NULL DEFAULT 'pppoe',
        pppoe_username TEXT UNIQUE,
        router_secret_id TEXT,
        profile_name TEXT,
        suspension_method TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
        FOREIGN KEY (router_host) REFERENCES routers(host) ON DELETE SET NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        monto REAL NOT NULL,
        fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP,
        mes_correspondiente TEXT NOT NULL,
        metodo_pago TEXT,
        notas TEXT,
        
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
    )
    """)

    # --- FIN DE NUEVAS TABLAS ---

    # --- Índices ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aps_zona ON aps (zona_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpes_ip ON cpes (ip_address);")
    
    # --- INICIO DE ÍNDICES PARA LAS NUEVAS TABLAS ---
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_client_id ON client_services (client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pagos_client_id ON pagos (client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pagos_mes ON pagos (client_id, mes_correspondiente);")

    # --- FIN DE ÍNDICES ---
    
    conn.commit()
    conn.close()

def _setup_stats_db():
    # Esta función está perfecta, no requiere cambios.
    stats_db_file = _get_current_stats_db_file()
    stats_conn = sqlite3.connect(stats_db_file)
    stats_conn.row_factory = sqlite3.Row
    cursor = stats_conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ap_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME NOT NULL, ap_host TEXT, uptime INTEGER,
        cpuload REAL, freeram INTEGER, client_count INTEGER, noise_floor INTEGER,
        total_throughput_tx INTEGER, total_throughput_rx INTEGER, airtime_total_usage INTEGER,
        airtime_tx_usage INTEGER, airtime_rx_usage INTEGER, frequency INTEGER, chanbw INTEGER,
        essid TEXT, total_tx_bytes INTEGER, total_rx_bytes INTEGER, gps_lat REAL, gps_lon REAL,
        gps_sats INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cpe_stats_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT, cpe_mac TEXT,
        cpe_hostname TEXT, ip_address TEXT, signal INTEGER, signal_chain0 INTEGER, signal_chain1 INTEGER,
        noisefloor INTEGER, cpe_tx_power INTEGER, distance INTEGER, dl_capacity INTEGER, ul_capacity INTEGER,
        airmax_cinr_rx REAL, airmax_usage_rx REAL, airmax_cinr_tx REAL, airmax_usage_tx REAL,
        throughput_rx_kbps INTEGER, throughput_tx_kbps INTEGER, total_rx_bytes INTEGER,
        total_tx_bytes INTEGER, cpe_uptime INTEGER, eth_plugged BOOLEAN, eth_speed INTEGER, eth_cable_len INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disconnection_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, ap_host TEXT, cpe_mac TEXT,
        cpe_hostname TEXT, reason_code INTEGER, connection_duration INTEGER
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_mac ON cpe_stats_history (cpe_mac);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpe_stats_ip ON cpe_stats_history (ip_address);")
    stats_conn.commit()
    stats_conn.close()