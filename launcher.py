# launcher.py
import sys
import os
import sqlite3
import getpass
import multiprocessing
import logging
import time
from dotenv import load_dotenv, find_dotenv

# --- Imports para el Asistente ---
import secrets
from cryptography.fernet import Fernet

# --- Constante ---
ENV_FILE = ".env"

# --- Configuración del logging ---
# (Sin cambios)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Launcher] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def run_setup_wizard():
    # (Sin cambios)
    logging.info(f"Iniciando asistente de configuración para '{ENV_FILE}'...")
    print("--- Asistente de Configuración de µMonitor Pro ---")
    
    load_dotenv(ENV_FILE, encoding="utf-8")
    existing_port = os.getenv("UVICORN_PORT", "8000")
    existing_db_file = os.getenv("INVENTORY_DB_FILE", "inventory.sqlite")

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

    db_prompt = f"¿Nombre del archivo de la base de datos? (Actual: {existing_db_file}): "
    db_input = input(db_prompt).strip()
    db_file = db_input if db_input else existing_db_file

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

    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Archivo de configuracion de µMonitor Pro\n") # <-- CORREGIDO
            f.write(f"# Clave para firmar tokens JWT\n")
            f.write(f"SECRET_KEY=\"{secret_key}\"\n\n")
            f.write(f"# Clave para cifrar contraseñas de routers\n")
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
    # (Sin cambios)
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            logging.warning("La tabla 'users' no existe. Ejecutando configuración inicial de la base de datos.")
            from app.db.init_db import setup_databases
            setup_databases()

        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logging.warning("No se encontraron usuarios en la base de datos.")
            print("--- Asistente de Configuración Inicial: Creación del Primer Administrador ---")
            
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

# --- CAMBIO: La función 'start_api_server' ahora importa sus propios módulos ---
def start_api_server():
    """
    Función objetivo para el proceso de la API.
    """
    # --- CAMBIO: Importaciones movidas AQUÍ ---
    from uvicorn import Config, Server
    from app.main import app as fastapi_app

    uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s - %(levelname)s - [API Server] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        },
    }

    server_host = os.getenv("UVICORN_HOST", "0.0.0.0")
    server_port = int(os.getenv("UVICORN_PORT", 8000))

    config = Config(
         app=fastapi_app, 
        host=server_host,
        port=server_port,
        log_config=uvicorn_log_config
    )
    server = Server(config)
    server.run()


# --- PUNTO DE ENTRADA PRINCIPAL ---

if __name__ == "__main__":
    
    # --- PASO 1: Manejar la configuración ---
    if "--config" in sys.argv:
        run_setup_wizard()
        print("\nConfiguración guardada. Por favor, reinicia el servidor para aplicar los cambios.")
        sys.exit(0)
    
    if not os.path.exists(ENV_FILE):
        run_setup_wizard()

    # --- PASO 2: Cargar las variables de entorno ---
    load_dotenv(ENV_FILE, encoding="utf-8")
    logging.info(f"Archivo de configuración '{ENV_FILE}' cargado.")

    # --- PASO 3: Importar módulos de la App ---
    # --- CAMBIO: Ya no importamos 'Config', 'Server', ni 'fastapi_app' aquí ---
    from app.monitor import run_monitor
    from app.db.base import INVENTORY_DB_FILE 
    from app.db.init_db import setup_databases
    from app.auth import get_password_hash

    # --- PASO 4: Inicializar la DB y el primer usuario ---
    setup_databases()
    check_and_create_first_user(INVENTORY_DB_FILE, get_password_hash)

    # --- PASO 5: Iniciar la aplicación ---
    server_port = os.getenv("UVICORN_PORT", 8000)
    logging.info("Todo listo. Lanzando los servicios de la aplicación...")
    print("-" * 50)
    print("µMonitor Pro está arrancando...")
    print(f"API Web disponible en: http://localhost:{server_port}")
    print("Presiona Ctrl+C para detener la aplicación.")
    print("-" * 50)
    
    process_monitor = multiprocessing.Process(target=run_monitor, name="MonitorProcess")
    
    # --- CAMBIO: Se elimina el argumento 'args' ---
    process_api = multiprocessing.Process(
        target=start_api_server, 
        name="ApiProcess"
        # args=(fastapi_app, Config, Server) <-- LÍNEA ELIMINADA
    )

    try:
        process_monitor.start()
        process_api.start()
        process_monitor.join()
        process_api.join()

    except KeyboardInterrupt:
        # (Sin cambios)
        logging.info("Se ha recibido una señal de interrupción (Ctrl+C).")
        print("\nDeteniendo los servicios de µMonitor Pro... Por favor, espera.")
        
        if process_api.is_alive():
            process_api.terminate()
            process_api.join(timeout=5)
        
        if process_monitor.is_alive():
             process_monitor.terminate()
             process_monitor.join(timeout=5)
            
        logging.info("Todos los servicios han sido detenidos. Adiós.")
        sys.exit(0)