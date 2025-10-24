# create_user.py
import sqlite3
import getpass
from passlib.context import CryptContext

INVENTORY_DB_FILE = "inventory.sqlite"

# Usamos el mismo contexto de hashing que usará la aplicación
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

def create_user():
    """
    Script de línea de comandos para crear un nuevo usuario en la base de datos.
    """
    print("--- Creación de Nuevo Usuario para µMonitor Pro ---")
    
    # Solicitar nombre de usuario
    username = input("Introduce el nombre de usuario: ").strip()
    if not username:
        print("El nombre de usuario no puede estar vacío.")
        return

    # Solicitar y confirmar contraseña de forma segura
    while True:
        password = getpass.getpass("Introduce la contraseña: ")
        if not password:
            print("La contraseña no puede estar vacía.")
            continue
        password_confirm = getpass.getpass("Confirma la contraseña: ")
        if password == password_confirm:
            break
        print("Las contraseñas no coinciden. Inténtalo de nuevo.")

    # Generar el hash de la contraseña
    hashed_password = get_password_hash(password)

    try:
        # Conectar a la base de datos y crear la tabla si no existe
        conn = sqlite3.connect(INVENTORY_DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            hashed_password TEXT NOT NULL,
            disabled BOOLEAN NOT NULL DEFAULT FALSE
        )
        """)
        
        # Insertar el nuevo usuario
        cursor.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        print(f"\n¡Usuario '{username}' creado exitosamente!")

    except sqlite3.IntegrityError:
        print(f"\nError: El usuario '{username}' ya existe.")
    except sqlite3.Error as e:
        print(f"\nError de base de datos: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_user()