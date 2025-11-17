# app/api/users/models.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

# --- Pydantic Models (Movidos) ---
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