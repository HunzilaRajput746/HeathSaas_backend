from datetime import datetime, timedelta, date
from typing import Optional, Tuple


def generate_slots(start_time: str, end_time: str, slot_minutes: int = 10) -> list[str]:
    slots = []
    fmt = "%H:%M"
    current = datetime.strptime(start_time, fmt)
    end = datetime.strptime(end_time, fmt)
    while current < end:
        slots.append(current.strftime(fmt))
        current += timedelta(minutes=slot_minutes)
    return slots


def is_doctor_available_on_date(doctor: dict, check_date: date) -> bool:
    """Check if doctor works on the given date based on available_days."""
    day_name = check_date.strftime("%A")  # e.g. "Monday"
    available_days = doctor.get("available_days", [])
    if not available_days:
        return True  # No restriction = always available
    return day_name in available_days


def get_doctor_timings_for_date(doctor: dict, check_date: date) -> Tuple[str, str]:
    """Get doctor's working hours for a specific date."""
    day_name = check_date.strftime("%A")
    timings = doctor.get("timings", [])

    for t in timings:
        day_field = t.get("day", "")
        # Handle formats like "Mon-Fri", "Mon-Wed-Fri", "Monday", "Tue-Sat"
        day_abbrevs = {
            "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
            "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"
        }
        # Parse range like "Mon-Fri"
        parts = day_field.split("-")
        if len(parts) == 2 and parts[0] in day_abbrevs and parts[1] in day_abbrevs:
            days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            start_idx = days_order.index(day_abbrevs[parts[0]])
            end_idx = days_order.index(day_abbrevs[parts[1]])
            if start_idx <= days_order.index(day_name) <= end_idx:
                return t["start_time"], t["end_time"]
        else:
            # Handle individual days or comma-separated
            for part in parts:
                full = day_abbrevs.get(part, part)
                if full == day_name:
                    return t["start_time"], t["end_time"]

    # Fallback to first timing if found
    if timings:
        return timings[0]["start_time"], timings[0]["end_time"]
    return "09:00", "17:00"


async def get_booked_slots(db, clinic_id: str, date_str: str, doctor_id: str = None) -> list[str]:
    """Return all booked time slots for a clinic/date, optionally per doctor."""
    query = {
        "clinic_id": clinic_id,
        "date": date_str,
        "status": {"$ne": "cancelled"}
    }
    if doctor_id:
        query["doctor_id"] = doctor_id

    cursor = db["appointments"].find(query, {"time_slot": 1})
    booked = []
    async for doc in cursor:
        if "time_slot" in doc:
            booked.append(doc["time_slot"])
    return booked


async def get_daily_count(db, clinic_id: str, date_str: str) -> int:
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
    doctor: dict = None,  # ← NEW: pass doctor dict for timing check
) -> Tuple[Optional[str], str]:
    """
    Find the next available slot.
    - Allows TODAY's date
    - Respects doctor's available_days and timings
    - Falls back to clinic working hours if no doctor passed
    """
    today = date.today()

    # Parse requested date — if it's in the past, use today
    try:
        check_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
    except Exception:
        check_date = today

    if check_date < today:
        check_date = today

    # Try up to 30 days forward
    for _ in range(30):
        date_str = check_date.strftime("%Y-%m-%d")

        # Check doctor availability on this day
        if doctor:
            if not is_doctor_available_on_date(doctor, check_date):
                check_date += timedelta(days=1)
                continue
            start, end = get_doctor_timings_for_date(doctor, check_date)
        else:
            start, end = working_start, working_end

        # Skip Sunday if no doctor specified
        if not doctor and check_date.weekday() == 6:
            check_date += timedelta(days=1)
            continue

        daily_count = await get_daily_count(db, clinic_id, date_str)
        if daily_count < max_patients:
            all_slots = generate_slots(start, end, slot_minutes)
            booked = await get_booked_slots(
                db, clinic_id, date_str,
                doctor_id=doctor.get("doctor_id") if doctor else None
            )

            # If today — skip past time slots
            now_time = datetime.now().strftime("%H:%M")
            for slot in all_slots:
                if slot in booked:
                    continue
                if check_date == today and slot <= now_time:
                    continue  # Skip slots that already passed today
                return slot, date_str

        check_date += timedelta(days=1)

    return None, requested_date


async def create_appointment(db, appointment_data: dict) -> dict:
    result = await db["appointments"].insert_one(appointment_data)
    appointment_data["_id"] = str(result.inserted_id)
    return appointment_data


async def get_appointments_for_clinic(
    db,
    clinic_id: str,
    date_str: str = None,
    status: str = None,
    limit: int = 200
) -> list:
    query = {"clinic_id": clinic_id}
    if date_str:
        query["date"] = date_str
    if status:
        query["status"] = status

    cursor = db["appointments"].find(query).sort(
        [("date", 1), ("time_slot", 1)]  # Sort by date then time
    ).limit(limit)

    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def get_appointments_grouped_by_date(db, clinic_id: str) -> dict:
    """
    Returns appointments grouped by date — for calendar/date view.
    { "2024-01-15": [appt1, appt2], "2024-01-16": [appt3] }
    """
    cursor = db["appointments"].find(
        {"clinic_id": clinic_id, "status": {"$ne": "cancelled"}}
    ).sort([("date", 1), ("time_slot", 1)])

    grouped = {}
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        d = doc.get("date", "unknown")
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(doc)

    return grouped
