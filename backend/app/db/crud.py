from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import User, CustomDictionaryEntry

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, password_hash: str, dialect: str = "ASL"):
    db_user = User(username=username, password_hash=password_hash)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    from app.db.models import DialectProfile
    db_profile = DialectProfile(user_id=db_user.id, primary_dialect=dialect)
    db.add(db_profile)
    await db.commit()
    
    return db_user

async def add_custom_dictionary_entry(db: AsyncSession, user_id: int, gesture_sequence: str, meaning: str):
    entry = CustomDictionaryEntry(user_id=user_id, gesture_sequence=gesture_sequence, meaning=meaning)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

async def get_user_custom_dictionary(db: AsyncSession, user_id: int):
    result = await db.execute(select(CustomDictionaryEntry).filter(CustomDictionaryEntry.user_id == user_id))
    return result.scalars().all()
