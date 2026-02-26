from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from db.mongodb import get_db


def generate_slots(start_time: str, end_time: str, slot_minutes: int = 10) -> list[str]:
    """
    Generate time slots between start and end time with given interval.
    Returns list of "HH:MM" strings.
    
    Example: generate_slots("09:00", "17:00", 10)
    → ["09:00", "09:10", "09:20", ..., "16:50"]
    """
    slots = []
    fmt = "%H:%M"
    current = datetime.strptime(start_time, fmt)
    end = datetime.strptime(end_time, fmt)

    while current < end:
        slots.append(current.strftime(fmt))
        current += timedelta(minutes=slot_minutes)

    return slots


async def get_booked_slots(db, clinic_id: str, date_str: str) -> list[str]:
    """Return all already-booked time slots for a given clinic and date."""
    cursor = db["appointments"].find(
        {"clinic_id": clinic_id, "date": date_str, "status": {"$ne": "cancelled"}},
        {"time_slot": 1}
    )
    booked = []
    async for doc in cursor:
        if "time_slot" in doc:
            booked.append(doc["time_slot"])
    return booked


async def get_daily_count(db, clinic_id: str, date_str: str) -> int:
    """Count non-cancelled appointments for a clinic on a given date."""
    return await db["appointments"].count_documents(
        {"clinic_id": clinic_id, "date": date_str, "status": {"$ne": "cancelled"}}
    )


async def assign_next_available_slot(
    db,
    clinic_id: str,
    requested_date: str,
    max_patients: int = 50,
    slot_minutes: int = 10,
    working_start: str = "09:00",
    working_end: str = "17:00",
) -> Tuple[Optional[str], str]:
    """
    Find the next available slot for a given date.
    If the day is full (≥ max_patients), try the next day, and so on.
    
    Returns: (time_slot, actual_date) — actual_date may differ from requested_date
    """
    check_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
    all_slots = generate_slots(working_start, working_end, slot_minutes)

    # Try up to 30 days forward
    for _ in range(30):
        date_str = check_date.strftime("%Y-%m-%d")
        daily_count = await get_daily_count(db, clinic_id, date_str)

        if daily_count < max_patients:
            booked = await get_booked_slots(db, clinic_id, date_str)
            for slot in all_slots:
                if slot not in booked:
                    return slot, date_str

        # Move to next day
        check_date += timedelta(days=1)
        # Skip Sundays (optional – clinics can configure this)
        while check_date.weekday() == 6:  # 6 = Sunday
            check_date += timedelta(days=1)

    return None, requested_date  # No slots found in 30 days


async def create_appointment(db, appointment_data: dict) -> dict:
    """
    Insert appointment into MongoDB and return the inserted document.
    """
    result = await db["appointments"].insert_one(appointment_data)
    appointment_data["_id"] = str(result.inserted_id)
    return appointment_data


async def get_appointments_for_clinic(
    db,
    clinic_id: str,
    date_str: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> list:
    """Fetch appointments for a clinic, optionally filtered by date and status."""
    query = {"clinic_id": clinic_id}
    if date_str:
        query["date"] = date_str
    if status:
        query["status"] = status

    cursor = db["appointments"].find(query).sort("created_at", -1).limit(limit)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results
