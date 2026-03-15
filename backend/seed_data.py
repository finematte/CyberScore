"""
Seed data for CyberScore database
"""
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import backend modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from sqlalchemy.orm import Session
from backend.database import SessionLocal, Area, Question, Recommendation, User
from passlib.context import CryptContext
from datetime import datetime

# Password hashing - using a simple approach to avoid bcrypt issues
def hash_password(password: str) -> str:
    # For demo purposes, we'll use a simple hash
    # In production, you'd want proper password hashing
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def seed_database():
    """Populate database with initial data"""
    # First, create the tables
    from backend.database import create_tables
    create_tables()
    
    db = SessionLocal()
    
    try:
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Database already has data. Skipping seed.")
            db.close()
            return
        
        # Create default admin user
        admin_user = User(
            username="admin",
            email="admin@cyberscore.com",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin_user)
        
        # Create test user
        test_user = User(
            username="testuser",
            email="test@cyberscore.com",
            password_hash=hash_password("test123"),
            role="user"
        )
        db.add(test_user)
        
        # Security Areas
        areas_data = [
            {
                "name": "Organization & Policy",
                "description": "Governance, policies, and organizational structure for information security",
                "weight": 1.20,
                "order_index": 1
            },
            {
                "name": "People & Training",
                "description": "Human resources security, awareness, and training programs",
                "weight": 1.00,
                "order_index": 2
            },
            {
                "name": "Technology & Infrastructure",
                "description": "Technical controls, network security, and system protection",
                "weight": 1.30,
                "order_index": 3
            },
            {
                "name": "Access Control",
                "description": "Identity management, authentication, and authorization controls",
                "weight": 1.10,
                "order_index": 4
            },
            {
                "name": "Incident Response & Continuity",
                "description": "Incident handling, business continuity, and disaster recovery",
                "weight": 1.00,
                "order_index": 5
            }
        ]
        
        areas = []
        for area_data in areas_data:
            area = Area(**area_data)
            db.add(area)
            db.flush()  # Get the ID
            areas.append(area)
        
        # Questions for each area
        questions_data = [
            # Organization & Policy (Area 1)
            [
                {
                    "question_text": "Does your organization have a formal information security policy?",
                    "description": "A documented policy that defines the organization's approach to information security",
                    "weight": 1.20,
                    "order_index": 1
                },
                {
                    "question_text": "Is there a designated Chief Information Security Officer (CISO) or equivalent?",
                    "description": "A senior executive responsible for information security governance",
                    "weight": 1.00,
                    "order_index": 2
                },
                {
                    "question_text": "Are information security roles and responsibilities clearly defined?",
                    "description": "Clear job descriptions and accountability for security functions",
                    "weight": 1.10,
                    "order_index": 3
                },
                {
                    "question_text": "Is there a formal risk management process in place?",
                    "description": "Systematic identification, assessment, and treatment of information security risks",
                    "weight": 1.30,
                    "order_index": 4
                },
                {
                    "question_text": "Are security policies regularly reviewed and updated?",
                    "description": "Annual or periodic review of security policies and procedures",
                    "weight": 1.00,
                    "order_index": 5
                }
            ],
            # People & Training (Area 2)
            [
                {
                    "question_text": "Do all employees receive information security awareness training?",
                    "description": "Regular training on security best practices and organizational policies",
                    "weight": 1.20,
                    "order_index": 1
                },
                {
                    "question_text": "Are background checks performed for new employees?",
                    "description": "Verification of credentials and criminal history for sensitive positions",
                    "weight": 1.00,
                    "order_index": 2
                },
                {
                    "question_text": "Is there a formal process for handling employee departures?",
                    "description": "Systematic deprovisioning of access and return of company assets",
                    "weight": 1.10,
                    "order_index": 3
                },
                {
                    "question_text": "Are security incidents reported and tracked?",
                    "description": "Mechanism for employees to report security concerns or incidents",
                    "weight": 1.30,
                    "order_index": 4
                },
                {
                    "question_text": "Is there ongoing security education for IT staff?",
                    "description": "Continuous professional development for technical security personnel",
                    "weight": 1.00,
                    "order_index": 5
                }
            ],
            # Technology & Infrastructure (Area 3)
            [
                {
                    "question_text": "Are all systems protected by up-to-date antivirus software?",
                    "description": "Current endpoint protection on all workstations and servers",
                    "weight": 1.20,
                    "order_index": 1
                },
                {
                    "question_text": "Is network traffic monitored and logged?",
                    "description": "Continuous monitoring of network communications and access",
                    "weight": 1.30,
                    "order_index": 2
                },
                {
                    "question_text": "Are security patches applied regularly?",
                    "description": "Systematic patching of operating systems and applications",
                    "weight": 1.40,
                    "order_index": 3
                },
                {
                    "question_text": "Is data encrypted in transit and at rest?",
                    "description": "Protection of sensitive data through encryption mechanisms",
                    "weight": 1.20,
                    "order_index": 4
                },
                {
                    "question_text": "Are regular security assessments performed?",
                    "description": "Periodic vulnerability scans and penetration testing",
                    "weight": 1.10,
                    "order_index": 5
                }
            ],
            # Access Control (Area 4)
            [
                {
                    "question_text": "Is multi-factor authentication (MFA) implemented?",
                    "description": "Additional authentication factors beyond passwords",
                    "weight": 1.30,
                    "order_index": 1
                },
                {
                    "question_text": "Are user access rights reviewed regularly?",
                    "description": "Periodic review and validation of user permissions",
                    "weight": 1.20,
                    "order_index": 2
                },
                {
                    "question_text": "Is there a principle of least privilege in place?",
                    "description": "Users granted minimum necessary access to perform their duties",
                    "weight": 1.10,
                    "order_index": 3
                },
                {
                    "question_text": "Are privileged accounts managed separately?",
                    "description": "Special handling and monitoring of administrative accounts",
                    "weight": 1.40,
                    "order_index": 4
                },
                {
                    "question_text": "Is there automated provisioning and deprovisioning?",
                    "description": "Automated systems for granting and revoking access",
                    "weight": 1.00,
                    "order_index": 5
                }
            ],
            # Incident Response & Continuity (Area 5)
            [
                {
                    "question_text": "Is there a formal incident response plan?",
                    "description": "Documented procedures for handling security incidents",
                    "weight": 1.30,
                    "order_index": 1
                },
                {
                    "question_text": "Are regular backups performed and tested?",
                    "description": "Systematic backup procedures with restoration testing",
                    "weight": 1.20,
                    "order_index": 2
                },
                {
                    "question_text": "Is there a business continuity plan?",
                    "description": "Procedures for maintaining operations during disruptions",
                    "weight": 1.10,
                    "order_index": 3
                },
                {
                    "question_text": "Are incident response team roles defined?",
                    "description": "Clear responsibilities for incident handling personnel",
                    "weight": 1.00,
                    "order_index": 4
                },
                {
                    "question_text": "Is there regular testing of incident response procedures?",
                    "description": "Periodic drills and exercises to validate response capabilities",
                    "weight": 1.20,
                    "order_index": 5
                }
            ]
        ]
        
        questions = []
        for area_idx, area_questions in enumerate(questions_data):
            area = areas[area_idx]
            for question_data in area_questions:
                question_data["area_id"] = area.id
                question = Question(**question_data)
                db.add(question)
                db.flush()  # Get the ID
                questions.append(question)
        
        # Recommendations for questions with low scores
        recommendations_data = [
            # Organization & Policy recommendations
            [
                {
                    "threshold_score": 2,
                    "title": "Develop Information Security Policy",
                    "description": "Create a comprehensive information security policy that aligns with business objectives and regulatory requirements.",
                    "improvement_tips": "Start with ISO 27001 framework, involve stakeholders from all departments, ensure legal review, and establish approval process.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 5.2",
                    "nist_reference": "NIST CSF - PR.IP-1",
                    "cis_reference": "CIS Control 1 - Inventory and Control of Enterprise Assets",
                    "priority": "high"
                },
                {
                    "threshold_score": 2,
                    "title": "Appoint Information Security Officer",
                    "description": "Designate a senior executive responsible for information security governance and risk management.",
                    "improvement_tips": "Consider internal promotion or external hiring, ensure executive support, define clear reporting structure, and provide necessary resources.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 5.3",
                    "nist_reference": "NIST CSF - ID.GV-1",
                    "cis_reference": "CIS Control 1 - Inventory and Control of Enterprise Assets",
                    "priority": "high"
                }
            ],
            # People & Training recommendations
            [
                {
                    "threshold_score": 2,
                    "title": "Implement Security Awareness Training",
                    "description": "Develop and deliver regular information security awareness training for all employees.",
                    "improvement_tips": "Use interactive content, include real-world examples, conduct phishing simulations, and track completion rates.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 7.2.2",
                    "nist_reference": "NIST CSF - PR.AT-1",
                    "cis_reference": "CIS Control 14 - Security Awareness and Skills Training",
                    "priority": "medium"
                },
                {
                    "threshold_score": 2,
                    "title": "Establish Background Check Process",
                    "description": "Implement background verification procedures for new hires, especially for sensitive positions.",
                    "improvement_tips": "Define roles requiring background checks, establish vendor relationships, ensure legal compliance, and document procedures.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 7.1.2",
                    "nist_reference": "NIST CSF - PR.AT-2",
                    "cis_reference": "CIS Control 14 - Security Awareness and Skills Training",
                    "priority": "medium"
                }
            ],
            # Technology & Infrastructure recommendations
            [
                {
                    "threshold_score": 2,
                    "title": "Deploy Endpoint Protection",
                    "description": "Implement comprehensive endpoint protection including antivirus, anti-malware, and EDR solutions.",
                    "improvement_tips": "Choose enterprise-grade solutions, ensure centralized management, configure real-time protection, and establish update procedures.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 8.1",
                    "nist_reference": "NIST CSF - PR.DS-1",
                    "cis_reference": "CIS Control 8 - Malware Defenses",
                    "priority": "high"
                },
                {
                    "threshold_score": 2,
                    "title": "Implement Network Monitoring",
                    "description": "Deploy network monitoring and logging solutions to detect and respond to security threats.",
                    "improvement_tips": "Consider SIEM solutions, establish baseline network behavior, configure alerting, and ensure log retention policies.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 12.4.1",
                    "nist_reference": "NIST CSF - DE.CM-1",
                    "cis_reference": "CIS Control 6 - Maintenance, Monitoring, and Analysis of Audit Logs",
                    "priority": "high"
                }
            ],
            # Access Control recommendations
            [
                {
                    "threshold_score": 2,
                    "title": "Enable Multi-Factor Authentication",
                    "description": "Implement multi-factor authentication for all user accounts, especially privileged accounts.",
                    "improvement_tips": "Start with high-risk accounts, choose appropriate MFA methods, ensure user training, and monitor adoption rates.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 9.2.1",
                    "nist_reference": "NIST CSF - PR.AC-1",
                    "cis_reference": "CIS Control 6 - Maintenance, Monitoring, and Analysis of Audit Logs",
                    "priority": "high"
                },
                {
                    "threshold_score": 2,
                    "title": "Implement Access Review Process",
                    "description": "Establish regular review and validation of user access rights and permissions.",
                    "improvement_tips": "Define review frequency, involve business owners, automate where possible, and document exceptions.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 9.2.5",
                    "nist_reference": "NIST CSF - PR.AC-4",
                    "cis_reference": "CIS Control 5 - Account Management",
                    "priority": "medium"
                }
            ],
            # Incident Response & Continuity recommendations
            [
                {
                    "threshold_score": 2,
                    "title": "Develop Incident Response Plan",
                    "description": "Create comprehensive incident response procedures and establish response team.",
                    "improvement_tips": "Define incident categories, establish communication procedures, create playbooks, and conduct regular training.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 16.1",
                    "nist_reference": "NIST CSF - RS.RP-1",
                    "cis_reference": "CIS Control 19 - Incident Response and Management",
                    "priority": "high"
                },
                {
                    "threshold_score": 2,
                    "title": "Implement Backup Strategy",
                    "description": "Establish comprehensive backup procedures with regular testing and validation.",
                    "improvement_tips": "Define RTO/RPO requirements, implement 3-2-1 backup rule, test restoration procedures, and ensure offsite storage.",
                    "iso_reference": "ISO/IEC 27001:2013 - Clause 12.3.1",
                    "nist_reference": "NIST CSF - PR.DS-4",
                    "cis_reference": "CIS Control 11 - Data Recovery",
                    "priority": "high"
                }
            ]
        ]
        
        # Create recommendations
        for area_idx, area_recommendations in enumerate(recommendations_data):
            area_start_idx = area_idx * 5  # 5 questions per area
            for rec_idx, rec_data in enumerate(area_recommendations):
                question_idx = area_start_idx + rec_idx
                if question_idx < len(questions):
                    rec_data["question_id"] = questions[question_idx].id
                    recommendation = Recommendation(**rec_data)
                    db.add(recommendation)
        
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
