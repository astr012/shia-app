from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    dialect = Column(String, default="ASL")  # e.g., ASL, BSL, ISL
    role = Column(String, default="user", nullable=False)  # user | admin
    preferences = Column(JSON, default={})  # Store UI preferences

    custom_words = relationship("CustomDictionaryEntry", back_populates="user")


class CustomDictionaryEntry(Base):
    __tablename__ = "custom_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gesture_sequence = Column(String, index=True, nullable=False) # e.g., "THUMBS_UP POINT"
    meaning = Column(String, nullable=False) # "Hello friend"
    
    user = relationship("User", back_populates="custom_words")
