# app/api/cpes/models.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# (Modelos movidos desde cpes_api.py)
class CPEDetail(BaseModel):
    cpe_mac: str
    cpe_hostname: Optional[str] = None
    ip_address: Optional[str] = None
    signal: Optional[int] = None
    signal_chain0: Optional[int] = None
    signal_chain1: Optional[int] = None
    noisefloor: Optional[int] = None
    dl_capacity: Optional[int] = None
    ul_capacity: Optional[int] = None
    throughput_rx_kbps: Optional[int] = None
    throughput_tx_kbps: Optional[int] = None
    total_rx_bytes: Optional[int] = None
    total_tx_bytes: Optional[int] = None
    cpe_uptime: Optional[int] = None
    eth_plugged: Optional[bool] = None
    eth_speed: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class CPEGlobalInfo(CPEDetail):
    ap_host: Optional[str] = None
    ap_hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AssignedCPE(BaseModel):
    mac: str
    hostname: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)