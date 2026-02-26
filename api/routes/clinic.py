from fastapi import APIRouter, HTTPException, Depends
from models.doctor import DoctorCreate, DoctorUpdate
from models.lab_test import LabTestCreate, LabTestUpdate
from core.dependencies import get_current_admin, get_clinic_id_from_token
from db.mongodb import get_db
import uuid

router = APIRouter(prefix="/api/clinic", tags=["Clinic Management"])


# ─── CLINIC INFO ──────────────────────────────────────────────────────────────

@router.get("/info")
async def get_clinic_info(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    clinic = await db["clinics"].find_one({"clinic_id": clinic_id})
    if not clinic:
        raise HTTPException(404, detail="Clinic not found")
    clinic["_id"] = str(clinic["_id"])
    return clinic


@router.put("/info")
async def update_clinic_info(
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    allowed_fields = ["name", "address", "phone", "email", "logo_url", "settings"]
    update = {k: v for k, v in data.items() if k in allowed_fields}
    await db["clinics"].update_one({"clinic_id": clinic_id}, {"$set": update})
    return {"success": True, "message": "Clinic info updated"}


# ─── DOCTORS ──────────────────────────────────────────────────────────────────

@router.get("/doctors")
async def list_doctors(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    cursor = db["doctors"].find({"clinic_id": clinic_id})
    doctors = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doctors.append(doc)
    return doctors


@router.post("/doctors")
async def add_doctor(
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    doctor_doc = {
        "doctor_id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "name": data["name"],
        "specialization": data.get("specialization", ""),
        "qualification": data.get("qualification", ""),
        "consultation_fee": float(data["consultation_fee"]),
        "timings": data.get("timings", []),
        "available_days": data.get("available_days", []),
        "image_url": data.get("image_url", ""),
        "bio": data.get("bio", ""),
        "is_active": True,
    }
    await db["doctors"].insert_one(doctor_doc)
    doctor_doc["_id"] = str(doctor_doc.get("_id", ""))
    return {"success": True, "doctor": doctor_doc}


@router.put("/doctors/{doctor_id}")
async def update_doctor(
    doctor_id: str,
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    allowed = ["name", "specialization", "qualification", "consultation_fee",
               "timings", "available_days", "image_url", "bio", "is_active"]
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db["doctors"].update_one(
        {"doctor_id": doctor_id, "clinic_id": clinic_id},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(404, detail="Doctor not found")
    return {"success": True}


@router.delete("/doctors/{doctor_id}")
async def delete_doctor(
    doctor_id: str,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    await db["doctors"].update_one(
        {"doctor_id": doctor_id, "clinic_id": clinic_id},
        {"$set": {"is_active": False}}
    )
    return {"success": True}


# ─── LAB TESTS ────────────────────────────────────────────────────────────────

@router.get("/lab-tests")
async def list_lab_tests(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    cursor = db["lab_tests"].find({"clinic_id": clinic_id})
    tests = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        tests.append(doc)
    return tests


@router.post("/lab-tests")
async def add_lab_test(
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    test_doc = {
        "test_id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "name": data["name"],
        "category": data.get("category", ""),
        "description": data.get("description", ""),
        "fee": float(data["fee"]),
        "preparation": data.get("preparation", ""),
        "duration_minutes": int(data.get("duration_minutes", 30)),
        "report_time_hours": int(data.get("report_time_hours", 24)),
        "is_active": True,
    }
    await db["lab_tests"].insert_one(test_doc)
    test_doc["_id"] = str(test_doc.get("_id", ""))
    return {"success": True, "test": test_doc}


@router.put("/lab-tests/{test_id}")
async def update_lab_test(
    test_id: str,
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    allowed = ["name", "category", "description", "fee", "preparation",
               "duration_minutes", "report_time_hours", "is_active"]
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db["lab_tests"].update_one(
        {"test_id": test_id, "clinic_id": clinic_id},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(404, detail="Lab test not found")
    return {"success": True}


@router.delete("/lab-tests/{test_id}")
async def delete_lab_test(
    test_id: str,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    await db["lab_tests"].update_one(
        {"test_id": test_id, "clinic_id": clinic_id},
        {"$set": {"is_active": False}}
    )
    return {"success": True}
