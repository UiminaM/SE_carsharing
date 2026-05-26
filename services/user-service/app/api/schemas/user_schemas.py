
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserCreateRequest(BaseModel):
    email: EmailStr
    phone: str = Field(max_length=20)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    password: str = Field(min_length=6, max_length=128)

class UserResponse(BaseModel):
    id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    is_active: bool
    balance: float
    license_number: str | None
    license_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class TopUpRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)

class PaymentMethodCreateRequest(BaseModel):
    method_type: str = Field(pattern="^(card|wallet)$")
    token: str
    card_last4: str | None = Field(default=None, max_length=4)

class PaymentMethodResponse(BaseModel):
    id: str
    method_type: str
    card_last4: str | None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
