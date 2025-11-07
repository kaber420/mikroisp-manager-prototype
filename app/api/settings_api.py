# app/api/settings_api.py
from fastapi import APIRouter, Depends, status
from typing import Dict

from ..auth import User, get_current_active_user
from ..db import settings_db  # <-- CAMBIO AQUÍ

router = APIRouter()

# --- API Endpoints ---
@router.get("/settings", response_model=Dict[str, str])
def api_get_settings(current_user: User = Depends(get_current_active_user)):
    """
    Retrieves all global settings from the database.
    """
    return settings_db.get_all_settings()

@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def api_update_settings(settings: Dict[str, str], current_user: User = Depends(get_current_active_user)):
    """
    Updates global settings in the database.
    """
    settings_db.update_settings(settings)
    return