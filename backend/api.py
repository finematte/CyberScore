"""
FastAPI endpoints for CyberScore
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.database import (
    get_db,
    create_tables,
    Assessment,
    Answer,
    Area,
    Question,
    Recommendation,
    User,
    AreaScore,
    AssessmentRecommendation,
)
from backend.models import *
from backend.scoring import ScoringService
from config import settings

# Authentication configuration (using config.py)
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()


# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    user_id: int = Depends(verify_token), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


# Create FastAPI app
app = FastAPI(
    title="CyberScore API",
    description="Information Security Maturity Assessment Tool",
    version="1.0.0",
)


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()


# Health check
@app.get("/")
async def root():
    return {"message": "CyberScore API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Areas endpoints
@app.get("/areas", response_model=List[AreaResponse])
async def get_areas(db: Session = Depends(get_db)):
    """Get all security areas"""
    areas = db.query(Area).order_by(Area.order_index).all()
    return areas


@app.get("/areas/{area_id}", response_model=AreaResponse)
async def get_area(area_id: int, db: Session = Depends(get_db)):
    """Get a specific area by ID"""
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


# Questions endpoints
@app.get("/questions", response_model=List[QuestionResponse])
async def get_questions(db: Session = Depends(get_db)):
    """Get all questions"""
    questions = (
        db.query(Question).order_by(Question.area_id, Question.order_index).all()
    )
    return questions


@app.get("/questions/area/{area_id}", response_model=List[QuestionResponse])
async def get_questions_by_area(area_id: int, db: Session = Depends(get_db)):
    """Get questions for a specific area"""
    questions = (
        db.query(Question)
        .filter(Question.area_id == area_id)
        .order_by(Question.order_index)
        .all()
    )
    return questions


@app.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """Get a specific question by ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


