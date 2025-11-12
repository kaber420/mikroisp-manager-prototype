# launcher.py
import sys
import os
import sqlite3
import getpass
import multiprocessing
import logging
import time
from dotenv import load_dotenv, find_dotenv
import secrets
from cryptography.fernet import Fernet

# --- Constante ---
ENV_FILE = ".env"

# --- Configuración del logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Launcher] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---
# Las funciones del asistente se quedan aquí, ya que no dependen de la app.
# ---

def run_setup_wizard():
    """
    Guía al usuario para crear o actualizar el archivo .env.
    """
    logging.info(f"Iniciando asistente de configuración para '{ENV_FILE}'...")
    print("\n--- Asistente de Configuración de µMonitor Pro ---")
    
    # Carga valores existentes si el archivo .env ya existe
    load_dotenv(ENV_FILE, encoding="utf-8")
    existing_port = os.getenv("UVICORN_PORT", "8000")
    existing_db_file = os.getenv("INVENTORY_DB_FILE", "inventory.sqlite")

    # Preguntar por el puerto
    while True:
        port_prompt = f"¿En qué puerto debe correr la App Web? (Actual: {existing_port}): "
        port_input = input(port_prompt).strip()
        port = port_input if port_input else existing_port
        try:
            port_num = int(port)
            if 1024 <= port_num <= 65535:
                break 
            else:
                print("Error: Por favor introduce un número de puerto entre 1024 y 65535.")
        except ValueError:
            print("Error: Eso no es un número de puerto válido.")

    # Preguntar por el archivo de la base de datos
    db_prompt = f"¿Nombre del archivo de la base de datos? (Actual: {existing_db_file}): "
    db_input = input(db_prompt).strip()
    db_file = db_input if db_input else existing_db_file

    # Generar claves de seguridad si no existen
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        print("Generando nueva SECRET_KEY para tokens JWT...")
        secret_key = secrets.token_hex(32)
    else:
        print("Usando SECRET_KEY existente.")

    encrypt_key = os.getenv("ENCRYPTION_KEY")
    if not encrypt_key:
        print("Generando nueva ENCRYPTION_KEY para cifrado de contraseñas...")
        encrypt_key = Fernet.generate_key().decode()
    else:
        print("Usando ENCRYPTION_KEY existente.")

    # Escribir el archivo .env
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Archivo de configuracion de µMonitor Pro\n")
            f.write(f"# Clave para firmar tokens JWT\n")
            f.write(f"SECRET_KEY=\"{secret_key}\"\n\n")
            f.write(f"# Clave para cifrar contraseñas de dispositivos\n")
            f.write(f"ENCRYPTION_KEY=\"{encrypt_key}\"\n\n")
            f.write(f"# Configuración del servidor\n")
            f.write(f"UVICORN_PORT={port}\n\n")
            f.write(f"# Configuración de la Base de Datos\n")
            f.write(f"INVENTORY_DB_FILE=\"{db_file}\"\n")
        
        print(f"\n¡Éxito! Configuración guardada en el archivo '{ENV_FILE}'.")
    except IOError as e:
        print(f"\nError Crítico: No se pudo escribir el archivo .env. Causa: {e}")
        sys.exit(1)

