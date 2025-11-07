# app/api/aps_api.py
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..auth import User, get_current_active_user
from ..core.ap_client import UbiquitiClient
from ..db import aps_db, settings_db, stats_db
from ..db.base import get_stats_db_connection

router = APIRouter()

# --- Modelos Pydantic (Completos) ---
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
    # --- INICIO DE LA CORRECCIÓN ---
    timestamp: Optional[datetime] = None  # <-- CAMPO AÑADIDO PARA CORREGIR EL ERROR
    # --- FIN DE LA CORRECCIÓN ---
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

class APHistoryResponse(BaseModel):
    host: str
    hostname: Optional[str]
    history: List[HistoryDataPoint]

# --- Dependencia de DB (solo para stats) ---
def get_stats_db():
    conn = get_stats_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()

# --- Endpoints de la API ---

@router.post("/aps", response_model=AP, status_code=status.HTTP_201_CREATED)
def create_ap(ap: APCreate, current_user: User = Depends(get_current_active_user)):
    ap_data = ap.model_dump()
    if ap_data.get("monitor_interval") is None:
        default_interval_str = settings_db.get_setting('default_monitor_interval')
        ap_data["monitor_interval"] = int(default_interval_str) if default_interval_str and default_interval_str.isdigit() else 300
    try:
        new_ap = aps_db.create_ap_in_db(ap_data)
        return new_ap
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/aps", response_model=List[AP])
def get_all_aps(current_user: User = Depends(get_current_active_user)):
    return aps_db.get_all_aps_with_stats()

@router.get("/aps/{host}", response_model=AP)
def get_ap(host: str, current_user: User = Depends(get_current_active_user)):
    ap = aps_db.get_ap_by_host_with_stats(host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP no encontrado.")
    return ap

@router.put("/aps/{host}", response_model=AP)
def update_ap(host: str, ap_update: APUpdate, current_user: User = Depends(get_current_active_user)):
    update_fields = ap_update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar.")
    
    rows_affected = aps_db.update_ap_in_db(host, update_fields)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="AP no encontrado.")
        
    updated_ap_data = aps_db.get_ap_by_host_with_stats(host)
    if not updated_ap_data:
        raise HTTPException(status_code=404, detail="No se pudo recuperar el AP después de la actualización.")
    return updated_ap_data

@router.delete("/aps/{host}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ap(host: str, current_user: User = Depends(get_current_active_user)):
    rows_affected = aps_db.delete_ap_from_db(host)
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="AP no encontrado para eliminar.")
    return

@router.get("/aps/{host}/cpes", response_model=List[CPEDetail])
def get_cpes_for_ap(host: str, current_user: User = Depends(get_current_active_user)):
    """Obtiene los CPEs conectados a un AP específico desde el último snapshot guardado."""
    return stats_db.get_cpes_for_ap_from_stats(host)

@router.get("/aps/{host}/live", response_model=APLiveDetail)
def get_ap_live_data(host: str, current_user: User = Depends(get_current_active_user)):
    ap_credentials = aps_db.get_ap_credentials(host)
    if not ap_credentials:
        raise HTTPException(status_code=404, detail="AP no encontrado en el inventario.")

    client = UbiquitiClient(host=host, username=ap_credentials['username'], password=ap_credentials['password'])
    status_data = client.get_status_data()

    if not status_data:
        raise HTTPException(status_code=503, detail="No se pudo obtener datos del AP. Puede estar offline.")
    
    host_info = status_data.get("host", {})
    wireless_info = status_data.get("wireless", {})
    ath0_status = status_data.get("interfaces", [{}, {}])[1].get("status", {})
    gps_info = status_data.get("gps", {})
    throughput_info = wireless_info.get("throughput", {})
    polling_info = wireless_info.get("polling", {})
    
    clients_list = []
    for cpe_data in wireless_info.get("sta", []):
        remote = cpe_data.get("remote", {})
        stats_data = cpe_data.get("stats", {})
        airmax = cpe_data.get("airmax", {})
        eth_info = remote.get("ethlist", [{}])[0]
        chainrssi = cpe_data.get('chainrssi', [None, None, None])

        clients_list.append(CPEDetail(
            cpe_mac=cpe_data.get("mac"),
            cpe_hostname=remote.get("hostname"),
            ip_address=cpe_data.get("lastip"),
            signal=cpe_data.get("signal"),
            signal_chain0=chainrssi[0],
            signal_chain1=chainrssi[1],
            noisefloor=cpe_data.get("noisefloor"),
            dl_capacity=airmax.get("dl_capacity"),
            ul_capacity=airmax.get("ul_capacity"),
            throughput_rx_kbps=remote.get('rx_throughput'),
            throughput_tx_kbps=remote.get('tx_throughput'),
            total_rx_bytes=stats_data.get('rx_bytes'),
            total_tx_bytes=stats_data.get('tx_bytes'),
            cpe_uptime=remote.get('uptime'),
            eth_plugged=eth_info.get('plugged'),
            eth_speed=eth_info.get('speed')
        ))

    return APLiveDetail(
        host=host,
        username=ap_credentials['username'],
        is_enabled=True,
        hostname=host_info.get("hostname"),
        model=host_info.get("devmodel"),
        mac=status_data.get("interfaces", [{}, {}])[1].get("hwaddr"),
        firmware=host_info.get("fwversion"),
        last_status='online',
        client_count=wireless_info.get("count"),
        noise_floor=wireless_info.get("noisef"),
        chanbw=wireless_info.get("chanbw"),
        frequency=wireless_info.get("frequency"),
        essid=wireless_info.get("essid"),
        total_tx_bytes=ath0_status.get("tx_bytes"),
        total_rx_bytes=ath0_status.get("rx_bytes"),
        gps_lat=gps_info.get("lat"),
        gps_lon=gps_info.get("lon"),
        gps_sats=gps_info.get("sats"),
        total_throughput_tx=throughput_info.get("tx"),
        total_throughput_rx=throughput_info.get("rx"),
        airtime_total_usage=polling_info.get("use"),
        airtime_tx_usage=polling_info.get("tx_use"),
        airtime_rx_usage=polling_info.get("rx_use"),
        clients=clients_list
    )

@router.get("/aps/{host}/history", response_model=APHistoryResponse)
def get_ap_history(
    host: str,
    period: str = "24h",
    stats_conn: Optional[sqlite3.Connection] = Depends(get_stats_db),
    current_user: User = Depends(get_current_active_user)
):
    ap_info = aps_db.get_ap_by_host_with_stats(host)
    if not ap_info:
        raise HTTPException(status_code=404, detail="AP no encontrado.")

    if not stats_conn:
        return APHistoryResponse(host=host, hostname=ap_info.get('hostname', host), history=[])

    if period == "7d":
        start_time = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_time = datetime.utcnow() - timedelta(days=30)
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)
    
    query = "SELECT timestamp, client_count, airtime_total_usage, total_throughput_tx, total_throughput_rx FROM ap_stats_history WHERE ap_host = ? AND timestamp >= ? ORDER BY timestamp ASC;"
    cursor = stats_conn.execute(query, (host, start_time))
    rows = cursor.fetchall()
    
    return APHistoryResponse(host=host, hostname=ap_info.get('hostname'), history=[dict(row) for row in rows])