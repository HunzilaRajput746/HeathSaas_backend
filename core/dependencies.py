from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_token
from db.mongodb import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_admin(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """Extract admin user from JWT and validate clinic ownership."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin = await db["admins"].find_one({"_id": payload.get("sub"), "clinic_id": payload.get("clinic_id")})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return admin


async def get_clinic_id_from_token(token: str = Depends(oauth2_scheme)) -> str:
    """Extract clinic_id from JWT for tenant-scoped queries."""
    payload = decode_token(token)
    if not payload or not payload.get("clinic_id"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["clinic_id"]
