"""
Security utilities for CyberScore
"""

import re
import hashlib
import secrets
from typing import List, Optional
from passlib.context import CryptContext
from config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Validate password strength based on configuration
    Returns (is_valid, error_messages)
    """
    errors = []

    # Check minimum length
    if len(password) < settings.password_min_length:
        errors.append(
            f"Password must be at least {settings.password_min_length} characters long"
        )

    # Check for special characters
    if settings.password_require_special_chars:
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

    # Check for numbers
    if settings.password_require_numbers:
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one number")

    # Check for uppercase letters
    if settings.password_require_uppercase:
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

    return len(errors) == 0, errors


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", '"', "'", "&", ";", "(", ")", "script", "javascript"]
    sanitized = text

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    return sanitized.strip()


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """Validate username format"""
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 50:
        return False, "Username must be less than 50 characters"

    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return (
            False,
            "Username can only contain letters, numbers, underscores, and hyphens",
        )

    return True, None