def check_and_create_first_user(db_file, get_pass_hash_func):
    """
    Verifica si existe la tabla de usuarios y si hay al menos un usuario.
    Si no, inicia el asistente para crear el primer administrador.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            logging.warning("La tabla 'users' no existe. Ejecutando configuración inicial de la base de datos.")
            # Importación local para evitar dependencias circulares
            from app.db.init_db import setup_databases
            setup_databases()

        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logging.warning("No se encontraron usuarios en la base de datos.")
            print("\n--- Asistente: Creación del Primer Administrador ---")
            
            username = input("Introduce el nombre de usuario para el administrador: ").strip()
            if not username:
                print("Error: El nombre de usuario no puede estar vacío.")
                sys.exit(1)

            while True:
                password = getpass.getpass("Introduce la contraseña: ")
                if not password:
                    print("La contraseña no puede estar vacía.")
                    continue
                password_confirm = getpass.getpass("Confirma la contraseña: ")
                if password == password_confirm:
                    break
                print("Las contraseñas no coinciden. Inténtalo de nuevo.")

            hashed_password = get_pass_hash_func(password)
            
            cursor.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hashed_password, 'admin') 
            )
            conn.commit()
            logging.info(f"Usuario administrador '{username}' creado exitosamente.")
            print(f"\n¡Usuario '{username}' creado! La aplicación ahora se iniciará.")
        else:
            logging.info(f"Se encontraron {user_count} usuario(s). Omitiendo la creación del primer usuario.")
            
    except sqlite3.Error as e:
         logging.error(f"Error de base de datos durante la verificación de usuario: {e}")
         sys.exit(1)
    finally:
        if conn:
            conn.close()

# ---
# Las funciones que inician procesos se quedan aquí.
# ---

def start_api_server():
    """
    Función objetivo para el proceso de la API. Importa sus dependencias localmente.
    """
    from uvicorn import Config, Server
    from app.main import app as fastapi_app
    
    server_host = os.getenv("UVICORN_HOST", "0.0.0.0")
    server_port = int(os.getenv("UVICORN_PORT", 8000))

    config = Config(app=fastapi_app, host=server_host, port=server_port, log_level="info")
    server = Server(config)
    
    # Para evitar logs duplicados, reconfiguramos el logger de uvicorn
    for handler in logging.getLogger().handlers:
        logging.getLogger("uvicorn").addHandler(handler)
        logging.getLogger("uvicorn.access").addHandler(handler)
    
    server.run()

# ---
# --- PUNTO DE ENTRADA PRINCIPAL ---
# ---
if __name__ == "__main__":
    
    # PASO 1: Manejar la configuración ANTES de importar cualquier cosa de la app
    if "--config" in sys.argv:
        run_setup_wizard()
        print("\nConfiguración guardada. Por favor, reinicia el launcher para aplicar los cambios.")
        sys.exit(0)
    
    if not os.path.exists(ENV_FILE):
        run_setup_wizard()

    # PASO 2: Cargar las variables de entorno AHORA
    load_dotenv(ENV_FILE, encoding="utf-8")
    logging.info(f"Archivo de configuración '{ENV_FILE}' cargado.")

    # PASO 3: AHORA SÍ, importar los módulos de la aplicación
    from app.monitor import run_monitor
    from app.billing_engine import run_billing_engine
    from app.db.base import INVENTORY_DB_FILE 
    from app.db.init_db import setup_databases
    from app.auth import get_password_hash

    # PASO 4: Inicializar la DB y el primer usuario (si es necesario)
    setup_databases()
    check_and_create_first_user(INVENTORY_DB_FILE, get_password_hash)

    # PASO 5: Iniciar la aplicación y sus procesos
    server_port = os.getenv("UVICORN_PORT", 8000)
    logging.info("Todo listo. Lanzando los servicios de la aplicación...")
    print("-" * 50)
    print("µMonitor Pro está arrancando...")
    print(f"API Web disponible en: http://localhost:{server_port}")
    print("Iniciando procesos en segundo plano: Monitor y Motor de Facturación.")
    print("Presiona Ctrl+C para detener la aplicación.")
    print("-" * 50)
    
    process_monitor = multiprocessing.Process(target=run_monitor, name="MonitorProcess")
    process_api = multiprocessing.Process(target=start_api_server, name="ApiProcess")
    process_billing = multiprocessing.Process(target=run_billing_engine, name="BillingProcess")

    try:
        process_monitor.start()
        process_api.start()
        process_billing.start()
        
        process_monitor.join()
        process_api.join()
        process_billing.join()

    except KeyboardInterrupt:
        logging.info("Se ha recibido una señal de interrupción (Ctrl+C).")
        print("\nDeteniendo los servicios de µMonitor Pro... Por favor, espera.")
        
        # Terminar procesos de forma segura
        for process in [process_api, process_monitor, process_billing]:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            
        logging.info("Todos los servicios han sido detenidos. Adiós.")
        sys.exit(0)