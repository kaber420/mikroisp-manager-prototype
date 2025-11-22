from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Existing Router Models ---
class RouterResponse(BaseModel):
    id: Optional[int] = None
    host: str
    username: str
    zona_id: Optional[int] = None
    api_port: int
    api_ssl_port: int
    is_enabled: bool
    hostname: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None

class RouterCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: Optional[int] = None
    api_port: int
    is_enabled: bool = True

class RouterUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    is_enabled: Optional[bool] = None

class ProvisionRequest(BaseModel):
    new_api_user: str
    new_api_password: str

class ProvisionResponse(BaseModel):
    status: str
    message: str

class GenericActionResponse(BaseModel):
    status: str
    message: str

# --- New VLAN and Bridge Models ---
class VlanCreate(BaseModel):
    name: str
    vlan_id: int
    interface: str
    comment: str

class VlanUpdate(BaseModel):
    name: str
    vlan_id: int
    interface: str

class BridgeCreate(BaseModel):
    name: str
    ports: List[str]
    comment: str

class BridgeUpdate(BaseModel):
    name: str
    ports: List[str]

# --- Models from config.py ---
class RouterFullDetails(BaseModel):
    interfaces: List[Dict[str, Any]]
    ip_addresses: List[Dict[str, Any]]
    nat_rules: List[Dict[str, Any]]
    pppoe_servers: List[Dict[str, Any]]
    ppp_profiles: List[Dict[str, Any]]
    simple_queues: List[Dict[str, Any]]
    ip_pools: List[Dict[str, Any]]
    bridge_ports: List[Dict[str, Any]]

class CreatePlanRequest(BaseModel):
    plan_name: str
    rate_limit: Optional[str] = None
    parent_queue: Optional[str] = None
    local_address: Optional[str] = None
    comment: str
    pool_range: Optional[str] = None
    remote_address: Optional[str] = None

class AddSimpleQueueRequest(BaseModel):
    name: str
    target: str
    max_limit: str
    parent: Optional[str] = None
    dst: Optional[str] = None
    comment: Optional[str] = None
    is_parent: bool = False

class AddIpRequest(BaseModel):
    address: str
    interface: str
    comment: str

class AddNatRequest(BaseModel):
    out_interface: str
    comment: str

class AddPppoeServerRequest(BaseModel):
    service_name: str
    interface: str
    default_profile: str

# --- Models from pppoe.py ---
class PppoeSecretCreate(BaseModel):
    username: str
    password: str
    profile: str
    comment: Optional[str] = None
    service: str = 'pppoe'

class PppoeSecretUpdate(BaseModel):
    password: Optional[str] = None
    profile: Optional[str] = None
    comment: Optional[str] = None

class PppoeSecretDisable(BaseModel):
    disable: bool

# --- Models from system.py ---
class SystemResource(BaseModel):
    uptime: Optional[str] = None
    cpu_load: Optional[str] = Field(None, alias='cpu-load')
    free_memory: Optional[str] = Field(None, alias='free-memory')
    total_memory: Optional[str] = Field(None, alias='total-memory')
    board_name: Optional[str] = Field(None, alias='board-name')
    version: Optional[str] = None
    name: Optional[str] = None # hostname
    serial_number: Optional[str] = Field(None, alias='serial-number')
    
    # --- CAMPOS AÑADIDOS PARA QUE PASEN EL FILTRO! ---
    platform: Optional[str] = None
    cpu: Optional[str] = None
    cpu_count: Optional[str] = Field(None, alias='cpu-count')
    cpu_frequency: Optional[str] = Field(None, alias='cpu-frequency')
    model: Optional[str] = None
    nlevel: Optional[str] = None
    voltage: Optional[str] = None
    temperature: Optional[str] = None
    
    # Campos de disco normalizados
    total_disk: Optional[str] = Field(None, alias='total-disk')
    free_disk: Optional[str] = Field(None, alias='free-disk')

class BackupCreateRequest(BaseModel):
    backup_type: str # 'backup' or 'export'
    backup_name: str

class RouterUserCreate(BaseModel):
    username: str
    password: str
    group: str # 'full', 'write', 'read'
