from sqlalchemy import Column, String, Integer, Date, DateTime
from sqlalchemy.sql import func
from database import Base



class Maps(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    long_url = Column(String, index=True)
    shortened_url = Column(String, unique=True, index=True)
    unique_code = Column(String, index=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())