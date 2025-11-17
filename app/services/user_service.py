# app/services/user_service.py
from typing import List, Dict, Any, Optional
from ..db import users_db
from ..auth import get_password_hash

class UserService:
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        return users_db.get_all_users()

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        hashed_password = get_password_hash(user_data['password'])
        try:
            new_user = users_db.create_user(
                username=user_data['username'],
                hashed_password=hashed_password,
                role=user_data['role']
            )
            return new_user
        except ValueError as e: # Error de constraint UNIQUE
            raise ValueError(str(e))

    def update_user(self, username: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        updates = user_data.copy()
        
        if 'password' in updates and updates['password']:
            updates['hashed_password'] = get_password_hash(updates.pop('password'))
        elif 'password' in updates:
            del updates['password']
        
        if not updates:
            raise ValueError("No hay campos para actualizar.")
            
        updated_user = users_db.update_user(username, updates)
        if not updated_user:
            raise FileNotFoundError("Usuario no encontrado.")
        return updated_user

    def delete_user(self, username: str):
        was_deleted = users_db.delete_user(username)
        if not was_deleted:
            raise FileNotFoundError("Usuario no encontrado.")