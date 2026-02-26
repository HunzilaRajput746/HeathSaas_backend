from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class LabTestCreate(BaseModel):
    clinic_id: str
    name: str
    category: str = ""          # e.g. "Blood Test", "Radiology"
    description: str = ""
    fee: float
    preparation: str = ""       # e.g. "Fast for 8 hours"
    duration_minutes: int = 30  # How long the test takes
    report_time_hours: int = 24 # When report is ready
    is_active: bool = True


class LabTestInDB(LabTestCreate):
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class LabTestResponse(BaseModel):
    test_id: str
    clinic_id: str
    name: str
    category: str
    description: str
    fee: float
    preparation: str
    duration_minutes: int
    report_time_hours: int
    is_active: bool


class LabTestUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    fee: Optional[float] = None
    preparation: Optional[str] = None
    duration_minutes: Optional[int] = None
    report_time_hours: Optional[int] = None
    is_active: Optional[bool] = None
