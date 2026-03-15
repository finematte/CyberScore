"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


# User Models
class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email_or_username: str
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# Area Models
class AreaBase(BaseModel):
    area_id: Optional[str] = None  # Stable identifier from JSON (e.g., "GOVERN")
    name: str
    description: Optional[str] = None
    weight: Decimal = 1.00
    order_index: int = 0


class AreaCreate(AreaBase):
    pass


class AreaResponse(AreaBase):
    id: int
    area_id: str  # Make required in response
    created_at: datetime

    class Config:
        from_attributes = True


# Question Models
class QuestionBase(BaseModel):
    question_id: Optional[str] = None  # Stable identifier from JSON (e.g., "GOV_Q1")
    question_text: str
    description: Optional[str] = None
    weight: Decimal = 1.00
    order_index: int = 0


class QuestionCreate(QuestionBase):
    area_id: int


class QuestionResponse(QuestionBase):
    id: int
    area_id: int
    question_id: str  # Make required in response
    created_at: datetime

    class Config:
        from_attributes = True


# Assessment Models
class AssessmentBase(BaseModel):
    title: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    user_id: int


class AssessmentResponse(AssessmentBase):
    id: int
    user_id: int
    status: str
    total_score: Optional[Decimal] = None
    maturity_level: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Answer Models
class AnswerBase(BaseModel):
    score: int  # 0-5 scale
    notes: Optional[str] = None


class AnswerCreate(AnswerBase):
    assessment_id: int
    question_id: int


class AnswerResponse(AnswerBase):
    id: int
    assessment_id: int
    question_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Area Score Models
class AreaScoreResponse(BaseModel):
    id: int
    assessment_id: int
    area_id: int
    score: Decimal
    weighted_score: Decimal
    area_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Recommendation Models
class RecommendationBase(BaseModel):
    applies_if_score_below: int = 3  # Renamed from threshold_score for clarity
    title: str
    description: str
    improvement_tips: Optional[str] = None
    iso_reference: Optional[str] = None
    nist_reference: Optional[str] = None
    cis_reference: Optional[str] = None
    nis2_reference: Optional[str] = None  # Added for NIS2 compliance references
    priority: str = "medium"


class RecommendationCreate(RecommendationBase):
    question_id: int


class RecommendationResponse(RecommendationBase):
    id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Assessment Recommendation Models
class AssessmentRecommendationResponse(BaseModel):
    id: int
    assessment_id: int
    recommendation_id: int
    question_score: int
    is_applicable: bool
    recommendation: RecommendationResponse
    created_at: datetime

    class Config:
        from_attributes = True


# Scoring Models
class ScoringRequest(BaseModel):
    assessment_id: int


class ScoringResponse(BaseModel):
    assessment_id: int
    total_score: Decimal
    maturity_level: str
    area_scores: List[AreaScoreResponse]
    recommendations: List[AssessmentRecommendationResponse]


# Assessment with Questions Model
class AssessmentWithQuestions(BaseModel):
    assessment: AssessmentResponse
    areas: List[dict]  # Will contain area info with questions


# Bulk Answer Submission
class BulkAnswerSubmission(BaseModel):
    assessment_id: int
    answers: List[AnswerCreate]
