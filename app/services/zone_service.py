# app/services/zone_service.py
import os
import uuid
import aiofiles
from fastapi import UploadFile
from typing import List, Dict, Any, Optional
from ..db import zonas_db
from ..api.zonas.models import ZonaDetail, ZonaInfra, ZonaDocumento, ZonaNote

class ZoneService:
    
    def create_zona(self, nombre: str) -> Dict[str, Any]:
        try:
            new_zona = zonas_db.create_zona(nombre)
            return new_zona
        except ValueError as e: # Error de constraint UNIQUE
            raise ValueError(str(e))

    def get_all_zonas(self) -> List[Dict[str, Any]]:
        return zonas_db.get_all_zonas()

    def get_zona(self, zona_id: int) -> Dict[str, Any]:
        zona = zonas_db.get_zona_by_id(zona_id)
        if not zona:
            raise FileNotFoundError("Zona no encontrada.")
        return zona

    def update_zona(self, zona_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        if not update_data:
            raise ValueError("No se proporcionaron campos para actualizar.")
        try:
            updated_zona = zonas_db.update_zona_details(zona_id, update_data)
            if not updated_zona:
                raise FileNotFoundError("Zona no encontrada.")
            return updated_zona
        except ValueError as e: # Error de constraint UNIQUE
            raise ValueError(str(e))

    def delete_zona(self, zona_id: int):
        try:
            deleted_count = zonas_db.delete_zona(zona_id)
            if deleted_count == 0:
                raise FileNotFoundError("Zona no encontrada para eliminar.")
        except ValueError as e: # Error de constraint (APs/Routers asignados)
            raise ValueError(str(e))

    # --- Métodos de Detalles y Documentación ---

    def get_zona_details(self, zona_id: int) -> ZonaDetail:
        zona_data = zonas_db.get_zona_by_id(zona_id)
        if not zona_data:
            raise FileNotFoundError("Zona no encontrada.")
        
        infra_data = zonas_db.get_infra_by_zona_id(zona_id)
        docs_data = zonas_db.get_docs_by_zona_id(zona_id)
        notes_data = zonas_db.get_notes_by_zona_id(zona_id)
        
        response = ZonaDetail(**zona_data)
        if infra_data:
            response.infraestructura = ZonaInfra(**infra_data)
        response.documentos = [ZonaDocumento(**doc) for doc in docs_data]
        response.notes = [ZonaNote(**note) for note in notes_data]
        
        return response

    def update_infraestructura(self, zona_id: int, infra_data: Dict[str, Any]) -> Dict[str, Any]:
        updated_infra = zonas_db.update_or_create_infra(zona_id, infra_data)
        return updated_infra

    async def upload_documento(self, zona_id: int, file: UploadFile, descripcion: Optional[str]) -> Dict[str, Any]:
        file_type = 'image' if file.content_type.startswith("image/") else 'document'
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{uuid.uuid4()}{file_extension}"
        
        save_dir = os.path.join("uploads", "zonas", str(zona_id))
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, saved_filename)
        
        try:
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
        except Exception as e:
            raise Exception(f"No se pudo guardar el archivo: {e}")

        doc_data = {
            "zona_id": zona_id, "tipo": file_type,
            "nombre_original": file.filename, "nombre_guardado": saved_filename,
            "descripcion": descripcion
        }
        new_doc = zonas_db.add_document(doc_data)
        return new_doc

    def delete_documento(self, doc_id: int):
        deleted_rows = zonas_db.delete_document(doc_id)
        if deleted_rows == 0:
            raise FileNotFoundError("Documento no encontrado.")

    # --- Métodos de Notas ---

    def create_note_for_zona(self, zona_id: int, title: str, content: str, is_encrypted: bool) -> Dict[str, Any]:
        # We could add validation here if needed
        new_note = zonas_db.create_note(zona_id, title, content, is_encrypted)
        return new_note

    def get_note(self, note_id: int) -> Dict[str, Any]:
        note = zonas_db.get_note_by_id(note_id)
        if not note:
            raise FileNotFoundError("Nota no encontrada.")
        return note

    def update_note(self, note_id: int, title: str, content: str, is_encrypted: bool) -> Dict[str, Any]:
        updated_note = zonas_db.update_note(note_id, title, content, is_encrypted)
        if not updated_note:
            raise FileNotFoundError("Nota no encontrada para actualizar.")
        return updated_note

    def delete_note(self, note_id: int):
        deleted_count = zonas_db.delete_note(note_id)
        if deleted_count == 0:
            raise FileNotFoundError("Nota no encontrada para eliminar.")