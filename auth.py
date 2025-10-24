# auth.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

# --- CAMBIO 1: Importamos 'Request' para poder leer las cookies ---
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from database import INVENTORY_DB_FILE

# --- Configuración de Seguridad ---
SECRET_KEY = "a_very_secret_key_change_me_in_production"  # ¡IMPORTANTE! Cambia esta clave
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # El token expira en 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CAMBIO 2: Centralizamos el nombre de la cookie en una constante ---
ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"

# --- Modelos de Datos ---
class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: bool = False

class UserInDB(User):
    hashed_password: str


# --- Funciones de Contraseña ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña plana coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)


# --- Funciones de Base de Datos para Usuarios ---
def get_user(username: str) -> Optional[UserInDB]:
    """Busca un usuario en la base de datos por su nombre de usuario."""
    conn = sqlite3.connect(INVENTORY_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    conn.close()
    if user_row:
        return UserInDB(**dict(user_row))
    return None

# --- Funciones de Token JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un nuevo token de acceso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Aseguramos que el delta de tiempo se use correctamente
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- CAMBIO 3: Nueva dependencia para extraer el token directamente de la cookie ---
async def get_token_from_cookie(request: Request) -> str:
    """
    Dependencia que extrae el token JWT de la cookie de la petición.
    Si la cookie no existe, lanza un error 401.
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated, no token provided",
        )
    return token

# --- CAMBIO 4: La dependencia principal ahora usa nuestra nueva función ---
async def get_current_active_user(token: str = Depends(get_token_from_cookie)) -> User:
    """
    Dependencia de FastAPI para obtener el usuario activo a partir de un token
    obtenido de la cookie. Esta es la única función que protegerá nuestros endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return User(**user.model_dump())