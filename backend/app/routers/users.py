from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
from app.db.database import get_db
from app.db import crud

router = APIRouter(prefix="/api/users", tags=["Users"])

class UserCreate(BaseModel):
    username: str
    dialect: str = "ASL"

class CustomWordCreate(BaseModel):
    gesture_sequence: str
    meaning: str

@router.post("/", response_model=Dict[str, Any])
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_username(db, username=user.username)
    if db_user:
        # For idempotency: return existing user
        return {"id": db_user.id, "username": db_user.username, "dialect": db_user.dialect, "status": "existing"}
    new_user = await crud.create_user(db, username=user.username, dialect=user.dialect)
    return {"id": new_user.id, "username": new_user.username, "dialect": new_user.dialect, "status": "created"}

@router.post("/{user_id}/custom-words", response_model=Dict[str, Any])
async def add_custom_word(user_id: int, word: CustomWordCreate, db: AsyncSession = Depends(get_db)):
    try:
        entry = await crud.add_custom_dictionary_entry(
            db, 
            user_id=user_id, 
            gesture_sequence=word.gesture_sequence, 
            meaning=word.meaning
        )
        return {"id": entry.id, "meaning": entry.meaning, "gesture_sequence": entry.gesture_sequence}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Database integrity error or invalid user_id.")

@router.get("/{username}/custom-words", response_model=List[Dict[str, Any]])
async def get_custom_dictionary(username: str, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_username(db, username=username)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    entries = await crud.get_user_custom_dictionary(db, db_user.id)
    return [{"id": e.id, "gesture_sequence": e.gesture_sequence, "meaning": e.meaning} for e in entries]
