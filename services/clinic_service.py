from typing import Optional
from datetime import date


async def get_clinic_by_id(db, clinic_id: str) -> Optional[dict]:
    clinic = await db["clinics"].find_one({"clinic_id": clinic_id})
    if clinic:
        clinic["_id"] = str(clinic["_id"])
    return clinic


async def get_doctors(db, clinic_id: str, active_only: bool = True) -> list:
    query = {"clinic_id": clinic_id}
    if active_only:
        query["is_active"] = True
    cursor = db["doctors"].find(query)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def get_doctor_by_id(db, clinic_id: str, doctor_id: str) -> Optional[dict]:
    doc = await db["doctors"].find_one({"clinic_id": clinic_id, "doctor_id": doctor_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_lab_tests(db, clinic_id: str, active_only: bool = True) -> list:
    query = {"clinic_id": clinic_id}
    if active_only:
        query["is_active"] = True
    cursor = db["lab_tests"].find(query)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def get_lab_test_by_id(db, clinic_id: str, test_id: str) -> Optional[dict]:
    doc = await db["lab_tests"].find_one({"clinic_id": clinic_id, "test_id": test_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


def format_doctors_for_ai(doctors: list) -> str:
    """
    Format doctor list for AI — MUST include doctor_id so AI can use it in BOOKING_REQUEST.
    """
    if not doctors:
        return "No doctors are currently available."
    
    today = date.today().strftime("%A")  # e.g. "Saturday"
    lines = []
    for d in doctors:
        timings = ", ".join([
            f"{t['day']} {t['start_time']}–{t['end_time']}"
            for t in d.get("timings", [])
        ])
        available_days = ", ".join(d.get("available_days", []))
        lines.append(
            f"• Dr. {d['name']} | ID: {d['doctor_id']} | "
            f"Specialization: {d['specialization']} | "
            f"Fee: PKR {d['consultation_fee']:.0f} | "
            f"Available: {available_days or 'Mon-Fri'} | "
            f"Timings: {timings or '09:00-17:00'}"
        )
    return "\n".join(lines)


def format_tests_for_ai(tests: list) -> str:
    """
    Format lab test list for AI — MUST include test_id so AI can use it in BOOKING_REQUEST.
    """
    if not tests:
        return "No lab tests are currently available."
    lines = []
    for t in tests:
        lines.append(
            f"• {t['name']} | ID: {t['test_id']} | "
            f"Category: {t.get('category', '')} | "
            f"Fee: PKR {t['fee']:.0f} | "
            f"Report in: {t.get('report_time_hours', 24)}h"
        )
    return "\n".join(lines)