# Assessments endpoints
@app.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(
    assessment: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new assessment"""
    if assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create assessment for another user",
        )
    db_assessment = Assessment(**assessment.model_dump())
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment


@app.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific assessment by ID"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return assessment


# Assessment with questions endpoint
@app.get(
    "/assessments/{assessment_id}/questions", response_model=AssessmentWithQuestions
)
async def get_assessment_with_questions(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get assessment with all areas and questions"""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Get all areas with their questions
    areas = db.query(Area).order_by(Area.order_index).all()
    areas_data = []

    for area in areas:
        questions = (
            db.query(Question)
            .filter(Question.area_id == area.id)
            .order_by(Question.order_index)
            .all()
        )
        areas_data.append(
            {
                "id": area.id,
                "area_id": area.area_id,
                "name": area.name,
                "description": area.description,
                "weight": area.weight,
                "questions": [
                    {
                        "id": q.id,
                        "question_id": q.question_id,  # Add stable identifier
                        "question_text": q.question_text,
                        "description": q.description,
                        "weight": q.weight,
                    }
                    for q in questions
                ],
            }
        )

    return AssessmentWithQuestions(assessment=assessment, areas=areas_data)


# Answers endpoints
@app.post("/answers", response_model=AnswerResponse)
async def create_answer(
    answer: AnswerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update an answer"""
    # Check if answer already exists
    existing_answer = (
        db.query(Answer)
        .filter(
            Answer.assessment_id == answer.assessment_id,
            Answer.question_id == answer.question_id,
        )
        .first()
    )

    if existing_answer:
        # Update existing answer
        existing_answer.score = answer.score
        existing_answer.notes = answer.notes
        db.commit()
        db.refresh(existing_answer)
        return existing_answer
    else:
        # Create new answer
        db_answer = Answer(**answer.model_dump())
        db.add(db_answer)
        db.commit()
        db.refresh(db_answer)
        return db_answer


@app.post("/answers/bulk")
async def create_bulk_answers(
    bulk_data: BulkAnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update multiple answers at once"""
    created_answers = []

    for answer_data in bulk_data.answers:
        answer_data.assessment_id = bulk_data.assessment_id

        # Check if answer already exists
        existing_answer = (
            db.query(Answer)
            .filter(
                Answer.assessment_id == answer_data.assessment_id,
                Answer.question_id == answer_data.question_id,
            )
            .first()
        )

        if existing_answer:
            # Update existing answer
            existing_answer.score = answer_data.score
            existing_answer.notes = answer_data.notes
            created_answers.append(existing_answer)
        else:
            # Create new answer
            db_answer = Answer(**answer_data.model_dump())
            db.add(db_answer)
            created_answers.append(db_answer)

    db.commit()

    for answer in created_answers:
        db.refresh(answer)

    return {"message": f"Successfully processed {len(created_answers)} answers"}


@app.get("/answers/assessment/{assessment_id}", response_model=List[AnswerResponse])
async def get_assessment_answers(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all answers for an assessment"""
    answers = db.query(Answer).filter(Answer.assessment_id == assessment_id).all()
    return answers


# Scoring endpoints
@app.post("/score", response_model=ScoringResponse)
async def calculate_score(
    request: ScoringRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate assessment score and generate recommendations"""
    scoring_service = ScoringService(db)

    try:
        results = scoring_service.get_assessment_results(request.assessment_id)

        return ScoringResponse(
            assessment_id=results["assessment_id"],
            total_score=results["total_score"],
            maturity_level=results["maturity_level"],
            area_scores=[
                AreaScoreResponse(
                    id=0,  # Will be set by database
                    assessment_id=request.assessment_id,
                    area_id=as_data["area_id"],
                    score=as_data["score"],
                    weighted_score=as_data["weighted_score"],
                    area_name=as_data["area_name"],
                    created_at=datetime.utcnow(),
                )
                for as_data in results["area_scores"]
            ],
            recommendations=[
                AssessmentRecommendationResponse(
                    id=0,  # Will be set by database
                    assessment_id=request.assessment_id,
                    recommendation_id=rec["recommendation_id"],
                    question_score=rec["question_score"],
                    is_applicable=True,
                    recommendation=RecommendationResponse(
                        id=rec["recommendation_id"],
                        question_id=0,
                        applies_if_score_below=3,
                        title=rec["title"],
                        description=rec["description"],
                        improvement_tips=rec["improvement_tips"],
                        iso_reference=rec["iso_reference"],
                        nist_reference=rec["nist_reference"],
                        cis_reference=rec["cis_reference"],
                        nis2_reference=rec.get("nis2_reference"),
                        priority=rec["priority"],
                        created_at=datetime.utcnow(),
                    ),
                    created_at=datetime.utcnow(),
                )
                for rec in results["recommendations"]
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Results endpoint
@app.get("/results/{assessment_id}")
def get_results(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Area scores joined with Area for area_name and area_id (string)
    area_rows = (
        db.query(AreaScore, Area.name, Area.area_id)
        .join(Area, Area.id == AreaScore.area_id)
        .filter(AreaScore.assessment_id == assessment_id)
        .all()
    )
    area_scores = [
        {
            "area_id": row.AreaScore.area_id,
            "area_id_str": row[2],
            "area_name": row[1],
            "score": float(row.AreaScore.score or 0),
            "weighted_score": float(row.AreaScore.weighted_score or 0),
        }
        for row in area_rows
    ]

    # Recommendations joined with Recommendation -> Question -> Area for full details
    rec_rows = (
        db.query(AssessmentRecommendation, Recommendation, Area.name, Question.question_id)
        .join(
            Recommendation,
            Recommendation.id == AssessmentRecommendation.recommendation_id,
        )
        .join(Question, Question.id == Recommendation.question_id)
        .join(Area, Area.id == Question.area_id)
        .filter(AssessmentRecommendation.assessment_id == assessment_id)
        .all()
    )
    recommendations = [
        {
            "recommendation_id": rec.Recommendation.id,
            "question_id": rec[3],
            "area_name": rec[2],
            "title": rec.Recommendation.title or "",
            "description": rec.Recommendation.description or "",
            "improvement_tips": rec.Recommendation.improvement_tips or "",
            "iso_reference": rec.Recommendation.iso_reference or "",
            "nist_reference": rec.Recommendation.nist_reference or "",
            "cis_reference": rec.Recommendation.cis_reference or "",
            "nis2_reference": rec.Recommendation.nis2_reference or "",
            "priority": rec.Recommendation.priority or "medium",
            "question_score": int(rec.AssessmentRecommendation.question_score or 0),
        }
        for rec in rec_rows
    ]

    return {
        "assessment": {
            "id": assessment.id,
            "total_score": float(assessment.total_score or 0),
            "maturity_level": assessment.maturity_level or "",
            "status": assessment.status,
        },
        "area_scores": area_scores,
        "recommendations": recommendations,
    }


# Recommendations endpoints
@app.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(db: Session = Depends(get_db)):
    """Get all recommendations"""
    recommendations = db.query(Recommendation).all()
    return recommendations


@app.get(
    "/recommendations/question/{question_id}",
    response_model=List[RecommendationResponse],
)
async def get_recommendations_by_question(
    question_id: int, db: Session = Depends(get_db)
):
    """Get recommendations for a specific question"""
    recommendations = (
        db.query(Recommendation).filter(Recommendation.question_id == question_id).all()
    )
    return recommendations


# Authentication endpoints
@app.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = (
        db.query(User)
        .filter((User.email == user_data.email) | (User.username == user_data.username))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        created_at=datetime.utcnow(),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/login")
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    # Find user by email or username
    user = (
        db.query(User)
        .filter(
            (User.email == login_data.email_or_username)
            | (User.username == login_data.email_or_username)
        )
        .first()
    )

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@app.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.get("/users/{user_id}/assessments", response_model=List[AssessmentResponse])
def get_user_assessments(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get assessments for a specific user (users can only see their own)"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    assessments = db.query(Assessment).filter(Assessment.user_id == user_id).all()
    return assessments


@app.get("/my-assessments", response_model=List[AssessmentResponse])
def get_my_assessments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's assessments"""
    assessments = (
        db.query(Assessment).filter(Assessment.user_id == current_user.id).all()
    )
    return assessments


@app.post("/areas", response_model=AreaResponse)
async def create_area(area: AreaCreate, db: Session = Depends(get_db)):
    """Create a new security area"""
    db_area = Area(**area.model_dump())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area


@app.put("/areas/{area_id}", response_model=AreaResponse)
async def update_area(area_id: int, area: AreaCreate, db: Session = Depends(get_db)):
    """Update a security area"""
    db_area = db.query(Area).filter(Area.id == area_id).first()
    if not db_area:
        raise HTTPException(status_code=404, detail="Area not found")

    for key, value in area.model_dump().items():
        setattr(db_area, key, value)

    db.commit()
    db.refresh(db_area)
    return db_area


@app.delete("/areas/{area_id}")
async def delete_area(area_id: int, db: Session = Depends(get_db)):
    """Delete a security area"""
    db_area = db.query(Area).filter(Area.id == area_id).first()
    if not db_area:
        raise HTTPException(status_code=404, detail="Area not found")

    db.delete(db_area)
    db.commit()
    return {"message": "Area deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
