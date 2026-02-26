from fastapi import APIRouter, Depends, Query
from core.dependencies import get_clinic_id_from_token
from db.mongodb import get_db
from services.booking_service import get_appointments_for_clinic
from datetime import datetime, date

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/appointments")
async def get_appointments(
    date_filter: str = Query(None, description="YYYY-MM-DD"),
    status: str = Query(None),
    limit: int = Query(100),
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """Get all appointments for the clinic with optional filters."""
    appointments = await get_appointments_for_clinic(
        db, clinic_id, date_filter, status, limit
    )
    return {"appointments": appointments, "count": len(appointments)}


@router.get("/appointments/today")
async def get_today_appointments(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    today = date.today().strftime("%Y-%m-%d")
    appointments = await get_appointments_for_clinic(db, clinic_id, today)
    return {"appointments": appointments, "date": today, "count": len(appointments)}


@router.put("/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: str,
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """Update appointment status (confirmed/cancelled/completed)."""
    allowed_status = ["confirmed", "cancelled", "completed"]
    update = {}
    if "status" in data and data["status"] in allowed_status:
        update["status"] = data["status"]
    if "notes" in data:
        update["notes"] = data["notes"]

    await db["appointments"].update_one(
        {"appointment_id": appointment_id, "clinic_id": clinic_id},
        {"$set": update}
    )
    return {"success": True}


@router.get("/stats")
async def get_dashboard_stats(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """Dashboard summary statistics."""
    today = date.today().strftime("%Y-%m-%d")

    # Today's counts
    today_total = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today}
    )
    today_confirmed = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today, "status": "confirmed"}
    )
    today_cancelled = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today, "status": "cancelled"}
    )

    # All-time total
    all_time = await db["appointments"].count_documents({"clinic_id": clinic_id})

    # Doctor count
    doctor_count = await db["doctors"].count_documents(
        {"clinic_id": clinic_id, "is_active": True}
    )

    # Test count
    test_count = await db["lab_tests"].count_documents(
        {"clinic_id": clinic_id, "is_active": True}
    )

    # Revenue today
    pipeline = [
        {"$match": {"clinic_id": clinic_id, "date": today, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$fee"}}}
    ]
    revenue_result = await db["appointments"].aggregate(pipeline).to_list(1)
    today_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0

    return {
        "today": {
            "total": today_total,
            "confirmed": today_confirmed,
            "cancelled": today_cancelled,
            "revenue": today_revenue,
        },
        "all_time_appointments": all_time,
        "active_doctors": doctor_count,
        "active_lab_tests": test_count,
    }


@router.get("/public/{clinic_id}/info")
async def get_public_clinic_info(clinic_id: str, db=Depends(get_db)):
    """Public endpoint — no auth needed. Returns clinic info for chatbot widget."""
    clinic = await db["clinics"].find_one({"clinic_id": clinic_id, "is_active": True})
    if not clinic:
        return {"error": "Clinic not found"}
    clinic["_id"] = str(clinic["_id"])
    # Return only public fields
    return {
        "clinic_id": clinic["clinic_id"],
        "name": clinic["name"],
        "address": clinic.get("address"),
        "phone": clinic.get("phone"),
        "logo_url": clinic.get("logo_url"),
    }
