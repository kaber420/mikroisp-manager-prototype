# app/services/settings_service.py
from typing import Dict
from ..db import settings_db

class SettingsService:

    def get_all_settings(self) -> Dict[str, str]:
        return settings_db.get_all_settings()

    def update_settings(self, settings: Dict[str, str]):
        settings_db.update_settings(settings)