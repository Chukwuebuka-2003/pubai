from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Dict, Optional

class UserRegister(BaseModel):
    username: str
    password: str
    # FIX: Make email required for registration
    email: EmailStr

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserProfile(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    title: Optional[str] = None


class UpdateUserProfile(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    title: Optional[str] = None

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class SearchHistoryItem(BaseModel):
    id: int
    username: str
    query: str
    result_count: int
    timestamp: datetime
    articles: list

class SearchHistoryCreate(BaseModel):
    query: str
    result_count: int
    articles: list


class ExplainTermRequest(BaseModel):
    terms: List[str]
    abstracts: List[str] = []

class ExplainTermResponse(BaseModel):
    explanation: str


class MethodologyAnalysisRequest(BaseModel):
    abstract: str

class MethodologyAnalysisResponse(BaseModel):
    analysis: str

class ResearchGapRequest(BaseModel):
    abstracts: list[str]
    topic: str | None = None

class ResearchGapResponse(BaseModel):
    gaps: list[str]

class LiteratureReviewRequest(BaseModel):
    abstracts: list[str]
    topic: str

class LiteratureReviewResponse(BaseModel):
    review: str

class StudyComparisonRequest(BaseModel):
    studies: list[dict]  # Each dict: {title, abstract, [optional fields]}

class StudyComparisonResponse(BaseModel):
    comparison: str
