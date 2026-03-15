"""
Scoring logic for CyberScore assessment (idempotent version)
"""

from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import List, Dict
from decimal import Decimal
from backend.database import (
    Assessment,
    Answer,
    Area,
    Question,
    AreaScore,
    Recommendation,
    AssessmentRecommendation,
)


class ScoringService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_assessment_score(self, assessment_id: int) -> Dict:
        """
        Calculate total score and area scores for an assessment.
        Idempotent: clears old area_scores for this assessment before inserting fresh rows.
        Returns: dict with total_score, maturity_level, area_scores
        """
        # Get assessment
        assessment = (
            self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        )
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # Get all answers for this assessment
        answers = (
            self.db.query(Answer).filter(Answer.assessment_id == assessment_id).all()
        )
        if not answers:
            raise ValueError(f"No answers found for assessment {assessment_id}")

        # Clean previous area scores (idempotency)
        self.db.execute(
            delete(AreaScore).where(AreaScore.assessment_id == assessment_id)
        )
        self.db.flush()

        # Group answers by area
        answers_by_area = {}
        for answer in answers:
            area_id = answer.question.area_id
            answers_by_area.setdefault(area_id, []).append(answer)

        # Calculate area scores
        area_scores = []
        total_weighted_score = Decimal("0")
        total_area_weight = Decimal("0")

        for area_id, area_answers in answers_by_area.items():
            area = self.db.query(Area).filter(Area.id == area_id).first()
            if not area:
                continue

            # Calculate weighted average for this area (0-100%)
            # Formula: sum(question_score * question_weight) / sum(max_score * question_weight) * 100
            area_weighted_points = Decimal("0")
            max_area_weighted_points = Decimal("0")
            default_max_score = Decimal("5")  # Maximum score per question

            for answer in area_answers:
                question_weight = Decimal(str(answer.question.weight))
                score = Decimal(str(answer.score))

                area_weighted_points += score * question_weight
                max_area_weighted_points += default_max_score * question_weight

            # Area score as weighted average (0-100%)
            if max_area_weighted_points > 0:
                weighted_area_score = (
                    area_weighted_points / max_area_weighted_points
                ) * 100
            else:
                weighted_area_score = Decimal("0")

            # Store area score
            area_score_record = AreaScore(
                assessment_id=assessment_id,
                area_id=area_id,
                score=weighted_area_score,  # Use weighted score as primary
                weighted_score=weighted_area_score,
            )
            self.db.add(area_score_record)

            area_scores.append(
                {
                    "area_id": area_id,
                    "area_name": area.name,
                    "score": float(weighted_area_score),
                    "weighted_score": float(weighted_area_score),
                    "weight": float(area.weight),
                }
            )

            # Accumulate for overall weighted score
            area_weight = Decimal(str(area.weight))
            total_weighted_score += weighted_area_score * area_weight
            total_area_weight += area_weight

        # Calculate overall score as weighted average of area scores
        # Formula: sum(area_score * area_weight) / sum(area_weight)
        if total_area_weight > 0:
            weighted_total_score = total_weighted_score / total_area_weight
        else:
            weighted_total_score = Decimal("0")
        # Determine maturity level
        maturity_level = self._determine_maturity_level(weighted_total_score)

        # Update assessment
        assessment.total_score = weighted_total_score
        assessment.maturity_level = maturity_level
        assessment.status = "completed"

        self.db.commit()

        return {
            "total_score": weighted_total_score,
            "maturity_level": maturity_level,
            "area_scores": area_scores,
        }

    def _determine_maturity_level(self, score: Decimal) -> str:
        """Determine maturity level based on score"""
        if score < Decimal("40"):
            return "Low"
        elif score < Decimal("70"):
            return "Medium"
        else:
            return "High"

    def generate_recommendations(self, assessment_id: int) -> List[Dict]:
        """
        Generate recommendations based on low-scoring answers.
        Idempotent: clears previous assessment_recommendations for this assessment first.
        Returns: list of recommendation dictionaries.
        """
        # Clean previous recommendations (idempotency)
        self.db.execute(
            delete(AssessmentRecommendation).where(
                AssessmentRecommendation.assessment_id == assessment_id
            )
        )
        self.db.flush()

        # Get all answers for this assessment
        answers = (
            self.db.query(Answer).filter(Answer.assessment_id == assessment_id).all()
        )

        recommendations = []

        for answer in answers:
            # Get recommendations for this question where score is below threshold
            question_recommendations = (
                self.db.query(Recommendation)
                .filter(Recommendation.question_id == answer.question_id)
                .all()
            )

            for rec in question_recommendations:
                # Check if answer score is below the threshold
                if answer.score < rec.applies_if_score_below:
                    # Create assessment recommendation record
                    assessment_rec = AssessmentRecommendation(
                        assessment_id=assessment_id,
                        recommendation_id=rec.id,
                        question_score=answer.score,
                        is_applicable=True,
                    )
                    self.db.add(assessment_rec)

                    recommendations.append(
                        {
                            "recommendation_id": rec.id,
                            "title": rec.title,
                            "description": rec.description,
                            "improvement_tips": rec.improvement_tips,
                            "iso_reference": rec.iso_reference,
                            "nist_reference": rec.nist_reference,
                            "cis_reference": rec.cis_reference,
                            "nis2_reference": rec.nis2_reference,
                            "priority": rec.priority,
                            "question_score": answer.score,
                            "area_name": answer.question.area.name,
                            "question_text": answer.question.question_text,
                            "question_id": answer.question.question_id,
                        }
                    )

        self.db.commit()
        return recommendations

    def get_assessment_results(self, assessment_id: int) -> Dict:
        """
        Get complete assessment results including scores and recommendations.
        Ensures idempotent scoring + rec generation pipeline.
        """
        # Calculate scores
        score_data = self.calculate_assessment_score(assessment_id)

        # Generate recommendations
        recommendations = self.generate_recommendations(assessment_id)

        # Get area scores from database
        area_scores = (
            self.db.query(AreaScore)
            .filter(AreaScore.assessment_id == assessment_id)
            .all()
        )

        return {
            "assessment_id": assessment_id,
            "total_score": score_data["total_score"],
            "maturity_level": score_data["maturity_level"],
            "area_scores": [
                {
                    "area_id": as_record.area_id,
                    "area_name": as_record.area.name,
                    "score": as_record.score,
                    "weighted_score": as_record.weighted_score,
                }
                for as_record in area_scores
            ],
            "recommendations": recommendations,
        }
