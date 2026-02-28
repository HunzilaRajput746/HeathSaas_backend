"""
Yeh script purani 083ce1af clinic ID wali appointments ko
9aaaea92 se update karega taake dashboard mein dikh sakein.
Run ONCE only.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

OLD_CLINIC_ID = "083ce1af-409b-4a39-b59d-410cff7da9ef"
NEW_CLINIC_ID = "9aaaea92-2408-4c9e-8884-e9c119dde575"

async def fix():
    client = AsyncIOMotorClient(
        os.getenv('MONGODB_URL'),
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    db = client['healthsaas']

    # Find old appointments
    old = await db['appointments'].find(
        {"clinic_id": OLD_CLINIC_ID}
    ).to_list(100)
    
    print(f"Found {len(old)} appointments with old clinic ID")
    
    if old:
        result = await db['appointments'].update_many(
            {"clinic_id": OLD_CLINIC_ID},
            {"$set": {"clinic_id": NEW_CLINIC_ID}}
        )
        print(f"✅ Fixed {result.modified_count} appointments!")
    else:
        print("No old appointments found — already fixed!")

    # Verify
    all_appts = await db['appointments'].find({}).to_list(100)
    print(f"\nAll appointments now:")
    for a in all_appts:
        print(f"  {a.get('patient_name')} | {a.get('date')} | {a.get('clinic_id', '')[:8]}")

    client.close()

asyncio.run(fix())
