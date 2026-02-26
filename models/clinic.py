from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ClinicSettings(BaseModel):
    max_patients_per_day: int = 50
    slot_duration_minutes: int = 10
    working_hours_start: str = "09:00"  # HH:MM 24h
    working_hours_end: str = "17:00"
    whatsapp_enabled: bool = True
    timezone: str = "Asia/Karachi"


class ClinicCreate(BaseModel):
    name: str
    subdomain: str  # e.g. "greenpark" → greenpark.healthsaas.com
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    logo_url: Optional[str] = ""
    settings: ClinicSettings = ClinicSettings()


class ClinicInDB(ClinicCreate):
    clinic_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        # Tells Pydantic to work with MongoDB's _id
        populate_by_name = True


class ClinicResponse(BaseModel):
    clinic_id: str
    name: str
    subdomain: str
    address: Optional[str]
    phone: Optional[str]
    logo_url: Optional[str]
    settings: ClinicSettings
    is_active: bool
