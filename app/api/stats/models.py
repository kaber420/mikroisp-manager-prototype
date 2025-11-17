# app/api/stats/models.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

# --- Modelos Pydantic ---
class TopAP(BaseModel):
    hostname: Optional[str] = None
    host: str
    airtime_total_usage: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class TopCPE(BaseModel):
    cpe_hostname: Optional[str] = None
    cpe_mac: str
    ap_host: str
    signal: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)