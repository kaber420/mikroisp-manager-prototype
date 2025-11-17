# app/services/cpe_service.py
from typing import List, Dict, Any
from ..db import cpes_db

class CPEService:
    
    def get_unassigned_cpes(self) -> List[Dict[str, Any]]:
        return cpes_db.get_unassigned_cpes()

    def assign_cpe_to_client(self, mac: str, client_id: int) -> Dict[str, Any]:
        try:
            rows_affected = cpes_db.assign_cpe_to_client(mac, client_id)
            if rows_affected == 0:
                raise FileNotFoundError("CPE not found.")
        except ValueError as e:
            raise FileNotFoundError(str(e)) # Client ID no encontrado
            
        updated_cpe = cpes_db.get_cpe_by_mac(mac)
        if not updated_cpe:
            raise Exception("Could not retrieve CPE after assignment.")
        return updated_cpe

    def unassign_cpe(self, mac: str) -> Dict[str, Any]:
        rows_affected = cpes_db.unassign_cpe(mac)
        if rows_affected == 0:
            raise FileNotFoundError("CPE not found.")
        
        unassigned_cpe = cpes_db.get_cpe_by_mac(mac)
        if not unassigned_cpe:
            raise Exception("Could not retrieve CPE after unassignment.")
        return unassigned_cpe

    def get_all_cpes_globally(self) -> List[Dict[str, Any]]:
        try:
            return cpes_db.get_all_cpes_globally()
        except RuntimeError as e:
            raise Exception(str(e)) # Error de DB