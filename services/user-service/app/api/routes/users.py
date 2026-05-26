
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.user_schemas import (
    PaymentMethodCreateRequest,
    PaymentMethodResponse,
    TopUpRequest,
    UserCreateRequest,
    UserResponse,
)
from app.api.dependencies.service import get_user_service
from app.domain.services.user_service import UserDomainService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    req: UserCreateRequest,
    svc: UserDomainService = Depends(get_user_service),
):
    user = await svc.register_user(
        email=req.email,
        phone=req.phone,
        first_name=req.first_name,
        last_name=req.last_name,
        password=req.password,
    )
    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    svc: UserDomainService = Depends(get_user_service),
):
    user = await svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/{user_id}/top-up", response_model=UserResponse)
async def top_up_balance(
    user_id: str,
    req: TopUpRequest,
    svc: UserDomainService = Depends(get_user_service),
):
    user = await svc.top_up_balance(user_id, req.amount)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/{user_id}/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    user_id: str,
    req: PaymentMethodCreateRequest,
    svc: UserDomainService = Depends(get_user_service),
):
    return await svc.add_payment_method(
        user_id=user_id,
        method_type=req.method_type,
        token=req.token,
        card_last4=req.card_last4,
    )
