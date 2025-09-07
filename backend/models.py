from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=True)
    title = Column(String, nullable=True)


class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, ForeignKey("users.username"), index=True)
    query = Column(String, nullable=False)
    result_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    articles = Column(Text)
