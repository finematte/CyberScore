"""
Seed database from JSON files - Single source of truth for assessment model
Reads area1_govern.json through area6_recover.json and upserts into database
"""

import sys
import json
from pathlib import Path
from decimal import Decimal

# Add the parent directory to the path so we can import backend modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from sqlalchemy.orm import Session
from backend.database import (
    SessionLocal,
    Area,
    Question,
    Recommendation,
    create_tables,
)


def load_json_area(file_path: Path) -> dict:
    """Load and validate a single area JSON file"""
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate required fields
    required_fields = [
        "area_id",
        "name",
        "description",
        "weight",
        "questions",
        "recommendations",
    ]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {file_path}")

    return data


def seed_from_json(json_dir: Path = None):
    """
    Seed database from JSON files in db_data directory.
    Uses upsert logic: updates existing records if area_id/question_id match, creates new ones otherwise.
    """
    if json_dir is None:
        json_dir = parent_dir / "db_data"

    if not json_dir.exists():
        raise FileNotFoundError(f"JSON directory not found: {json_dir}")

    # Ensure tables exist
    create_tables()

    db = SessionLocal()

    try:
        # Find all area JSON files
        json_files = sorted(json_dir.glob("area*.json"))

        if not json_files:
            raise FileNotFoundError(f"No area JSON files found in {json_dir}")

        print(f"Found {len(json_files)} area JSON files")

        # Process each area file
        for json_file in json_files:
            print(f"\nProcessing {json_file.name}...")
            area_data = load_json_area(json_file)

            # Upsert Area
            area = db.query(Area).filter(Area.area_id == area_data["area_id"]).first()
            if area:
                # Update existing area
                area.name = area_data["name"]
                area.description = area_data["description"]
                area.weight = Decimal(str(area_data["weight"]))
                # Keep existing order_index or set based on file order
                if area.order_index == 0:
                    area.order_index = len(json_files) - json_files.index(json_file)
                print(f"  Updated area: {area_data['area_id']} ({area.name})")
            else:
                # Create new area
                area = Area(
                    area_id=area_data["area_id"],
                    name=area_data["name"],
                    description=area_data["description"],
                    weight=Decimal(str(area_data["weight"])),
                    order_index=json_files.index(json_file) + 1,
                )
                db.add(area)
                print(f"  Created area: {area_data['area_id']} ({area.name})")

            db.flush()  # Get area.id

            # Process questions
            questions_map = {}  # Map question_id (string) to Question object
            for idx, q_data in enumerate(area_data["questions"]):
                # Upsert Question
                question = (
                    db.query(Question)
                    .filter(Question.question_id == q_data["question_id"])
                    .first()
                )

                if question:
                    # Update existing question
                    question.area_id = area.id
                    question.question_text = q_data["text"]
                    question.description = q_data.get("description")
                    question.weight = Decimal(str(q_data.get("weight", 1.0)))
                    question.order_index = idx + 1
                    print(f"    Updated question: {q_data['question_id']}")
                else:
                    # Create new question
                    question = Question(
                        area_id=area.id,
                        question_id=q_data["question_id"],
                        question_text=q_data["text"],
                        description=q_data.get("description"),
                        weight=Decimal(str(q_data.get("weight", 1.0))),
                        order_index=idx + 1,
                    )
                    db.add(question)
                    print(f"    Created question: {q_data['question_id']}")

                db.flush()  # Get question.id
                questions_map[q_data["question_id"]] = question

            # Process recommendations
            for rec_data in area_data["recommendations"]:
                question_id_key = rec_data["question_id"]
                if question_id_key not in questions_map:
                    print(
                        f"    Warning: Question ID {question_id_key} not found, skipping recommendation"
                    )
                    continue

                question = questions_map[question_id_key]

                # Check if recommendation already exists (by question_id and title)
                existing_rec = (
                    db.query(Recommendation)
                    .filter(
                        Recommendation.question_id == question.id,
                        Recommendation.title == rec_data["title"],
                    )
                    .first()
                )

                if existing_rec:
                    # Update existing recommendation
                    existing_rec.applies_if_score_below = rec_data.get(
                        "applies_if_score_below", 3
                    )
                    existing_rec.description = rec_data["description"]
                    existing_rec.improvement_tips = rec_data.get("improvement_tips")
                    existing_rec.iso_reference = rec_data.get("iso_ref")
                    existing_rec.nist_reference = rec_data.get("nist_ref")
                    existing_rec.cis_reference = rec_data.get("cis_ref")
                    existing_rec.nis2_reference = rec_data.get("nis2_ref")
                    existing_rec.priority = rec_data.get("priority", "medium")
                    print(f"      Updated recommendation: {rec_data['title'][:50]}...")
                else:
                    # Create new recommendation
                    recommendation = Recommendation(
                        question_id=question.id,
                        applies_if_score_below=rec_data.get(
                            "applies_if_score_below", 3
                        ),
                        title=rec_data["title"],
                        description=rec_data["description"],
                        improvement_tips=rec_data.get("improvement_tips"),
                        iso_reference=rec_data.get("iso_ref"),
                        nist_reference=rec_data.get("nist_ref"),
                        cis_reference=rec_data.get("cis_ref"),
                        nis2_reference=rec_data.get("nis2_ref"),
                        priority=rec_data.get("priority", "medium"),
                    )
                    db.add(recommendation)
                    print(f"      Created recommendation: {rec_data['title'][:50]}...")

        db.commit()
        print(f"\n✅ Successfully seeded database from {len(json_files)} JSON files!")

        # Print summary
        area_count = db.query(Area).count()
        question_count = db.query(Question).count()
        rec_count = db.query(Recommendation).count()
        print(f"\nSummary:")
        print(f"  Areas: {area_count}")
        print(f"  Questions: {question_count}")
        print(f"  Recommendations: {rec_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_from_json()
