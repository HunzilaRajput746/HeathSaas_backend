from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient = None


async def connect_db():
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)
    # Verify connection
    await _client.admin.command("ping")
    print("✅ Connected to MongoDB Atlas")


async def close_db():
    global _client
    if _client:
        _client.close()
        print("🔌 MongoDB connection closed")


def get_db():
    """Return the database instance. Used as a FastAPI dependency."""
    return _client[settings.mongodb_db_name]


async def create_indexes(db):
    """Create all necessary indexes for performance and uniqueness."""
    # Clinics
    await db["clinics"].create_index("clinic_id", unique=True)
    await db["clinics"].create_index("subdomain", unique=True)

    # Admins
    await db["admins"].create_index([("email", 1), ("clinic_id", 1)], unique=True)

    # Doctors
    await db["doctors"].create_index("clinic_id")

    # Lab Tests
    await db["lab_tests"].create_index("clinic_id")

    # Appointments
    await db["appointments"].create_index([("clinic_id", 1), ("date", 1)])
    await db["appointments"].create_index([("clinic_id", 1), ("phone", 1)])

    print("✅ Database indexes created")
