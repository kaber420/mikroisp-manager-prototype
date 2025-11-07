# app/api/stats_api.py
import sqlite3
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional

from ..auth import User, get_current_active_user
# --- CAMBIOS EN IMPORTACIONES DE DB ---
from ..db.base import get_db_connection, get_stats_db_connection
from ..db.cpes_db import get_all_cpes_globally # Reutilizamos una función ya creada

router = APIRouter()

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

# --- Dependencias de DB ---
def get_inventory_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()

def get_stats_db():
    conn = get_stats_db_connection()
    try:
        yield conn
    finally:
        if conn:
            conn.close()

# --- Endpoints de la API ---
@router.get("/stats/top-aps-by-airtime", response_model=List[TopAP])
def get_top_aps_by_airtime(
    limit: int = 5, 
    conn: sqlite3.Connection = Depends(get_inventory_db), 
    current_user: User = Depends(get_current_active_user)
):
    stats_db_file = f"stats_{datetime.utcnow().strftime('%Y_%m')}.sqlite"
    if not os.path.exists(stats_db_file):
        return []

    try:
        conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
        query = """
            WITH LatestStats AS (
                SELECT 
                    ap_host, airtime_total_usage,
                    ROW_NUMBER() OVER(PARTITION BY ap_host ORDER BY timestamp DESC) as rn
                FROM stats_db.ap_stats_history
                WHERE airtime_total_usage IS NOT NULL
            )
            SELECT a.hostname, a.host, s.airtime_total_usage
            FROM aps as a 
            JOIN LatestStats s ON a.host = s.ap_host AND s.rn = 1
            ORDER BY s.airtime_total_usage DESC 
            LIMIT ?;
        """
        cursor = conn.execute(query, (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


@router.get("/stats/top-cpes-by-signal", response_model=List[TopCPE])
def get_top_cpes_by_weak_signal(
    limit: int = 5, 
    stats_conn: Optional[sqlite3.Connection] = Depends(get_stats_db), 
    current_user: User = Depends(get_current_active_user)
):
    if not stats_conn: 
        return []
    
    query = """
        WITH LatestCPEStats AS (
            SELECT 
                *,
                ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
            FROM cpe_stats_history
            WHERE signal IS NOT NULL
        )
        SELECT cpe_hostname, cpe_mac, ap_host, signal
        FROM LatestCPEStats
        WHERE rn = 1
        ORDER BY signal ASC 
        LIMIT ?;
    """
    cursor = stats_conn.execute(query, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    return rows


@router.get("/stats/cpe-count", response_model=Dict[str, int])
def get_cpe_total_count(
    conn: sqlite3.Connection = Depends(get_inventory_db), 
    current_user: User = Depends(get_current_active_user)
):
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM cpes")
        count = cursor.fetchone()[0]
        return {"total_cpes": count}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")