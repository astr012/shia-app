from sqlalchemy import Column, String, JSON, Integer
from .database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    
    # E.g. "ASL", "BSL", "ISL"
    regional_dialect = Column(String, default="ASL")
    
    # Custom mappings of English concepts to specific gesture arrays 
    # e.g. {"grandma": ["TAPPING_CHIN", "FAMILY"], "boss": ["SALUTE"]}
    bespoke_dictionary = Column(JSON, default=dict)
