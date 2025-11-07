# app/api/users_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from ..auth import User, get_current_active_user, get_password_hash
# --- CAMBIO: Importación del módulo de DB de usuarios ---
from ..db import users_db

router = APIRouter()

# --- Pydantic Models ---
class UserResponse(BaseModel):
    username: str
    role: str
    telegram_chat_id: Optional[str] = None
    receive_alerts: bool
    receive_announcements: bool
    disabled: bool
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = 'admin'

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    receive_alerts: Optional[bool] = None
    receive_announcements: Optional[bool] = None
    disabled: Optional[bool] = None

# --- API Endpoints ---
@router.get("/users", response_model=List[UserResponse])
def api_get_all_users(current_user: User = Depends(get_current_active_user)):
    return users_db.get_all_users()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def api_create_user(user_data: UserCreate, current_user: User = Depends(get_current_active_user)):
    hashed_password = get_password_hash(user_data.password)
    try:
        new_user = users_db.create_user(
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{username}", response_model=UserResponse)
def api_update_user(username: str, user_data: UserUpdate, current_user: User = Depends(get_current_active_user)):
    updates = user_data.model_dump(exclude_unset=True)
    if 'password' in updates and updates['password']:
        updates['hashed_password'] = get_password_hash(updates.pop('password'))
    elif 'password' in updates:
        del updates['password']
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
        
    updated_user = users_db.update_user(username, updates)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return updated_user

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_user(username: str, current_user: User = Depends(get_current_active_user)):
    if username == current_user.username:
        raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta.")
    was_deleted = users_db.delete_user(username)
    if not was_deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return