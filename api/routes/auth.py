from fastapi import APIRouter, HTTPException, Depends
from models.user import AdminCreate, LoginRequest, TokenResponse, AdminInDB, AdminResponse
from models.clinic import ClinicCreate, ClinicInDB
from core.security import hash_password, verify_password, create_access_token
from core.dependencies import get_current_admin
from db.mongodb import get_db
import uuid

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register-clinic", response_model=dict, summary="Register a new clinic with admin account")
async def register_clinic(data: dict, db=Depends(get_db)):
    """
    One-shot endpoint to create a new clinic + admin account.
    This is how you onboard a new clinic client.
    
    Body: {
        clinic_name, subdomain, address, phone, email, logo_url,
        admin_email, admin_password, admin_name
    }
    """
    # Check subdomain uniqueness
    existing = await db["clinics"].find_one({"subdomain": data.get("subdomain")})
    if existing:
        raise HTTPException(400, detail="Subdomain already taken")

    # Create clinic
    clinic_id = str(uuid.uuid4())
    clinic_doc = {
        "clinic_id": clinic_id,
        "name": data["clinic_name"],
        "subdomain": data["subdomain"],
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "logo_url": data.get("logo_url", ""),
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
    await db["clinics"].insert_one(clinic_doc)

    # Create admin
    admin_id = str(uuid.uuid4())
    admin_doc = {
        "_id": admin_id,
        "clinic_id": clinic_id,
        "email": data["admin_email"],
        "hashed_password": hash_password(data["admin_password"]),
        "full_name": data["admin_name"],
        "role": "clinic_admin",
        "is_active": True,
    }
    await db["admins"].insert_one(admin_doc)

    return {
        "success": True,
        "clinic_id": clinic_id,
        "message": f"Clinic '{data['clinic_name']}' created successfully",
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db=Depends(get_db)):
    admin = await db["admins"].find_one({
        "email": data.email,
        "clinic_id": data.clinic_id,
        "is_active": True,
    })
    if not admin or not verify_password(data.password, admin["hashed_password"]):
        raise HTTPException(401, detail="Invalid credentials")

    clinic = await db["clinics"].find_one({"clinic_id": data.clinic_id})
    if not clinic or not clinic.get("is_active"):
        raise HTTPException(403, detail="Clinic not found or inactive")

    token = create_access_token({
        "sub": admin["_id"],
        "clinic_id": data.clinic_id,
        "role": admin["role"],
        "email": admin["email"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": {
            "id": admin["_id"],
            "clinic_id": admin["clinic_id"],
            "email": admin["email"],
            "full_name": admin["full_name"],
            "role": admin["role"],
            "is_active": admin["is_active"],
        },
        "clinic_name": clinic["name"],
    }


@router.get("/me")
async def get_me(current_admin=Depends(get_current_admin)):
    current_admin["_id"] = str(current_admin["_id"])
    return current_admin
