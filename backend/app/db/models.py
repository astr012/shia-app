from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # user | admin
    preferences = Column(JSON, default={})  # Store UI preferences

    custom_words = relationship("CustomDictionaryEntry", back_populates="user")
    dialect_profile = relationship("DialectProfile", back_populates="user", uselist=False)
    conversations = relationship("ConversationalContext", back_populates="user")

class DialectProfile(Base):
    __tablename__ = "dialect_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    primary_dialect = Column(String, default="ASL", nullable=False) # ASL, BSL, ISL
    regional_modifications = Column(JSON, default={}) # Specific mapped adjustments

    user = relationship("User", back_populates="dialect_profile")

class ConversationalContext(Base):
    __tablename__ = "conversational_contexts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, index=True)
    context_data = Column(JSON, default={}) # Recent translations/topic memory
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="conversations")

class CustomDictionaryEntry(Base):
    __tablename__ = "custom_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gesture_sequence = Column(String, index=True, nullable=False) # e.g., "THUMBS_UP POINT"
    meaning = Column(String, nullable=False) # "Hello friend"
    
    user = relationship("User", back_populates="custom_words")
