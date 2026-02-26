from typing import Optional


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
    """Format doctor list as a readable string for the AI context."""
    if not doctors:
        return "No doctors are currently available."
    lines = []
    for d in doctors:
        timings = ", ".join([f"{t['day']} {t['start_time']}–{t['end_time']}" for t in d.get("timings", [])])
        lines.append(
            f"• Dr. {d['name']} ({d['specialization']}) — "
            f"Fee: PKR {d['consultation_fee']:.0f} — "
            f"Timings: {timings or 'Contact clinic'}"
        )
    return "\n".join(lines)


def format_tests_for_ai(tests: list) -> str:
    """Format lab test list as a readable string for the AI context."""
    if not tests:
        return "No lab tests are currently available."
    lines = []
    for t in tests:
        lines.append(
            f"• {t['name']} ({t.get('category','')}) — "
            f"Fee: PKR {t['fee']:.0f} — "
            f"Report in: {t.get('report_time_hours', 24)}h"
        )
    return "\n".join(lines)
