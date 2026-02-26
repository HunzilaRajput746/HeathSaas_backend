from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, date
import uuid


class AppointmentCreate(BaseModel):
    clinic_id: str
    patient_name: str
    phone: str               # Will receive WhatsApp notification
    date: str                # "YYYY-MM-DD"
    booking_type: Literal["doctor", "lab_test"]
    # One of these must be set based on booking_type:
    doctor_id: Optional[str] = None
    test_id: Optional[str] = None
    notes: Optional[str] = ""


class AppointmentInDB(BaseModel):
    appointment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    clinic_id: str
    patient_name: str
    phone: str
    date: str                # "YYYY-MM-DD"
    time_slot: str           # "09:00" – assigned by booking engine
    booking_type: Literal["doctor", "lab_test"]
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    test_id: Optional[str] = None
    test_name: Optional[str] = None
    fee: float = 0.0
    status: Literal["confirmed", "cancelled", "completed"] = "confirmed"
    whatsapp_sent: bool = False
    notes: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class AppointmentResponse(AppointmentInDB):
    pass


class AppointmentUpdate(BaseModel):
    status: Optional[Literal["confirmed", "cancelled", "completed"]] = None
    notes: Optional[str] = None
