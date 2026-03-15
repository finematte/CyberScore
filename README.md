# CyberScore - Information Security Maturity Assessment Tool

A comprehensive web application for assessing organizational information security maturity based on international standards (ISO/IEC 27001, NIST Cybersecurity Framework, and CIS Controls).

## 🎯 Overview

CyberScore helps organizations evaluate their cybersecurity posture through a structured assessment covering 5 key security areas with 25 questions total. The tool provides automated scoring, visual analytics, and actionable recommendations mapped to international standards.

## 🏗️ Architecture

- **Backend**: FastAPI (Python) with SQLite database
- **Frontend**: Streamlit web application
- **Database**: SQLite with SQLAlchemy ORM
- **Visualization**: Plotly charts (radar and bar charts)
- **API**: RESTful API with comprehensive endpoints

## 📊 Features

### Assessment Features
- **5 Security Areas**: Organization & Policy, People & Training, Technology & Infrastructure, Access Control, Incident Response & Continuity
- **25 Questions**: Comprehensive coverage of security practices
- **0-5 Scoring Scale**: Detailed maturity assessment
- **Weighted Scoring**: Industry-standard weighting for questions and areas

### Results & Analytics
- **Overall Score**: Percentage-based maturity score
- **Maturity Levels**: Low (<40%), Medium (40-70%), High (>70%)
- **Visual Charts**: Radar chart and bar chart visualizations
- **Area Breakdown**: Detailed scores for each security area
- **Recommendations**: Actionable improvement suggestions

### Standards Integration
- **ISO/IEC 27001**: Information Security Management Systems
- **NIST Cybersecurity Framework**: Cybersecurity risk management
- **CIS Controls**: Critical Security Controls

## ☁️ Deploy to Streamlit Community Cloud

1. **Set main file**: In the Cloud app settings, set the main file to **`app_with_auth.py`** (not `start_improved.py`). The app runs the API in-process and does not need a separate backend process.

2. **Python version**: Add a `runtime.txt` in the repo root with e.g. `python-3.11.9` so Cloud does not use Python 3.14.

