# app/services/ap_service.py
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Importaciones de nuestras utilidades y capas de DB
from ..utils.device_clients.ap_client import UbiquitiClient
from ..db import aps_db, settings_db, stats_db
from ..db.base import get_stats_db_connection

# --- ¡LÍNEA CORREGIDA! ---
# La importación ahora apunta a la nueva ubicación de los modelos de 'aps'
from ..api.aps.models import (
    AP, APLiveDetail, CPEDetail, APHistoryResponse, HistoryDataPoint, 
    APCreate, APUpdate
)

# --- Excepciones personalizadas del Servicio ---
class APNotFoundError(Exception):
    pass
class APUnreachableError(Exception):
    pass
class APDataError(Exception):
    pass
class APCreateError(Exception):
    pass


class APService:
    """
    Servicio para toda la lógica de negocio relacionada con los Access Points (APs).
    """

    def __init__(self):
        # Este servicio no tiene estado, por lo que __init__ está vacío.
        # Las dependencias se llaman a nivel de módulo (ej. aps_db.metodo())
        pass

    def get_all_aps(self) -> List[Dict[str, Any]]:
        """Obtiene todos los APs con sus últimas estadísticas."""
        return aps_db.get_all_aps_with_stats()

    def get_ap_by_host(self, host: str) -> Dict[str, Any]:
        """Obtiene un AP específico por host."""
        ap = aps_db.get_ap_by_host_with_stats(host)
        if not ap:
            raise APNotFoundError(f"AP no encontrado: {host}")
        return ap

    def create_ap(self, ap_data: APCreate) -> Dict[str, Any]:
        """Crea un nuevo AP en la base de datos."""
        ap_dict = ap_data.model_dump()
        
        # Lógica de negocio: Asignar intervalo por defecto si no se proporciona
        if ap_dict.get("monitor_interval") is None:
            default_interval_str = settings_db.get_setting('default_monitor_interval')
            ap_dict["monitor_interval"] = int(default_interval_str) if default_interval_str and default_interval_str.isdigit() else 300
        
        try:
            new_ap = aps_db.create_ap_in_db(ap_dict)
            return new_ap
        except ValueError as e:
            raise APCreateError(str(e))

    def update_ap(self, host: str, ap_update: APUpdate) -> Dict[str, Any]:
        """Actualiza un AP existente."""
        update_fields = ap_update.model_dump(exclude_unset=True)
        if not update_fields:
            raise APDataError("No se proporcionaron campos para actualizar.")
        
        # Lógica de negocio: No permitir cambiar contraseña si está vacía
        if "password" in update_fields and not update_fields["password"]:
            del update_fields["password"]

        rows_affected = aps_db.update_ap_in_db(host, update_fields)
        if rows_affected == 0:
            raise APNotFoundError(f"AP no encontrado para actualizar: {host}")
            
        updated_ap_data = aps_db.get_ap_by_host_with_stats(host)
        if not updated_ap_data:
            raise APDataError(f"No se pudo recuperar el AP {host} después de la actualización.")
        return updated_ap_data

    def delete_ap(self, host: str):
        """Elimina un AP de la base de datos."""
        rows_affected = aps_db.delete_ap_from_db(host)
        if rows_affected == 0:
            raise APNotFoundError(f"AP no encontrado para eliminar: {host}")
    
    def get_cpes_for_ap(self, host: str) -> List[Dict[str, Any]]:
        """Obtiene los CPEs conectados a un AP desde el último snapshot."""
        return stats_db.get_cpes_for_ap_from_stats(host)

    def get_live_data(self, host: str) -> APLiveDetail:
        """Obtiene datos en vivo de un AP y los formatea."""
        ap_credentials = aps_db.get_ap_credentials(host)
        if not ap_credentials:
            raise APNotFoundError(f"AP no encontrado en el inventario: {host}")

        client = UbiquitiClient(host=host, username=ap_credentials['username'], password=ap_credentials['password'])
        status_data = client.get_status_data()

        if not status_data:
            raise APUnreachableError(f"No se pudo obtener datos del AP {host}. Puede estar offline.")
        
        # --- INICIO DE LÓGICA DE TRANSFORMACIÓN (movida desde la API) ---
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
            is_enabled=True, # Asumimos True si logramos conectar
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
        # --- FIN DE LÓGICA DE TRANSFORMACIÓN ---

    def get_ap_history(self, host: str, period: str = "24h") -> APHistoryResponse:
        """Obtiene datos históricos de un AP desde la DB de estadísticas."""
        
        # Obtenemos info básica del AP (como el hostname)
        ap_info = self.get_ap_by_host(host) # Reutilizamos nuestro propio método

        # Lógica de conexión a la DB de stats (movida desde la API)
        stats_conn = get_stats_db_connection()
        if not stats_conn:
            return APHistoryResponse(host=host, hostname=ap_info.get('hostname', host), history=[])

        if period == "7d":
            start_time = datetime.utcnow() - timedelta(days=7)
        elif period == "30d":
            start_time = datetime.utcnow() - timedelta(days=30)
        else:
            start_time = datetime.utcnow() - timedelta(hours=24)
        
        try:
            query = "SELECT timestamp, client_count, airtime_total_usage, total_throughput_tx, total_throughput_rx FROM ap_stats_history WHERE ap_host = ? AND timestamp >= ? ORDER BY timestamp ASC;"
            cursor = stats_conn.execute(query, (host, start_time))
            rows = cursor.fetchall()
            
            return APHistoryResponse(
                host=host, 
                hostname=ap_info.get('hostname'), 
                history=[HistoryDataPoint(**dict(row)) for row in rows]
            )
        except sqlite3.Error as e:
            raise APDataError(f"Error en la base de datos de estadísticas: {e}")
        finally:
            if stats_conn:
                stats_conn.close()