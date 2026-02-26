"""
Safe Seed Script — 2 modes:

1. python seed.py         → Sirf existing clinic info dikhata hai (SAFE)
2. python seed.py --fresh → Naya clinic banata hai (TABHI chalao jab chahiye)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db.mongodb import connect_db, get_db, create_indexes
from core.security import hash_password
import uuid


async def show_existing():
    """Existing data dikhao — kuch delete/add nahi karta."""
    await connect_db()
    db = get_db()

    print("\n" + "=" * 60)
    print("📊 EXISTING DATA IN DATABASE")
    print("=" * 60)

    clinics = await db["clinics"].find({}).to_list(100)
    if not clinics:
        print("❌ Koi clinic nahi mili!")
        print("   'python seed.py --fresh' chalao naya banane ke liye")
        return

    for clinic in clinics:
        clinic_id = clinic.get("clinic_id", "N/A")
        print(f"\n🏥 Clinic  : {clinic.get('name')}")
        print(f"   ID      : {clinic_id}")
        print(f"   Active  : {clinic.get('is_active')}")

        # Admin dhundo
        admin = await db["admins"].find_one({"clinic_id": clinic_id})
        if admin:
            print(f"\n👤 Admin")
            print(f"   Email   : {admin.get('email')}")
            print(f"   Name    : {admin.get('full_name')}")
            print(f"   Password: (reset karna ho to --reset flag use karo)")

        # Doctors count
        doc_count = await db["doctors"].count_documents({"clinic_id": clinic_id})
        test_count = await db["lab_tests"].count_documents({"clinic_id": clinic_id})
        appt_count = await db["appointments"].count_documents({"clinic_id": clinic_id})

        print(f"\n📈 Stats")
        print(f"   Doctors      : {doc_count}")
        print(f"   Lab Tests    : {test_count}")
        print(f"   Appointments : {appt_count}")

        print(f"\n🔗 URLs")
        print(f"   Chatbot : http://localhost:3000/?clinic={clinic_id}")
        print(f"   Admin   : http://localhost:3000/admin/login")

    print("\n" + "=" * 60)
    print("💡 TIP: Password reset karne ke liye:")
    print("   python seed.py --reset")
    print("=" * 60)


async def reset_password():
    """Admin password reset karo."""
    await connect_db()
    db = get_db()

    admins = await db["admins"].find({}).to_list(100)
    if not admins:
        print("❌ Koi admin nahi mila!")
        return

    print("\nAvailable admins:")
    for i, a in enumerate(admins):
        print(f"  {i+1}. {a.get('email')} (Clinic: {a.get('clinic_id', '')[:8]}...)")

    new_password = "Admin@123"
    for admin in admins:
        await db["admins"].update_one(
            {"_id": admin["_id"]},
            {"$set": {"hashed_password": hash_password(new_password)}}
        )
        print(f"\n✅ Password reset kiya: {admin.get('email')}")
        print(f"   Naya Password: {new_password}")


async def fresh_seed():
    """Naya clinic banao — sirf tab chalao jab bilkul fresh start chahiye."""
    await connect_db()
    db = get_db()
    await create_indexes(db)

    existing = await db["clinics"].count_documents({})
    if existing > 0:
        print(f"\n⚠️  WARNING: Database mein pehle se {existing} clinic(s) hain!")
        print("   Kya aap waqai naya banana chahte hain? (yes/no)")
        confirm = input("   > ").strip().lower()
        if confirm != "yes":
            print("❌ Cancelled. Existing data safe hai.")
            return

    clinic_id = str(uuid.uuid4())
    clinic = {
        "clinic_id": clinic_id,
        "name": "Green Park Medical Center",
        "subdomain": "greenpark",
        "address": "123 Main Street, Karachi",
        "phone": "+92-21-1234567",
        "email": "admin@greenpark.com",
        "logo_url": "",
        "settings": {
            "max_patients_per_day": 50,
            "slot_duration_minutes": 10,
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "whatsapp_enabled": True,
            "timezone": "Asia/Karachi",
        },
        "is_active": True,
    }
    await db["clinics"].insert_one(clinic)

    admin = {
        "_id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "email": "admin@greenpark.com",
        "hashed_password": hash_password("Admin@123"),
        "full_name": "Dr. Adnan Khan",
        "role": "clinic_admin",
        "is_active": True,
    }
    await db["admins"].insert_one(admin)

    doctors = [
        {"doctor_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "Adnan Khan",
         "specialization": "General Physician", "qualification": "MBBS, FCPS",
         "consultation_fee": 1500.0,
         "timings": [{"day": "Mon-Fri", "start_time": "09:00", "end_time": "17:00"}],
         "available_days": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
         "image_url": "", "bio": "15 years of experience.", "is_active": True},
        {"doctor_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "Sana Mirza",
         "specialization": "Cardiologist", "qualification": "MBBS, MD Cardiology",
         "consultation_fee": 3000.0,
         "timings": [{"day": "Mon-Wed", "start_time": "10:00", "end_time": "14:00"}],
         "available_days": ["Monday","Tuesday","Wednesday","Friday"],
         "image_url": "", "bio": "Specialist in cardiology.", "is_active": True},
        {"doctor_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "Omar Farooq",
         "specialization": "Dermatologist", "qualification": "MBBS, FCPS Dermatology",
         "consultation_fee": 2500.0,
         "timings": [{"day": "Tue-Sat", "start_time": "11:00", "end_time": "16:00"}],
         "available_days": ["Tuesday","Wednesday","Thursday","Friday","Saturday"],
         "image_url": "", "bio": "Skin expert.", "is_active": True},
    ]
    await db["doctors"].insert_many(doctors)

    lab_tests = [
        {"test_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "Complete Blood Count (CBC)",
         "category": "Blood Test", "description": "Blood components test",
         "fee": 800.0, "preparation": "No preparation", "duration_minutes": 15,
         "report_time_hours": 4, "is_active": True},
        {"test_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "Lipid Profile",
         "category": "Blood Test", "description": "Cholesterol test",
         "fee": 1200.0, "preparation": "Fast 9-12 hours", "duration_minutes": 15,
         "report_time_hours": 6, "is_active": True},
        {"test_id": str(uuid.uuid4()), "clinic_id": clinic_id, "name": "ECG",
         "category": "ECG", "description": "Heart activity",
         "fee": 700.0, "preparation": "No preparation", "duration_minutes": 15,
         "report_time_hours": 1, "is_active": True},
    ]
    await db["lab_tests"].insert_many(lab_tests)

    print("\n" + "=" * 60)
    print("🎉 NAYA CLINIC BAN GAYA!")
    print("=" * 60)
    print(f"  Clinic ID : {clinic_id}")
    print(f"  Email     : admin@greenpark.com")
    print(f"  Password  : Admin@123")
    print(f"\n  Chatbot   : http://localhost:3000/?clinic={clinic_id}")
    print(f"  Admin     : http://localhost:3000/admin/login")
    print("=" * 60)


if __name__ == "__main__":
    if "--fresh" in sys.argv:
        print("🆕 Fresh seed mode...")
        asyncio.run(fresh_seed())
    elif "--reset" in sys.argv:
        print("🔑 Password reset mode...")
        asyncio.run(reset_password())
    else:
        # DEFAULT — sirf dikhao, kuch change na karo
        asyncio.run(show_existing())