3. **Secrets** (required for production): In the app dashboard go to **Settings → Secrets** and add your configuration. Use either format:

   **Option A – Direct database URL**
   ```toml
   [database]
   url = "mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE"

   [secrets]
   secret_key = "your-secret-key-at-least-32-characters-long"
   ```

   **Option B – MySQL in Streamlit connections format** ([docs](https://docs.streamlit.io/develop/tutorials/databases/mysql))
   ```toml
   [connections.mysql]
   host = "your-mysql-host"
   port = 3306
   database = "cyberscore"
   username = "your-user"
   password = "your-password"

   [secrets]
   secret_key = "your-secret-key-at-least-32-characters-long"
   ```

   For a quick demo you can use SQLite (data will not persist across restarts):
   ```toml
   [database]
   url = "sqlite:///./cyberscore.db"
   [secrets]
   secret_key = "cyberscore-secret-key-change-in-production"
   ```

4. **Local secrets**: Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in values. Do not commit `secrets.toml` (it is in `.gitignore`).

5. **New database**: For a fresh MySQL (or other) database, tables are created automatically. You still need to load areas, questions, and recommendations once (e.g. run `backend/seed_data.py` or your migration against the production DB, or use a DB that was already seeded).

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone or download the project**
   ```bash
   cd SecureMeter
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python backend/seed_data.py
   ```

4. **Start the backend server**
   ```bash
   python run_backend.py
   ```
   The API will be available at `http://localhost:8000`

5. **Start the frontend application**
   ```bash
   streamlit run app.py
   ```
   The web application will be available at `http://localhost:8501`

## 📋 Usage

### Taking an Assessment

1. **Navigate to the application** at `http://localhost:8501`
2. **Click "Start Assessment"** from the home page
3. **Complete the questionnaire** by answering questions in each security area
4. **Save progress** as you go or complete all at once
5. **View results** with detailed analysis and recommendations

### Understanding Results

- **Overall Score**: Your organization's security maturity percentage
- **Maturity Level**: Low, Medium, or High classification
- **Area Scores**: Individual scores for each security area
- **Recommendations**: Prioritized improvement suggestions with standard references

### Exporting Results

- **JSON Export**: Complete results data for further analysis
- **CSV Export**: Area scores in spreadsheet format

## 🗄️ Database Schema

The application uses SQLite with the following main tables:

- **users**: User accounts and roles
- **areas**: Security assessment areas
- **questions**: Assessment questions
- **assessments**: Assessment sessions
- **answers**: User responses
- **area_scores**: Calculated area scores
- **recommendations**: Improvement suggestions
- **assessment_recommendations**: Generated recommendations

## 🔌 API Endpoints

### Core Endpoints
- `GET /areas` - Get all security areas
- `GET /questions` - Get all questions
- `POST /assessments` - Create new assessment
- `POST /answers/bulk` - Submit answers
- `POST /score` - Calculate assessment score
- `GET /results/{id}` - Get assessment results

### Documentation
API documentation is available at `http://localhost:8000/docs` when the backend is running.

## 📊 Sample Data

The application includes sample data with:
- **5 Security Areas** with descriptions and weights
- **25 Questions** (5 per area) with detailed descriptions
- **Recommendations** mapped to questions and standards
- **Default Users** (admin and test user)

## 🎨 User Interface

### Pages
- **Home**: Overview and navigation
- **Take Assessment**: Interactive questionnaire
- **View Results**: Analytics and recommendations
- **About**: Information about the tool and standards

### Features
- **Responsive Design**: Works on desktop and mobile
- **Progress Tracking**: Visual progress indicators
- **Interactive Charts**: Hover and zoom capabilities
- **Export Functions**: Download results in multiple formats

## 🔧 Configuration

### Environment Variables
- `API_BASE_URL`: Backend API URL (default: http://localhost:8000)
- Database: SQLite file (`cyberscore.db`)

### Customization
- **Questions**: Modify `backend/seed_data.py` to add/update questions
- **Weights**: Adjust question and area weights in the database
- **Recommendations**: Update recommendation text and references
- **Styling**: Modify CSS in `app.py` for custom appearance

## 📈 Scoring Algorithm

### Question Scoring
- Each question scored 0-5 (0 = not implemented, 5 = fully implemented)
- Questions weighted within their area based on importance

### Area Scoring
- Weighted average of questions within each area
- Areas weighted based on overall security importance
- Converted to percentage (0-100%)

### Overall Scoring
- Weighted average of all area scores
- Maturity level determined by overall percentage

## 🛠️ Development

### Project Structure
```
SecureMeter/
├── backend/
│   ├── __init__.py
│   ├── api.py              # FastAPI endpoints
│   ├── database.py         # Database models
│   ├── models.py          # Pydantic models
│   ├── scoring.py         # Scoring logic
│   └── seed_data.py       # Sample data
├── app.py                 # Streamlit frontend
├── run_backend.py         # Backend server script
├── requirements.txt       # Python dependencies
├── database_schema.sql   # Database schema
└── README.md             # This file
```

### Adding New Questions
1. Edit `backend/seed_data.py`
2. Add questions to appropriate area
3. Include recommendations for low scores
4. Run seed script to update database

### Modifying Scoring
1. Update weights in `backend/seed_data.py`
2. Modify scoring logic in `backend/scoring.py`
3. Test with sample assessments

## 📚 Standards References

### ISO/IEC 27001:2013
- Information Security Management Systems
- Risk management and continuous improvement
- Comprehensive security framework

### NIST Cybersecurity Framework
- Framework for Improving Critical Infrastructure Cybersecurity
- Five core functions: Identify, Protect, Detect, Respond, Recover
- Risk-based approach to cybersecurity

### CIS Controls
- Critical Security Controls
- Prioritized security actions
- Defense-in-depth best practices

## 🤝 Contributing

This is an academic project developed for a master's thesis. For questions or suggestions, please refer to the project documentation.

## 📄 License

Academic Use License - Developed for educational and research purposes.

## 🔍 Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check if port 8000 is available
   - Verify Python dependencies are installed
   - Check database file permissions

2. **Frontend connection errors**
   - Ensure backend is running on port 8000
   - Check API_BASE_URL configuration
   - Verify network connectivity

3. **Database errors**
   - Run `python backend/seed_data.py` to initialize
   - Check SQLite file permissions
   - Verify database schema

4. **Assessment not saving**
   - Check backend API status
   - Verify assessment ID in session
   - Check database connectivity

### Support
For technical issues, check the API documentation at `http://localhost:8000/docs` or review the application logs.

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Author**: Master's Thesis Project  
**Purpose**: Information Security Maturity Assessment
