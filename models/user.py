from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class AdminCreate(BaseModel):
    clinic_id: str
    email: str
    password: str
    full_name: str
    role: Literal["super_admin", "clinic_admin"] = "clinic_admin"


class AdminInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    clinic_id: str
    email: str
    hashed_password: str
    full_name: str
    role: str = "clinic_admin"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class AdminResponse(BaseModel):
    id: str
    clinic_id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class LoginRequest(BaseModel):
    email: str
    password: str
    clinic_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse
    clinic_name: str
