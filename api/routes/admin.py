from fastapi import APIRouter, Depends, Query
from core.dependencies import get_clinic_id_from_token
from db.mongodb import get_db
from services.booking_service import (
    get_appointments_for_clinic,
    get_appointments_grouped_by_date
)
from datetime import datetime, date

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get("/appointments")
async def get_appointments(
    date_filter: str = Query(None, description="YYYY-MM-DD — filter by date"),
    status: str = Query(None, description="confirmed/cancelled/completed"),
    limit: int = Query(200),
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """Get appointments — optionally filtered by date and status."""
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


@router.get("/appointments/by-date")
async def get_appointments_by_date(
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """
    Returns all appointments grouped by date.
    { "2024-01-15": [appt1, appt2], ... }
    """
    grouped = await get_appointments_grouped_by_date(db, clinic_id)

    # Add summary per date
    summary = []
    for d, appts in sorted(grouped.items()):
        confirmed = sum(1 for a in appts if a.get("status") == "confirmed")
        completed = sum(1 for a in appts if a.get("status") == "completed")
        revenue = sum(a.get("fee", 0) for a in appts if a.get("status") != "cancelled")
        summary.append({
            "date": d,
            "total": len(appts),
            "confirmed": confirmed,
            "completed": completed,
            "revenue": revenue,
            "appointments": appts,
        })

    return {"dates": summary, "total_dates": len(summary)}


@router.get("/appointments/upcoming")
async def get_upcoming_appointments(
    days: int = Query(7, description="How many days ahead"),
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    """Get appointments for next N days."""
    from datetime import timedelta
    today = date.today()
    results = []
    for i in range(days):
        d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        appts = await get_appointments_for_clinic(db, clinic_id, d)
        if appts:
            results.append({
                "date": d,
                "is_today": i == 0,
                "count": len(appts),
                "appointments": appts,
            })
    return {"days": results}


@router.put("/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: str,
    data: dict,
    clinic_id: str = Depends(get_clinic_id_from_token),
    db=Depends(get_db),
):
    allowed_status = ["confirmed", "cancelled", "completed"]
    update = {}
    if "status" in data and data["status"] in allowed_status:
        update["status"] = data["status"]
    if "notes" in data:
        update["notes"] = data["notes"]
    if update:
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
    today = date.today().strftime("%Y-%m-%d")

    today_total = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today}
    )
    today_confirmed = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today, "status": "confirmed"}
    )
    today_cancelled = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today, "status": "cancelled"}
    )
    today_completed = await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": today, "status": "completed"}
    )
    all_time = await db["appointments"].count_documents({"clinic_id": clinic_id})
    doctor_count = await db["doctors"].count_documents(
        {"clinic_id": clinic_id, "is_active": True}
    )
    test_count = await db["lab_tests"].count_documents(
        {"clinic_id": clinic_id, "is_active": True}
    )

    # Today revenue
    pipeline = [
        {"$match": {"clinic_id": clinic_id, "date": today, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$fee"}}}
    ]
    rev = await db["appointments"].aggregate(pipeline).to_list(1)
    today_revenue = rev[0]["total"] if rev else 0

    # Total revenue all time
    pipeline2 = [
        {"$match": {"clinic_id": clinic_id, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$fee"}}}
    ]
    rev2 = await db["appointments"].aggregate(pipeline2).to_list(1)
    total_revenue = rev2[0]["total"] if rev2 else 0

    # Upcoming appointments (next 7 days)
    from datetime import timedelta
    upcoming_count = await db["appointments"].count_documents({
        "clinic_id": clinic_id,
        "date": {"$gt": today},
        "status": "confirmed"
    })

    return {
        "today": {
            "total": today_total,
            "confirmed": today_confirmed,
            "cancelled": today_cancelled,
            "completed": today_completed,
            "revenue": today_revenue,
        },
        "all_time_appointments": all_time,
        "total_revenue": total_revenue,
        "upcoming_confirmed": upcoming_count,
        "active_doctors": doctor_count,
        "active_lab_tests": test_count,
        "date": today,
    }


@router.get("/public/{clinic_id}/info")
async def get_public_clinic_info(clinic_id: str, db=Depends(get_db)):
    clinic = await db["clinics"].find_one({"clinic_id": clinic_id, "is_active": True})
    if not clinic:
        return {"error": "Clinic not found"}
    clinic["_id"] = str(clinic["_id"])
    return {
        "clinic_id": clinic["clinic_id"],
        "name": clinic["name"],
        "address": clinic.get("address"),
        "phone": clinic.get("phone"),
        "logo_url": clinic.get("logo_url"),
    }
