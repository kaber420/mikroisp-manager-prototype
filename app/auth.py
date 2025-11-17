# app/auth.py
import os  # <--- 1. AÑADIDO
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .db import users_db

# --- Configuración de Seguridad ---
# --- 2. LÍNEAS MODIFICADAS ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Esto detendrá la app si la clave no está definida, evitando que corra en modo inseguro.
    raise RuntimeError("FATAL: SECRET_KEY no está configurada. La aplicación no puede iniciar de forma segura.")
    
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_COOKIE_NAME = "umonitorpro_access_token"

# --- Modelos de Datos ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: bool = False

# --- Funciones de Contraseña ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- Funciones de Token JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencias de Autenticación (Lógica Unificada) ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/access-token", auto_error=False)

# --- CORRECCIÓN EN LA FIRMA DE LA FUNCIÓN ---
async def get_current_active_user(
    token_from_bearer: Optional[str] = Depends(oauth2_scheme),
    request: Request = None  # Hacemos request opcional
) -> User:
    token = token_from_bearer
    # Si no hay bearer token y SÍ tenemos el objeto request, buscamos en la cookie
    if token is None and request:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = users_db.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return User(**user.model_dump())