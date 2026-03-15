-- CyberScore Database Schema
-- Information Security Maturity Assessment Tool

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Security areas (e.g., Organization & Policy, People, Technology, etc.)
CREATE TABLE areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    weight DECIMAL(3,2) DEFAULT 1.00, -- Area weight for scoring
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions within each area
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    description TEXT,
    weight DECIMAL(3,2) DEFAULT 1.00, -- Question weight within area
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE
);

-- Assessment sessions
CREATE TABLE assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200),
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed')),
    total_score DECIMAL(5,2),
    maturity_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User answers to questions
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    score INTEGER CHECK (score >= 0 AND score <= 5), -- 0-5 scale
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    UNIQUE(assessment_id, question_id)
);

-- Area scores for each assessment
CREATE TABLE area_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    weighted_score DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE,
    UNIQUE(assessment_id, area_id)
);

-- Recommendations based on low scores
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    threshold_score INTEGER DEFAULT 3, -- Recommend if score < threshold
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    improvement_tips TEXT,
    iso_reference VARCHAR(100),
    nist_reference VARCHAR(100),
    cis_reference VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Assessment recommendations (generated based on answers)
CREATE TABLE assessment_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    recommendation_id INTEGER NOT NULL,
    question_score INTEGER NOT NULL,
    is_applicable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE CASCADE
);

-- Indexes for better performance
CREATE INDEX idx_questions_area_id ON questions(area_id);
CREATE INDEX idx_answers_assessment_id ON answers(assessment_id);
CREATE INDEX idx_answers_question_id ON answers(question_id);
CREATE INDEX idx_assessments_user_id ON assessments(user_id);
CREATE INDEX idx_area_scores_assessment_id ON area_scores(assessment_id);
CREATE INDEX idx_recommendations_question_id ON recommendations(question_id);
CREATE INDEX idx_assessment_recommendations_assessment_id ON assessment_recommendations(assessment_id);
