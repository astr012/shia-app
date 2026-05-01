from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re
from app.db.database import get_db
from app.db import crud, models
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])

class CustomWordCreate(BaseModel):
    gesture_sequence: str = Field(..., max_length=100, pattern=r'^[\w\s-]+$')
    meaning: str = Field(..., max_length=200)

    @field_validator('meaning')
    def sanitize_meaning(cls, v):
        # Prevent prompt injection and control characters
        sanitized = re.sub(r'[^\w\s\.,\?!-]', '', v)
        if len(sanitized.strip()) == 0:
            raise ValueError("Meaning cannot be empty after sanitization")
        return sanitized.strip()

@router.post("/custom-words", response_model=Dict[str, Any])
async def add_custom_word(
    word: CustomWordCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        entry = await crud.add_custom_dictionary_entry(
            db, 
            user_id=current_user.id, 
            gesture_sequence=word.gesture_sequence, 
            meaning=word.meaning
        )
        return {"id": entry.id, "meaning": entry.meaning, "gesture_sequence": entry.gesture_sequence}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Database integrity error.")

@router.get("/custom-words", response_model=List[Dict[str, Any]])
async def get_custom_dictionary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entries = await crud.get_user_custom_dictionary(db, current_user.id)
    return [{"id": e.id, "gesture_sequence": e.gesture_sequence, "meaning": e.meaning} for e in entries]
