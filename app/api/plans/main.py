# app/api/plans/main.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from ...auth import User, get_current_active_user
from ...db import plans_db

router = APIRouter()

class PlanBase(BaseModel):
    name: str
    max_limit: str
    parent_queue: Optional[str] = None
    comment: Optional[str] = None
    router_id: int

class PlanCreate(PlanBase):
    pass

class Plan(PlanBase):
    id: int
    router_name: Optional[str] = None  # <--- Agregado para que el frontend pueda mostrar el router

# --- ESTE ENDPOINT FALTABA Y CAUSABA EL ERROR 405 ---
@router.get("/plans", response_model=List[Plan])
def get_all_plans(current_user: User = Depends(get_current_active_user)):
    """Obtiene todos los planes de la base de datos (usado para Simple Queues)."""
    return plans_db.get_all_plans()

@router.get("/plans/router/{router_id}", response_model=List[Plan])
def get_plans_by_router(router_id: int, current_user: User = Depends(get_current_active_user)):
    return plans_db.get_plans_by_router(router_id)

@router.post("/plans", response_model=Plan)
def create_plan(plan: PlanCreate, current_user: User = Depends(get_current_active_user)):
    try:
        return plans_db.create_plan(plan.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, current_user: User = Depends(get_current_active_user)):
    plans_db.delete_plan(plan_id)
    return {"status": "success"}