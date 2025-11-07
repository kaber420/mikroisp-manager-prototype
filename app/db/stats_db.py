# app/db/stats_db.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import get_db_connection, get_stats_db_connection
from .init_db import _setup_stats_db # Usamos la función de configuración

def _update_cpe_inventory(data: dict):
    """Actualiza la tabla de inventario de CPEs (dispositivos) en la DB de inventario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    
    for cpe in data.get("wireless", {}).get("sta", []):
        remote = cpe.get("remote", {})
        cursor.execute("""
        INSERT INTO cpes (mac, hostname, model, firmware, ip_address, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            hostname = excluded.hostname, model = excluded.model,
            firmware = excluded.firmware, ip_address = excluded.ip_address,
            last_seen = excluded.last_seen
        """, (
            cpe.get("mac"), remote.get("hostname"), remote.get("platform"),
            cpe.get("version"), cpe.get("lastip"), now, now
        ))
    conn.commit()
    conn.close()

def save_full_snapshot(ap_host: str, data: dict):
    """
    Función central que guarda un snapshot completo de datos en la DB de estadísticas.
    """
    if not data: return
    
    _update_cpe_inventory(data)
    _setup_stats_db()
    
    conn = get_stats_db_connection()
    if not conn:
        print(f"Error: No se pudo conectar a la base de datos de estadísticas para {ap_host}.")
        return

    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    ap_hostname = data.get("host", {}).get("hostname", ap_host)

    wireless_info = data.get("wireless", {})
    throughput_info = wireless_info.get("throughput", {})
    polling_info = wireless_info.get("polling", {})
    ath0_status = data.get("interfaces", [{}, {}])[1].get("status", {})
    gps_info = data.get("gps", {})
    
    try:
        cursor.execute("""
            INSERT INTO ap_stats_history (
                timestamp, ap_host, uptime, cpuload, freeram, client_count, noise_floor,
                total_throughput_tx, total_throughput_rx, airtime_total_usage, 
                airtime_tx_usage, airtime_rx_usage, frequency, chanbw, essid,
                total_tx_bytes, total_rx_bytes, gps_lat, gps_lon, gps_sats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, ap_host, data.get("host", {}).get("uptime"), data.get("host", {}).get("cpuload"),
            data.get("host", {}).get("freeram"), wireless_info.get("count"), wireless_info.get("noisef"),
            throughput_info.get("tx"), throughput_info.get("rx"),
            polling_info.get("use"), polling_info.get("tx_use"), polling_info.get("rx_use"),
            wireless_info.get("frequency"), wireless_info.get("chanbw"), wireless_info.get("essid"),
            ath0_status.get("tx_bytes"), ath0_status.get("rx_bytes"),
            gps_info.get("lat"), gps_info.get("lon"), gps_info.get("sats")
        ))

        for cpe in wireless_info.get("sta", []):
            remote = cpe.get("remote", {})
            stats = cpe.get("stats", {})
            airmax = cpe.get("airmax", {})
            eth_info = remote.get("ethlist", [{}])[0]
            chainrssi = cpe.get('chainrssi', [None, None, None])

            cursor.execute("""
                INSERT INTO cpe_stats_history (
                    timestamp, ap_host, cpe_mac, cpe_hostname, ip_address, signal, 
                    signal_chain0, signal_chain1, noisefloor, cpe_tx_power, distance, 
                    dl_capacity, ul_capacity, airmax_cinr_rx, airmax_usage_rx, 
                    airmax_cinr_tx, airmax_usage_tx, throughput_rx_kbps, throughput_tx_kbps, 
                    total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed, eth_cable_len
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, ap_host, cpe.get("mac"), remote.get("hostname"),
                cpe.get("lastip"), cpe.get("signal"), chainrssi[0], chainrssi[1], 
                cpe.get("noisefloor"), remote.get("tx_power"), cpe.get("distance"),
                airmax.get("dl_capacity"), airmax.get("ul_capacity"),
                airmax.get('rx', {}).get('cinr'), airmax.get('rx', {}).get('usage'), 
                airmax.get('tx', {}).get('cinr'), airmax.get('tx', {}).get('usage'), 
                remote.get('rx_throughput'), remote.get('tx_throughput'), 
                stats.get('rx_bytes'), stats.get('tx_bytes'), remote.get('uptime'), 
                eth_info.get('plugged'), eth_info.get('speed'), eth_info.get('cable_len')
            ))
            
        for event in wireless_info.get("sta_disconnected", []):
            cursor.execute("""
                INSERT INTO disconnection_events (timestamp, ap_host, cpe_mac, cpe_hostname, reason_code, connection_duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp, ap_host, event.get("mac"), event.get("hostname"),
                event.get("reason_code"), event.get("disconnect_duration")
            ))

        conn.commit()
        print(f"Datos de '{ap_hostname}' y sus CPEs guardados en la base de datos de estadísticas.")
    
    except sqlite3.Error as e:
        print(f"Error de base de datos al guardar snapshot para {ap_host}: {e}")
    finally:
        if conn:
            conn.close()

def get_cpes_for_ap_from_stats(host: str) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de CPEs más recientes para un AP específico desde la DB de estadísticas.
    """
    conn = get_stats_db_connection()
    if not conn:
        return []

    try:
        query = """
            WITH LatestCPEStats AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER(PARTITION BY cpe_mac, ap_host ORDER BY timestamp DESC) as rn
                FROM cpe_stats_history
                WHERE ap_host = ?
            )
            SELECT 
                timestamp,
                cpe_mac, cpe_hostname, ip_address, signal, signal_chain0, signal_chain1,
                noisefloor, dl_capacity, ul_capacity, throughput_rx_kbps, throughput_tx_kbps,
                total_rx_bytes, total_tx_bytes, cpe_uptime, eth_plugged, eth_speed 
            FROM LatestCPEStats WHERE rn = 1 ORDER BY signal DESC;
        """
        cursor = conn.execute(query, (host,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    finally:
        if conn:
            conn.close()