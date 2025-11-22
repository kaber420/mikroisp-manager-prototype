# app/services/backup_service.py
import os
import time
import paramiko
from datetime import datetime
from ..utils.device_clients.mikrotik.base import get_api_connection
from ..db.router_db import get_router_by_host, get_router_status

# Ruta base donde se guardarán los archivos
BACKUP_BASE_DIR = os.path.join(os.getcwd(), "data", "backups")

class BackupService:
    
    def __init__(self):
        # Asegurar que existen las carpetas base
        os.makedirs(BACKUP_BASE_DIR, exist_ok=True)

    def backup_router(self, host: str):
        router_data = get_router_by_host(host)
        if not router_data:
            return {"status": "error", "message": "Router no encontrado"}

        # 1. Preparar nombres y carpetas
        zona_name = f"Zona_{router_data['zona_id']}" if router_data['zona_id'] else "Sin_Zona"
        router_name = router_data['hostname'] or router_data['host']
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        
        # Crear carpeta de la zona si no existe: data/backups/Zona_1
        save_path = os.path.join(BACKUP_BASE_DIR, zona_name)
        os.makedirs(save_path, exist_ok=True)

        backup_filename = f"{router_name}-{timestamp}.backup"
        local_filepath = os.path.join(save_path, backup_filename)
        
        temp_backup_name = "umonitor_auto_backup" # Nombre temporal en el Mikrotik

        api = None
        ssh = None
        try:
            # --- FASE 1: CREAR RESPALDO (Vía API) ---
            api = get_api_connection(host) # Usa tu función existente de conexión
            # Comando: /system/backup/save name=umonitor_auto_backup
            api.get_resource('/system/backup').call('save', {'name': temp_backup_name})
            
            # Esperar un momento para asegurar que se escribió en disco del router
            time.sleep(2) 

            # --- FASE 2: DESCARGAR POR SFTP (Vía Paramiko) ---
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Nota: Usamos el puerto 22 por defecto para SFTP, o el que tengas configurado
            ssh.connect(
                hostname=router_data['host'],
                username=router_data['username'],
                password=router_data['password'],
                port=22, # Ojo: Si cambiaste el puerto SSH en Mikrotik, úsalo aquí
                timeout=10
            )
            
            sftp = ssh.open_sftp()
            # Mikrotik guarda los backups en la raíz o en /flash/ dependiendo del modelo
            remote_file = f"{temp_backup_name}.backup"
            
            # Intentar descargar
            try:
                sftp.get(remote_file, local_filepath)
            except FileNotFoundError:
                # A veces en equipos nuevos es flash/nombre
                sftp.get(f"flash/{remote_file}", local_filepath)
            
            sftp.close()
            ssh.close()

            # --- FASE 3: LIMPIEZA (Vía API) ---
            # Borrar el archivo del router para no ocupar espacio
            # Primero hay que encontrar el ID del archivo
            files_resource = api.get_resource('/file')
            file_to_delete = files_resource.get(name=f"{temp_backup_name}.backup")
            if file_to_delete:
                files_resource.remove(id=file_to_delete[0]['id'])

            return {
                "status": "success", 
                "file": backup_filename, 
                "path": local_filepath,
                "size_kb": os.path.getsize(local_filepath) / 1024
            }

        except Exception as e:
            print(f"Error respaldando {host}: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if ssh: ssh.close()
            # La API se cierra sola o depende de tu implementación de pool