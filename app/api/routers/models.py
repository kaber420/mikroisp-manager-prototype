# app/api/routers/models.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any

# --- Modelos Pydantic ---
class RouterBase(BaseModel):
    host: str
    username: str
    zona_id: Optional[int] = None
    api_port: int = 8728
    api_ssl_port: int = 8729
    is_enabled: bool = True

class RouterCreate(RouterBase):
    password: str

class RouterUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    is_enabled: Optional[bool] = None

class RouterResponse(RouterBase):
    model_config = ConfigDict(from_attributes=True)
    hostname: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None

class ProvisionRequest(BaseModel):
    new_api_user: str
    new_api_password: str

class ProvisionResponse(BaseModel):
    status: str
    message: str

class SystemResource(BaseModel):
    version: Optional[str] = None
    platform: Optional[str] = None
    board_name: Optional[str] = Field(None, alias='board-name')
    cpu: Optional[str] = None
    name: Optional[str] = None
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

class AddIpRequest(BaseModel):
    interface: str
    address: str
    comment: str = "Managed by µMonitor"

class AddNatRequest(BaseModel):
    out_interface: str
    comment: str = "NAT-WAN (µMonitor)"

class AddPppoeServerRequest(BaseModel):
    service_name: str
    interface: str
    default_profile: str = "default"

class CreatePlanRequest(BaseModel):
    plan_name: str
    pool_range: str
    local_address: str
    rate_limit: str
    parent_queue: str
    comment: str = "Managed by µMonitor"

class AddSimpleQueueRequest(BaseModel):
    name: str
    max_limit: str = Field(..., description="ej. 100M/500M")
    comment: str = "Managed by µMonitor (Parent Queue)"

class RouterFullDetails(BaseModel):
    interfaces: List[Dict[str, Any]]
    ip_addresses: List[Dict[str, Any]]
    nat_rules: List[Dict[str, Any]]
    pppoe_servers: List[Dict[str, Any]]
    ppp_profiles: List[Dict[str, Any]]
    simple_queues: List[Dict[str, Any]]
    ip_pools: List[Dict[str, Any]]

class PppoeSecretCreate(BaseModel):
    username: str
    password: str
    profile: str
    comment: str = ""
    service: str = 'pppoe'

class PppoeSecretUpdate(BaseModel):
    password: Optional[str] = None
    profile: Optional[str] = None
    comment: Optional[str] = None

class PppoeSecretDisable(BaseModel):
    disable: bool = True

class BackupCreateRequest(BaseModel):
    backup_name: str
    backup_type: str # 'backup' or 'export'

class RouterUserCreate(BaseModel):
    username: str
    password: str
    group: str # 'full', 'write', or 'read'