# app/api/users/main.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...auth import User, get_current_active_user
from ...services.user_service import UserService
from .models import UserResponse, UserCreate, UserUpdate

router = APIRouter()

# --- Dependencia del Inyector de Servicio ---
def get_user_service() -> UserService:
    return UserService()

# --- API Endpoints ---
@router.get("/users", response_model=List[UserResponse])
def api_get_all_users(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    return service.get_all_users()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def api_create_user(
    user_data: UserCreate, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        new_user = service.create_user(user_data.model_dump())
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{username}", response_model=UserResponse)
def api_update_user(
    username: str, 
    user_data: UserUpdate, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        updated_user = service.update_user(username, user_data.model_dump(exclude_unset=True))
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_user(
    username: str, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    if username == current_user.username:
        raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta.")
    try:
        service.delete_user(username)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))