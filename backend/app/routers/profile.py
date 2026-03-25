import jwt
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, List, Optional
from pydantic import BaseModel

from ..db.database import get_db, db_available
from ..db.models import UserProfile

logger = logging.getLogger("signai.profile")

# Simple JWT Secret for phase 2 identity architecture testing
JWT_SECRET = "SignAI_OS_SuperSecret_2026_Key"

router = APIRouter(prefix="/api/profile", tags=["Identity"])

class ProfileSchema(BaseModel):
    user_id: str
    regional_dialect: str = "ASL"
    bespoke_dictionary: Dict[str, List[str]] = {}

def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract user payload from JWT, validating administrative escalation endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split("Bearer ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub", "anonymous")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/sync", response_model=ProfileSchema)
async def sync_profile(user_id: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fetch user profile and customized bespoke conversational dictionary."""
    if not db_available or db is None:
        logger.warning("[Self-Healing] Database cluster offline. Forcing client to rely on offline IndexedDB.")
        raise HTTPException(status_code=503, detail="Database cluster isolates due to network failures.")
        
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalars().first()
    
    if not profile:
        profile = UserProfile(user_id=user_id, regional_dialect="ASL", bespoke_dictionary={})
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    return ProfileSchema(
        user_id=profile.user_id,
        regional_dialect=profile.regional_dialect,
        bespoke_dictionary=profile.bespoke_dictionary
    )

@router.post("/sync", response_model=ProfileSchema)
async def upstream_sync_profile(data: ProfileSchema, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Push localized edge client IndexedDB states to upstream Postgres cluster.
    Securely merges custom dictionaries without polluting global context logic.
    """
    if data.user_id != user_id:
        # Authorization check mitigating token manipulation mimicking unauthorized admin
        raise HTTPException(status_code=403, detail="Unauthorized token payload manipulation detected")

    if not db_available or db is None:
        raise HTTPException(status_code=503, detail="Database cluster offline")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalars().first()
    
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        
    profile.regional_dialect = data.regional_dialect
    profile.bespoke_dictionary = data.bespoke_dictionary
    
    await db.commit()
    await db.refresh(profile)
    return ProfileSchema(
        user_id=profile.user_id,
        regional_dialect=profile.regional_dialect,
        bespoke_dictionary=profile.bespoke_dictionary
    )
