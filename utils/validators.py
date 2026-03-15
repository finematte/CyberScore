"""
Input validation utilities for CyberScore
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator
import re


class AssessmentData(BaseModel):
    """Validate assessment data"""

    user_id: int
    title: str

    @validator("title")
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Assessment title cannot be empty")
        if len(v) > 200:
            raise ValueError("Assessment title must be less than 200 characters")
        return v.strip()


class AnswerData(BaseModel):
    """Validate answer data"""

    assessment_id: int
    question_id: int
    score: int
    notes: Optional[str] = None

    @validator("score")
    def validate_score(cls, v):
        if not isinstance(v, int):
            raise ValueError("Score must be an integer")
        if v < 0 or v > 5:
            raise ValueError("Score must be between 0 and 5")
        return v

    @validator("notes")
    def validate_notes(cls, v):
        if v and len(v) > 1000:
            raise ValueError("Notes must be less than 1000 characters")
        return v


class UserRegistrationData(BaseModel):
    """Validate user registration data"""

    username: str
    email: str
    password: str

    @validator("username")
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Username is required")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Username must be less than 50 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v.strip()

    @validator("email")
    def validate_email(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Email is required")
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()

    @validator("password")
    def validate_password(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Password is required")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserLoginData(BaseModel):
    """Validate user login data"""

    email_or_username: str
    password: str

    @validator("email_or_username")
    def validate_email_or_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Email or username is required")
        return v.strip()

    @validator("password")
    def validate_password(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Password is required")
        return v


def validate_assessment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize assessment data"""
    try:
        validated = AssessmentData(**data)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Invalid assessment data: {str(e)}")


def validate_answer_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize answer data"""
    try:
        validated = AnswerData(**data)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Invalid answer data: {str(e)}")


def validate_user_registration_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize user registration data"""
    try:
        validated = UserRegistrationData(**data)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Invalid registration data: {str(e)}")


def validate_user_login_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize user login data"""
    try:
        validated = UserLoginData(**data)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Invalid login data: {str(e)}")


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize string input"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';()&]', "", str(text))

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def validate_score(score: Any) -> int:
    """Validate and convert score to integer"""
    try:
        score_int = int(score)
        if score_int < 0 or score_int > 5:
            raise ValueError("Score must be between 0 and 5")
        return score_int
    except (ValueError, TypeError):
        raise ValueError("Score must be a valid integer between 0 and 5")
