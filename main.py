# main.py

import sqlite3
import getpass
import multiprocessing
import subprocess
import logging
import sys
import time
from uvicorn import Config, Server

# Importamos las funciones y objetos necesarios de nuestros módulos
from monitor import run_monitor
from api import app as fastapi_app
from database import INVENTORY_DB_FILE, setup_databases
from auth import get_password_hash

# Configuración del logging para el lanzador
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Launcher] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_and_create_first_user():
    """
    Verifica si existe algún usuario en la base de datos. Si no, inicia
    un asistente interactivo para crear el primer usuario administrador.
    """
    try:
        conn = sqlite3.connect(INVENTORY_DB_FILE)
        cursor = conn.cursor()
        
        # Primero, asegurarnos de que la tabla 'users' existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            logging.warning("La tabla 'users' no existe. Ejecutando configuración inicial de la base de datos.")
            # Si la tabla no existe, setup_databases la creará
            setup_databases()

        # Ahora, verificar si hay usuarios
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

            hashed_password = get_password_hash(password)
            
            cursor.execute(
                "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
                (username, hashed_password)
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

def start_api_server():
    """
    Función objetivo para el proceso de la API.
    Configura y ejecuta el servidor Uvicorn para la aplicación FastAPI.
    """
    # Cambiamos el formato del log para el proceso de la API
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

    config = Config(
        app=fastapi_app, 
        host="0.0.0.0", 
        port=8000, 
        log_config=uvicorn_log_config
    )
    server = Server(config)
    
    # Uvicorn se ejecuta en el hilo/proceso actual
    server.run()


if __name__ == "__main__":
    # Asegurarnos de que las bases de datos están configuradas antes de cualquier otra cosa
    setup_databases()

    # Paso 1: Verificar y, si es necesario, crear el primer usuario.
    check_and_create_first_user()

    logging.info("Todo listo. Lanzando los servicios de la aplicación...")
    print("-" * 50)
    print("µMonitor Pro está arrancando...")
    print("API Web disponible en: http://localhost:8000")
    print("Presiona Ctrl+C para detener la aplicación.")
    print("-" * 50)
    
    # Paso 2: Crear los procesos para el monitor y la API
    # Usamos multiprocessing para que se ejecuten en paralelo de verdad
    process_monitor = multiprocessing.Process(target=run_monitor, name="MonitorProcess")
    process_api = multiprocessing.Process(target=start_api_server, name="ApiProcess")

    try:
        # Paso 3: Iniciar ambos procesos
        process_monitor.start()
        process_api.start()

        # El proceso principal espera a que ambos terminen (lo cual no sucederá
        # hasta que se interrumpa con Ctrl+C)
        process_monitor.join()
        process_api.join()

    except KeyboardInterrupt:
        logging.info("Se ha recibido una señal de interrupción (Ctrl+C).")
        print("\nDeteniendo los servicios de µMonitor Pro... Por favor, espera.")
        
        # Terminar los procesos hijos de forma ordenada
        if process_api.is_alive():
            process_api.terminate()
            process_api.join(timeout=5) # Esperar un poco a que termine
        
        if process_monitor.is_alive():
            process_monitor.terminate()
            process_monitor.join(timeout=5)
            
        logging.info("Todos los servicios han sido detenidos. Adiós.")
        sys.exit(0)