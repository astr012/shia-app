from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class DialectProfileBase(BaseModel):
    primary_dialect: str
    regional_modifications: Dict[str, Any] = {}

class DialectProfileCreate(DialectProfileBase):
    pass

class DialectProfileResponse(DialectProfileBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

class ConversationalContextBase(BaseModel):
    session_id: str
    context_data: Dict[str, Any] = {}

class ConversationalContextCreate(ConversationalContextBase):
    pass

class ConversationalContextResponse(ConversationalContextBase):
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CustomDictionaryEntryBase(BaseModel):
    gesture_sequence: str
    meaning: str

class CustomDictionaryEntryCreate(CustomDictionaryEntryBase):
    pass

class CustomDictionaryEntryResponse(CustomDictionaryEntryBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str
    role: str = "user"
    preferences: Dict[str, Any] = {}

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    dialect_profile: Optional[DialectProfileResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# WebSocket Multi-Dimensional Vector DTOs
# ---------------------------------------------------------
class LandmarkPoint(BaseModel):
    x: float
    y: float
    z: float
    visibility: Optional[float] = None

class VisionPayload(BaseModel):
    hands: Optional[List[List[LandmarkPoint]]] = None
    pose: Optional[List[LandmarkPoint]] = None
    face: Optional[List[List[LandmarkPoint]]] = None
    gestures: Optional[List[str]] = None
    confidence: Optional[float] = None
    timestamp: Optional[float] = None
