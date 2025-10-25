# main.py - Lanzador principal para µMonitor Pro
# Versión: 0.3.0 - Optimizado para pools de conexión lazy
# Autor: Kaber420, Gemini pro 2.5, claude sonnet 4.5 
import sqlite3
import getpass
import multiprocessing
import logging
import sys
import signal
from uvicorn import Config, Server

# Importamos las funciones y objetos necesarios de nuestros módulos
from monitor import run_monitor
from api import app as fastapi_app
from database import (
    INVENTORY_DB_FILE, 
    setup_databases
    # Ya NO importamos init_connection_pools - no es necesario con lazy init
)
from auth import get_password_hash

# Configuración del logging para el lanzador
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


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
            logger.warning("La tabla 'users' no existe. Ejecutando configuración inicial de la base de datos.")
            conn.close()
            # Si la tabla no existe, setup_databases la creará
            setup_databases()
            # Reconectar después del setup
            conn = sqlite3.connect(INVENTORY_DB_FILE)
            cursor = conn.cursor()

        # Ahora, verificar si hay usuarios
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logger.warning("No se encontraron usuarios en la base de datos.")
            print("\n" + "=" * 70)
            print("  ASISTENTE DE CONFIGURACIÓN INICIAL")
            print("  Creación del Primer Administrador")
            print("=" * 70)
            
            username = input("\nIntroduce el nombre de usuario para el administrador: ").strip()
            if not username:
                print("❌ Error: El nombre de usuario no puede estar vacío.")
                sys.exit(1)

            while True:
                password = getpass.getpass("Introduce la contraseña: ")
                if not password:
                    print("⚠️  La contraseña no puede estar vacía.")
                    continue
                password_confirm = getpass.getpass("Confirma la contraseña: ")
                if password == password_confirm:
                    break
                print("⚠️  Las contraseñas no coinciden. Inténtalo de nuevo.")

            hashed_password = get_password_hash(password)
            
            cursor.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hashed_password, 'admin')
            )
            conn.commit()
            logger.info(f"✓ Usuario administrador '{username}' creado exitosamente.")
            print(f"\n✓ ¡Usuario '{username}' creado exitosamente!")
            print("  La aplicación ahora se iniciará...\n")
        else:
            logger.info(f"✓ Se encontraron {user_count} usuario(s) en la base de datos.")
            
    except sqlite3.Error as e:
        logger.error(f"❌ Error de base de datos durante la verificación de usuario: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def start_api_server():
    """
    Función objetivo para el proceso de la API.
    Configura y ejecuta el servidor Uvicorn para la aplicación FastAPI.
    """
    # Configuración personalizada del logging para Uvicorn
    uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s - %(levelname)s - [API Server] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s - INFO - [API Server] - %(client_addr)s - "%(request_line)s" %(status_code)s',
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    config = Config(
        app=fastapi_app, 
        host="0.0.0.0", 
        port=8000, 
        log_config=uvicorn_log_config,
        access_log=True
    )
    server = Server(config)
    
    logger.info("✓ Servidor API iniciado en http://0.0.0.0:8000")
    
    # Uvicorn se ejecuta en el hilo/proceso actual
    server.run()


def cleanup_resources():
    """
    Limpia los recursos de conexiones de base de datos al finalizar.
    """
    try:
        # Importar solo cuando sea necesario
        from database import inventory_pool, stats_manager
        
        logger.info("Cerrando pools de conexiones...")
        inventory_pool.close_all()
        stats_manager.close_all()
        
        logger.info("✓ Recursos de base de datos liberados correctamente.")
    except Exception as e:
        logger.error(f"Error al cerrar conexiones: {e}")


def signal_handler(signum, frame):
    """
    Manejador de señales para shutdown graceful.
    """
    logger.info(f"\n✋ Señal {signum} recibida. Iniciando shutdown graceful...")
    cleanup_resources()
    sys.exit(0)


def main():
    """
    Función principal que orquesta el inicio de la aplicación.
    """
    # Registrar manejadores de señales para cleanup
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("\n" + "=" * 70)
    print("  µMonitor Pro - Sistema de Monitoreo Ubiquiti")
    print("  Versión 1.2.0 - Optimizado")
    print("=" * 70 + "\n")
    
    # Paso 1: Configurar las bases de datos
    logger.info("⚙️  Configurando bases de datos...")
    setup_databases()
    
    # Paso 2: Ya NO es necesario inicializar pools manualmente
    # Los pools usan lazy initialization y se crean automáticamente al usarse
    logger.info("✓ Sistema configurado con pools de conexión lazy (se inicializan automáticamente)")
    
    # Paso 3: Verificar y crear el primer usuario si es necesario
    check_and_create_first_user()

    # Paso 4: Mostrar información de inicio
    logger.info("🚀 Lanzando los servicios de la aplicación...")
    print("\n" + "-" * 70)
    print("  SERVICIOS ACTIVOS:")
    print("  • Monitor de Red: Ejecutándose en segundo plano")
    print("  • API Web: http://localhost:8000")
    print("  • Dashboard: http://localhost:8000/")
    print("\n  Presiona Ctrl+C para detener la aplicación.")
    print("-" * 70 + "\n")
    
    # Paso 5: Crear los procesos para el monitor y la API
    # Usamos multiprocessing para ejecución paralela real
    process_monitor = multiprocessing.Process(
        target=run_monitor, 
        name="MonitorProcess",
        daemon=False
    )
    process_api = multiprocessing.Process(
        target=start_api_server, 
        name="ApiProcess",
        daemon=False
    )

    try:
        # Paso 6: Iniciar ambos procesos
        logger.info("🔄 Iniciando proceso de monitoreo...")
        process_monitor.start()
        
        logger.info("🔄 Iniciando servidor API...")
        process_api.start()
        
        logger.info("✓ Todos los servicios están activos y funcionando.")

        # El proceso principal espera a que ambos terminen
        # (lo cual no sucederá hasta que se interrumpa con Ctrl+C)
        process_monitor.join()
        process_api.join()

    except KeyboardInterrupt:
        logger.info("\n✋ Interrupción detectada (Ctrl+C). Deteniendo servicios...")
        print("\n⏳ Deteniendo µMonitor Pro... Por favor, espera.\n")
        
        # Terminar los procesos hijos de forma ordenada
        if process_api.is_alive():
            logger.info("⏹️  Deteniendo servidor API...")
            process_api.terminate()
            process_api.join(timeout=10)
            if process_api.is_alive():
                logger.warning("⚠️  Forzando cierre del servidor API...")
                process_api.kill()
                process_api.join()
        
        if process_monitor.is_alive():
            logger.info("⏹️  Deteniendo monitor de red...")
            process_monitor.terminate()
            process_monitor.join(timeout=10)
            if process_monitor.is_alive():
                logger.warning("⚠️  Forzando cierre del monitor...")
                process_monitor.kill()
                process_monitor.join()
        
        # Limpiar recursos
        cleanup_resources()
        
        print("\n" + "=" * 70)
        print("  ✓ µMonitor Pro detenido correctamente")
        print("  ¡Hasta pronto!")
        print("=" * 70 + "\n")
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ Error crítico en la aplicación: {e}", exc_info=True)
        
        # Intentar detener los procesos si aún están vivos
        if 'process_api' in locals() and process_api.is_alive():
            process_api.terminate()
            process_api.join(timeout=5)
        
        if 'process_monitor' in locals() and process_monitor.is_alive():
            process_monitor.terminate()
            process_monitor.join(timeout=5)
        
        cleanup_resources()
        sys.exit(1)


if __name__ == "__main__":
    # Configuración específica para multiprocessing en diferentes plataformas
    # Esto previene problemas en Windows y macOS
    multiprocessing.set_start_method('spawn', force=True)
    
    # Ejecutar la función principal
    main()