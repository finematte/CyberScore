"""
Database configuration and models for CyberScore
"""

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DECIMAL,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime
from config import settings

engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessments = relationship("Assessment", back_populates="user")


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., "GOVERN", "IDENTIFY"
    name = Column(String(100), nullable=False)
    description = Column(Text)
    weight = Column(DECIMAL(3, 2), default=1.00)
    order_index = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    questions = relationship("Question", back_populates="area")
    area_scores = relationship("AreaScore", back_populates="area")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    question_id = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., "GOV_Q1", "ID_Q2"
    question_text = Column(Text, nullable=False)
    description = Column(Text)
    weight = Column(DECIMAL(3, 2), default=1.00)
    order_index = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    area = relationship("Area", back_populates="questions")
    answers = relationship("Answer", back_populates="question")
    recommendations = relationship("Recommendation", back_populates="question")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200))
    status = Column(String(20), default="in_progress")
    total_score = Column(DECIMAL(5, 2))
    maturity_level = Column(String(20))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)

    # Relationships
    user = relationship("User", back_populates="assessments")
    answers = relationship("Answer", back_populates="assessment")
    area_scores = relationship("AreaScore", back_populates="assessment")
    assessment_recommendations = relationship(
        "AssessmentRecommendation", back_populates="assessment"
    )


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    score = Column(Integer)  # 0-5 scale
    notes = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class AreaScore(Base):
    __tablename__ = "area_scores"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "area_id", name="uq_area_scores_assessment_area"
        ),
        Index("idx_area_scores_assessment_id", "assessment_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    score = Column(DECIMAL(5, 2), nullable=False)
    weighted_score = Column(DECIMAL(5, 2), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="area_scores")
    area = relationship("Area", back_populates="area_scores")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    applies_if_score_below = Column(
        Integer, default=3
    )  # Renamed from threshold_score for clarity
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    improvement_tips = Column(Text)
    iso_reference = Column(String(100))
    nist_reference = Column(String(100))
    cis_reference = Column(String(100))
    nis2_reference = Column(String(100))  # Added for NIS2 compliance references
    priority = Column(String(20), default="medium")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    question = relationship("Question", back_populates="recommendations")
    assessment_recommendations = relationship(
        "AssessmentRecommendation", back_populates="recommendation"
    )


class AssessmentRecommendation(Base):
    __tablename__ = "assessment_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "recommendation_id",
            name="uq_assessment_recommendations_pair",
        ),
        Index("idx_assessment_recommendations_assessment_id", "assessment_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id"), nullable=False
    )
    question_score = Column(Integer, nullable=False)
    is_applicable = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="assessment_recommendations")
    recommendation = relationship(
        "Recommendation", back_populates="assessment_recommendations"
    )


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)
