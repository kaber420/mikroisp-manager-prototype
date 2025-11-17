# app/api/zonas/models.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime

# --- Modelos Pydantic (Movidos) ---
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



# --- Modelos de Notas ---

class ZonaNoteBase(BaseModel):

    title: str

    content: Optional[str] = None

    is_encrypted: bool = False



class ZonaNoteCreate(ZonaNoteBase):

    pass



class ZonaNoteUpdate(ZonaNoteBase):

    pass



class ZonaNote(ZonaNoteBase):

    id: int

    zona_id: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ZonaDetail(Zona):

    direccion: Optional[str] = None

    coordenadas_gps: Optional[str] = None

    infraestructura: Optional[ZonaInfra] = None

    documentos: List[ZonaDocumento] = []

    notes: List[ZonaNote] = []
