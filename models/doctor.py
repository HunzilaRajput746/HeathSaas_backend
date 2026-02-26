from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class DoctorTiming(BaseModel):
    day: str           # "Monday", "Tuesday", etc. or "Mon-Fri"
    start_time: str    # "09:00" (24h)
    end_time: str      # "17:00"


class DoctorCreate(BaseModel):
    clinic_id: str
    name: str
    specialization: str
    qualification: str = ""
    consultation_fee: float
    timings: List[DoctorTiming] = []
    available_days: List[str] = []  # ["Monday","Tuesday","Wednesday","Thursday","Friday"]
    image_url: Optional[str] = ""
    bio: Optional[str] = ""
    is_active: bool = True


class DoctorInDB(DoctorCreate):
    doctor_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class DoctorResponse(BaseModel):
    doctor_id: str
    clinic_id: str
    name: str
    specialization: str
    qualification: str
    consultation_fee: float
    timings: List[DoctorTiming]
    available_days: List[str]
    image_url: Optional[str]
    bio: Optional[str]
    is_active: bool


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    consultation_fee: Optional[float] = None
    timings: Optional[List[DoctorTiming]] = None
    available_days: Optional[List[str]] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None
