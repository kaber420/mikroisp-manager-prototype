# app/api/aps/models.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

"""
Este archivo contiene los modelos Pydantic (contratos de datos) 
que la API de APs utiliza.
"""

class AP(BaseModel):
    host: str
    username: str
    zona_id: Optional[int] = None
    is_enabled: bool
    monitor_interval: Optional[int] = None
    hostname: Optional[str] = None
    model: Optional[str] = None
    mac: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None
    client_count: Optional[int] = None
    airtime_total_usage: Optional[int] = None
    airtime_tx_usage: Optional[int] = None
    airtime_rx_usage: Optional[int] = None
    total_throughput_tx: Optional[int] = None
    total_throughput_rx: Optional[int] = None
    noise_floor: Optional[int] = None
    chanbw: Optional[int] = None
    frequency: Optional[int] = None
    essid: Optional[str] = None
    total_tx_bytes: Optional[int] = None
    total_rx_bytes: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_sats: Optional[int] = None
    zona_nombre: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class APCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: int
    is_enabled: bool = True
    monitor_interval: Optional[int] = None

class APUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    is_enabled: Optional[bool] = None
    monitor_interval: Optional[int] = None

class CPEDetail(BaseModel):
    timestamp: Optional[datetime] = None
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

class APLiveDetail(AP):
    clients: List[CPEDetail]

class HistoryDataPoint(BaseModel):
    timestamp: datetime
    client_count: Optional[int] = None
    airtime_total_usage: Optional[int] = None
    total_throughput_tx: Optional[int] = None
    total_throughput_rx: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class APHistoryResponse(BaseModel):
    host: str
    hostname: Optional[str] = None
    history: List[HistoryDataPoint]
    model_config = ConfigDict(from_attributes=True)