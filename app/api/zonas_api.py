# app/api/zonas_api.py
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime

from ..auth import User, get_current_active_user
from ..db import zonas_db

router = APIRouter()

# --- Pydantic Models ---
class Zona(BaseModel):
    id: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)

class ZonaCreate(BaseModel):
    nombre: str

class ZonaUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    coordenadas_gps: Optional[str] = None
    notas_generales: Optional[str] = None
    notas_sensibles: Optional[str] = None

class ZonaInfra(BaseModel):
    id: Optional[int] = None
    zona_id: int
    direccion_ip_gestion: Optional[str] = None
    gateway_predeterminado: Optional[str] = None
    servidores_dns: Optional[str] = None
    vlans_utilizadas: Optional[str] = None
    equipos_criticos: Optional[str] = None
    proximo_mantenimiento: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)

class ZonaDocumento(BaseModel):
    id: int
    zona_id: int
    tipo: str
    nombre_original: str
    nombre_guardado: str
    descripcion: Optional[str] = None
    creado_en: datetime
    model_config = ConfigDict(from_attributes=True)

class ZonaDetail(Zona):
    direccion: Optional[str] = None
    coordenadas_gps: Optional[str] = None
    notas_generales: Optional[str] = None
    notas_sensibles: Optional[str] = None
    infraestructura: Optional[ZonaInfra] = None
    documentos: List[ZonaDocumento] = []

# --- API Endpoints ---
@router.post("/zonas", response_model=Zona, status_code=status.HTTP_201_CREATED)
def create_zona(zona: ZonaCreate, current_user: User = Depends(get_current_active_user)):
    try:
        new_zona = zonas_db.create_zona(zona.nombre)
        return new_zona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/zonas", response_model=List[Zona])
def get_all_zonas(current_user: User = Depends(get_current_active_user)):
    return zonas_db.get_all_zonas()

@router.get("/zonas/{zona_id}", response_model=Zona)
def get_zona(zona_id: int, current_user: User = Depends(get_current_active_user)):
    zona = zonas_db.get_zona_by_id(zona_id)
    if not zona:
        raise HTTPException(status_code=404, detail="Zona no encontrada.")
    return zona

@router.put("/zonas/{zona_id}", response_model=Zona)
def update_zona(zona_id: int, zona_update: ZonaUpdate, current_user: User = Depends(get_current_active_user)):
    updates = zona_update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar.")
    try:
        updated_zona = zonas_db.update_zona_details(zona_id, updates)
        if not updated_zona:
            raise HTTPException(status_code=404, detail="Zona no encontrada.")
        return updated_zona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/zonas/{zona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zona(zona_id: int, current_user: User = Depends(get_current_active_user)):
    try:
        deleted_count = zonas_db.delete_zona(zona_id)
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Zona no encontrada para eliminar.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return

# --- Endpoints de Detalles y Documentación ---
@router.get("/zonas/{zona_id}/details", response_model=ZonaDetail)
def get_zona_details(zona_id: int, current_user: User = Depends(get_current_active_user)):
    zona_data = zonas_db.get_zona_by_id(zona_id)
    if not zona_data:
        raise HTTPException(status_code=404, detail="Zona no encontrada.")
    
    infra_data = zonas_db.get_infra_by_zona_id(zona_id)
    docs_data = zonas_db.get_docs_by_zona_id(zona_id)
    
    response = ZonaDetail(**zona_data)
    if infra_data:
        response.infraestructura = ZonaInfra(**infra_data)
    response.documentos = [ZonaDocumento(**doc) for doc in docs_data]
    
    return response

@router.put("/zonas/{zona_id}/infraestructura", response_model=ZonaInfra)
def update_infraestructura(zona_id: int, infra_update: ZonaInfra, current_user: User = Depends(get_current_active_user)):
    update_data = infra_update.model_dump(exclude={'id', 'zona_id'}, exclude_unset=True)
    updated_infra = zonas_db.update_or_create_infra(zona_id, update_data)
    return updated_infra

@router.post("/zonas/{zona_id}/documentos", response_model=ZonaDocumento, status_code=status.HTTP_201_CREATED)
async def upload_documento(
    zona_id: int,
    file: UploadFile = File(...),
    descripcion: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    # Validar tipo de archivo
    file_type = 'image' if file.content_type.startswith("image/") else 'document'
    
    # Crear un nombre de archivo seguro y único
    file_extension = os.path.splitext(file.filename)[1]
    saved_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Definir la ruta de guardado
    save_dir = os.path.join("uploads", "zonas", str(zona_id))
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, saved_filename)
    
    # Guardar el archivo
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {e}")

    # Guardar en la base de datos
    doc_data = {
        "zona_id": zona_id,
        "tipo": file_type,
        "nombre_original": file.filename,
        "nombre_guardado": saved_filename,
        "descripcion": descripcion
    }
    new_doc = zonas_db.add_document(doc_data)
    return new_doc

@router.delete("/documentos/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_documento(doc_id: int, current_user: User = Depends(get_current_active_user)):
    deleted_rows = zonas_db.delete_document(doc_id)
    if deleted_rows == 0:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return