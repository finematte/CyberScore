"""
CyberScore - Information Security Maturity Assessment Tool
Streamlit Frontend Application (Batched / Form-based Input Version)
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime
import time
import textwrap

# Configuration
API_BASE_URL = "http://localhost:8000"
st.set_page_config(
    page_title="CyberScore",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .score-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .recommendation-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
        color: #212529 !important;
    }
    .recommendation-card h4 {
        color: #212529 !important;
    }
    .recommendation-card p {
        color: #212529 !important;
    }
    .recommendation-card ul {
        color: #212529 !important;
    }
    .recommendation-card li {
        color: #212529 !important;
    }
    .high-priority {
        border-left-color: #dc3545 !important;
        background-color: #f8d7da !important;
        color: #721c24 !important;
    }
    .high-priority h4 {
        color: #721c24 !important;
    }
    .high-priority p {
        color: #721c24 !important;
    }
    .high-priority ul {
        color: #721c24 !important;
    }
    .high-priority li {
        color: #721c24 !important;
    }
    .medium-priority {
        border-left-color: #ffc107 !important;
        background-color: #fff3cd !important;
        color: #856404 !important;
    }
    .medium-priority h4 {
        color: #856404 !important;
    }
    .medium-priority p {
        color: #856404 !important;
    }
    .medium-priority ul {
        color: #856404 !important;
    }
    .medium-priority li {
        color: #856404 !important;
    }
    .low-priority {
        border-left-color: #28a745 !important;
        background-color: #d4edda !important;
        color: #155724 !important;
    }
    .low-priority h4 {
        color: #155724 !important;
    }
    .low-priority p {
        color: #155724 !important;
    }
    .low-priority ul {
        color: #155724 !important;
    }
    .low-priority li {
        color: #155724 !important;
    }
    .muted {
        color: #6c757d;
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def make_api_request(endpoint, method="GET", data=None):
    """Make API request with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=20)
        else:
            raise ValueError("Unsupported HTTP method")

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the API server. Please make sure the backend is running."
        )
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


@st.cache_data(show_spinner=False)
def fetch_assessment_with_questions(assessment_id: int):
    """Cache assessment + areas/questions to avoid refetch on every rerun"""
    return make_api_request(f"/assessments/{assessment_id}/questions")


def create_radar_chart(area_scores):
    """Create detailed radar chart for area scores"""
    if not area_scores:
        return None

    areas = []
    scores = []

    for score in area_scores:
        if isinstance(score, dict):
            areas.append(score.get("area_name", "Unknown Area"))
            scores.append(float(score.get("score", 0)))
        else:
            areas.append(getattr(score.area, "name", "Unknown Area"))
            scores.append(float(getattr(score, "score", 0)))

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=scores,
            theta=areas,
            fill="toself",
            name="Current Score",
            line_color="rgb(31, 119, 180)",
            fillcolor="rgba(31, 119, 180, 0.2)",
            line_width=3,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[70] * len(areas),
            theta=areas,
            fill="none",
            name="Target (70%)",
            line_color="rgb(255, 0, 0)",
            line_dash="dash",
            line_width=2,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[40] * len(areas),
            theta=areas,
            fill="none",
            name="Minimum (40%)",
            line_color="rgb(255, 165, 0)",
            line_dash="dot",
            line_width=2,
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickmode="linear",
                tick0=0,
                dtick=20,
                tickfont=dict(size=10),
            ),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        showlegend=True,
        title=dict(
            text="Security Maturity Assessment<br><sub>Detailed Analysis by Security Area</sub>",
            font=dict(size=16),
        ),
        font=dict(size=12),
        height=500,
        margin=dict(t=80, b=50, l=50, r=50),
    )

    return fig


def create_bar_chart(area_scores):
    """Create detailed bar chart for area scores"""
    if not area_scores:
        return None

    data = []
    for score in area_scores:
        if isinstance(score, dict):
            data.append(
                {
                    "area_name": score.get("area_name", "Unknown Area"),
                    "score": float(score.get("score", 0)),
                    "weighted_score": float(score.get("weighted_score", 0)),
                }
            )
        else:
            data.append(
                {
                    "area_name": getattr(score.area, "name", "Unknown Area"),
                    "score": float(getattr(score, "score", 0)),
                    "weighted_score": float(getattr(score, "weighted_score", 0)),
                }
            )

    df = pd.DataFrame(data).sort_values("score", ascending=True)

    colors = []
    for s in df["score"]:
        if s < 40:
            colors.append("#dc3545")
        elif s < 70:
            colors.append("#ffc107")
        else:
            colors.append("#28a745")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["area_name"],
            x=df["score"],
            orientation="h",
            marker=dict(color=colors),
            text=[f"{s:.1f}%" for s in df["score"]],
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}%<br>Weighted: %{customdata:.1f}%<extra></extra>",
            customdata=df["weighted_score"],
        )
    )

    fig.add_vline(
        x=70,
        line_dash="dash",
        line_color="red",
        annotation_text="Target (70%)",
        annotation_position="top",
    )
    fig.add_vline(
        x=40,
        line_dash="dot",
        line_color="orange",
        annotation_text="Minimum (40%)",
        annotation_position="top",
    )

    fig.update_layout(
        title=dict(
            text="Security Maturity Scores by Area<br><sub>Comparison with Target and Minimum Thresholds</sub>",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Score (%)", range=[0, 100], tickmode="linear", tick0=0, dtick=20
        ),
        yaxis=dict(title="Security Area"),
        height=500,
        font=dict(size=12),
        margin=dict(t=80, b=50, l=150, r=50),
        showlegend=False,
    )

    return fig


def main():
    st.markdown('<h1 class="main-header">🛡️ CyberScore</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">Information Security Maturity Assessment Tool</p>',
        unsafe_allow_html=True,
    )

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Home"
    if "assessment_id" not in st.session_state:
        st.session_state.assessment_id = None
    if "current_area" not in st.session_state:
        st.session_state.current_area = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "completed_assessment_id" not in st.session_state:
        st.session_state.completed_assessment_id = None

    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Home", "Take Assessment", "View Results", "About"],
        index=["Home", "Take Assessment", "View Results", "About"].index(
            st.session_state.current_page
        ),
    )

    if page != st.session_state.current_page:
        st.session_state.current_page = page
        st.rerun()

    if st.session_state.current_page == "Home":
        show_home_page()
    elif st.session_state.current_page == "Take Assessment":
        show_assessment_page()
    elif st.session_state.current_page == "View Results":
        show_results_page()
    elif st.session_state.current_page == "About":
        show_about_page()


def show_home_page():
    st.markdown(
        """
    ## Welcome to CyberScore
    
    CyberScore is a comprehensive information security maturity assessment tool based on:
    - **ISO/IEC 27001**
    - **NIST Cybersecurity Framework**
    - **CIS Controls**
    
    ### How It Works
    1. **Assessment**: Answer questions across 5 security areas
    2. **Scoring**: Weighted scoring algorithm
    3. **Analysis**: Results, charts and recommendations
    4. **Improvement**: Actionable guidance mapped to standards
    """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🎯 Quick Start")
        if st.button("Start Assessment", type="primary", use_container_width=True):
            st.session_state.current_page = "Take Assessment"
            st.rerun()

    with col2:
        st.markdown("### 📊 View Results")
        if st.button("View Results", use_container_width=True):
            st.session_state.current_page = "View Results"
            st.rerun()

    with col3:
        st.markdown("### ℹ️ Learn More")
        if st.button("About CyberScore", use_container_width=True):
            st.session_state.current_page = "About"
            st.rerun()


def show_assessment_page():
    st.markdown(
        '<h2 class="sub-header">📋 Security Maturity Assessment</h2>',
        unsafe_allow_html=True,
    )

    # Create assessment once
    if st.session_state.assessment_id is None:
        st.info("Starting a new assessment...")
        result = make_api_request(
            "/assessments",
            "POST",
            {
                "user_id": 1,
                "title": f"Assessment - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            },
        )
        if result:
            st.session_state.assessment_id = result["id"]
            st.success(f"Assessment created! ID: {st.session_state.assessment_id}")
        else:
            st.error("Failed to create assessment")
            return

    # Fetch once & cache
    assessment_data = fetch_assessment_with_questions(st.session_state.assessment_id)
    if not assessment_data:
        st.error("Failed to load assessment data")
        return
    areas = assessment_data["areas"]

    # Toggle to show minimal reruns info
    st.caption(
        "🔒 Tryb **batched/form**: zmiany w suwakach **nie przeładowują** aplikacji. "
        "Zapisz obszar przyciskiem, a do bazy zapisz całość dopiero na końcu."
    )

    # Progress across all areas (based on saved local answers)
    total_questions = sum(len(a["questions"]) for a in areas)
    answered_total = len(st.session_state.answers)
    st.progress(answered_total / total_questions if total_questions else 0.0)
    st.write(
        f"Postęp (lokalny): {answered_total}/{total_questions} odpowiedzi zapisanych w sesji"
    )

    # Current area
    idx = st.session_state.current_area
    idx = max(0, min(idx, len(areas) - 1))
    area = areas[idx]

    st.markdown(f"### {area['name']}")
    if area.get("description"):
        st.markdown(f"*{area['description']}*")

    # FORM: all question inputs in this area
    with st.form(f"area_form_{area['id']}", clear_on_submit=False):
        st.caption(
            "Zmiany w suwakach nie zapisują się automatycznie – użyj jednego z przycisków poniżej."
        )

        for i, q in enumerate(area["questions"]):
            qid = q["id"]
            # default from local session answers or 0
            default_val = int(st.session_state.answers.get(qid, {}).get("score", 0))
            st.markdown(f"**{q['question_text']}**")
            if q.get("description"):
                st.markdown(
                    f"<span class='muted'>{q['description']}</span>",
                    unsafe_allow_html=True,
                )
            st.slider(
                "Score (0-5):",
                min_value=0,
                max_value=5,
                value=default_val,
                key=f"form_q_{qid}",
                help="0 = Not implemented, 5 = Fully implemented",
            )
            if i < len(area["questions"]) - 1:
                st.markdown("---")

        # Buttons inside the form submit and persist local session answers in one go
        c1, c2, c3, c4 = st.columns(4)
        prev_btn = next_btn = save_area_btn = complete_btn = save_backend_btn = False

        with c1:
            if idx > 0:
                prev_btn = st.form_submit_button("← Poprzedni obszar")
        with c2:
            save_area_btn = st.form_submit_button("💾 Zapisz obszar (lokalnie)")
        with c3:
            save_backend_btn = st.form_submit_button("📥 Zapisz do bazy (bez obliczeń)")
        with c4:
            if idx < len(areas) - 1:
                next_btn = st.form_submit_button("Następny obszar →")
            else:
                complete_btn = st.form_submit_button("✅ Zakończ ocenę")

        any_submit = (
            prev_btn or next_btn or save_area_btn or save_backend_btn or complete_btn
        )

        if any_submit:
            # Persist current form values into local session
            for q in area["questions"]:
                qid = q["id"]
                st.session_state.answers[qid] = {
                    "score": int(st.session_state.get(f"form_q_{qid}", 0))
                }

            # Optionally push to backend without scoring
            if save_backend_btn:
                answers_payload = [
                    {
                        "assessment_id": st.session_state.assessment_id,
                        "question_id": qid,
                        "score": ad["score"],
                    }
                    for qid, ad in st.session_state.answers.items()
                ]
                res = make_api_request(
                    "/answers/bulk",
                    "POST",
                    {
                        "assessment_id": st.session_state.assessment_id,
                        "answers": answers_payload,
                    },
                )
                if res:
                    st.success(
                        f"Zapisano w bazie {len(answers_payload)} odpowiedzi (bez liczenia wyniku)."
                    )

            # Navigation
            if prev_btn and idx > 0:
                st.session_state.current_area = idx - 1
                st.rerun()
            if next_btn and idx < len(areas) - 1:
                st.session_state.current_area = idx + 1
                st.rerun()

            # Complete assessment: push all answers, then score
            if complete_btn:
                answers_payload = [
                    {
                        "assessment_id": st.session_state.assessment_id,
                        "question_id": qid,
                        "score": ad["score"],
                    }
                    for qid, ad in st.session_state.answers.items()
                ]

                save_result = make_api_request(
                    "/answers/bulk",
                    "POST",
                    {
                        "assessment_id": st.session_state.assessment_id,
                        "answers": answers_payload,
                    },
                )
                if save_result:
                    with st.spinner("Liczenie wyniku dojrzałości..."):
                        score_result = make_api_request(
                            "/score",
                            "POST",
                            {"assessment_id": st.session_state.assessment_id},
                        )
                        if score_result:
                            st.session_state.completed_assessment_id = (
                                st.session_state.assessment_id
                            )
                            st.session_state.assessment_id = None
                            st.session_state.answers = {}
                            st.session_state.current_area = 0
                            st.session_state.current_page = "View Results"
                            st.success("🎉 Zakończono ocenę! Przechodzę do wyników...")
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.error("❌ Nie udało się obliczyć wyniku.")
                else:
                    st.error("❌ Nie udało się zapisać odpowiedzi do bazy.")

        # Show local area progress based on saved answers
        area_qids = [q["id"] for q in area["questions"]]
        answered_in_area = sum(
            1 for qid in area_qids if qid in st.session_state.answers
        )
        st.progress(
            answered_in_area / len(area_qids) if area_qids else 0.0,
            text=f"Postęp w obszarze: {answered_in_area}/{len(area_qids)}",
        )


def show_results_page():
    st.markdown(
        '<h2 class="sub-header">📊 Assessment Results</h2>', unsafe_allow_html=True
    )

    assessment_id = st.session_state.get("completed_assessment_id")
    if not assessment_id:
        st.info("Brak zakończonej oceny. Najpierw wypełnij ankietę.")
        return

    results = make_api_request(f"/results/{assessment_id}")
    if not results:
        st.error("Failed to load results")
        return

    assessment = results["assessment"]
    area_scores = results["area_scores"]
    recommendations = results["recommendations"]

    total_score = float(assessment["total_score"])
    maturity_level = assessment["maturity_level"]

    if total_score < 40:
        score_color = "#dc3545"
    elif total_score < 70:
        score_color = "#ffc107"
    else:
        score_color = "#28a745"

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
        <div class="score-card">
            <h3 style="text-align: center; margin-bottom: 1rem;">Overall Security Maturity Score</h3>
            <h1 style="text-align: center; color: {score_color}; font-size: 4rem; margin: 0;">{total_score:.1f}%</h1>
            <h3 style="text-align: center; color: {score_color}; margin-top: 0.5rem;">{maturity_level} Maturity</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<h3 class="sub-header">📈 Detailed Analysis</h3>', unsafe_allow_html=True
    )

    if area_scores:
        # Radar
        radar_fig = create_radar_chart(area_scores)
        if radar_fig:
            st.plotly_chart(radar_fig, use_container_width=True)
        # Bar
        bar_fig = create_bar_chart(area_scores)
        if bar_fig:
            st.plotly_chart(bar_fig, use_container_width=True)

        # Table
        table_data = []
        for score in area_scores:
            if isinstance(score, dict):
                area_name = (
                    score.get("area_name")
                    or score.get("area", {}).get("name")
                    or "Unknown Area"
                )
                raw_score = score.get("score", 0)
                raw_w = score.get("weighted_score", 0)
            else:
                area_name = (
                    getattr(getattr(score, "area", None), "name", None)
                    or "Unknown Area"
                )
                raw_score = getattr(score, "score", 0)
                raw_w = getattr(score, "weighted_score", 0)

            table_data.append(
                {
                    "Security Area": area_name,
                    "Score (%)": round(float(raw_score or 0), 1),
                    "Weighted Score (%)": round(float(raw_w or 0), 1),
                }
            )

        df_scores = pd.DataFrame(table_data)
        st.dataframe(df_scores, use_container_width=True)

    st.markdown(
        '<h3 class="sub-header">💡 Recommendations</h3>', unsafe_allow_html=True
    )
    if recommendations:
        # group by priority
        def prio(rec):
            if hasattr(rec, "recommendation"):
                return getattr(rec.recommendation, "priority", "medium")
            return rec.get("priority", "medium")

        groups = {"high": [], "medium": [], "low": []}
        for rec in recommendations:
            groups.get(prio(rec), []).append(rec)

        for label, css in [
            ("high", "high-priority"),
            ("medium", "medium-priority"),
            ("low", "low-priority"),
        ]:
            if groups[label]:
                st.markdown(f"#### {label.capitalize()} Priority")
                for rec in groups[label]:
                    if hasattr(rec, "recommendation"):
                        rd = rec.recommendation
                        title = getattr(rd, "title", "Unknown")
                        desc = getattr(rd, "description", "")
                        tips = getattr(rd, "improvement_tips", "")
                        iso_ref = getattr(rd, "iso_reference", "")
                        nist_ref = getattr(rd, "nist_reference", "")
                        cis_ref = getattr(rd, "cis_reference", "")
                        qscore = getattr(rec, "question_score", 0)
                    else:
                        title = rec.get("title", "Unknown")
                        desc = rec.get("description", "")
                        tips = rec.get("improvement_tips", "")
                        iso_ref = rec.get("iso_reference", "")
                        nist_ref = rec.get("nist_reference", "")
                        cis_ref = rec.get("cis_reference", "")
                        qscore = rec.get("question_score", 0)

                    html = textwrap.dedent(
                        f"""
                        <div class="recommendation-card {css}">
                        <h4>{title or 'Untitled'}</h4>
                        <p><strong>Description:</strong> {desc or '—'}</p>
                        <p><strong>Question Score:</strong> {qscore}/5</p>
                        {f'<p><strong>Improvement Tips:</strong> {tips}</p>' if tips else ''}
                        <p><strong>References:</strong></p>
                        <ul>
                            {f'<li>ISO: {iso_ref}</li>' if iso_ref else ''}
                            {f'<li>NIST: {nist_ref}</li>' if nist_ref else ''}
                            {f'<li>CIS: {cis_ref}</li>' if cis_ref else ''}
                        </ul>
                        </div>
                        """
                    ).strip()
                    st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("No recommendations available. Great job on your security maturity!")

    st.markdown('<h3 class="sub-header">📤 Export Results</h3>', unsafe_allow_html=True)
    if area_scores:
        export_data = {
            "assessment_id": assessment_id,
            "total_score": total_score,
            "maturity_level": maturity_level,
            "area_scores": [
                {
                    "area_name": (
                        getattr(score.area, "name", "Unknown Area")
                        if hasattr(score, "area")
                        else score.get("area_name", "Unknown Area")
                    ),
                    "score": float(
                        getattr(score, "score", 0)
                        if hasattr(score, "score")
                        else score.get("score", 0)
                    ),
                    "weighted_score": float(
                        getattr(score, "weighted_score", 0)
                        if hasattr(score, "weighted_score")
                        else score.get("weighted_score", 0)
                    ),
                }
                for score in area_scores
            ],
            "recommendations": [
                {
                    "title": (
                        getattr(rec.recommendation, "title", "Unknown")
                        if hasattr(rec, "recommendation")
                        else rec.get("title", "Unknown")
                    ),
                    "description": (
                        getattr(rec.recommendation, "description", "")
                        if hasattr(rec, "recommendation")
                        else rec.get("description", "")
                    ),
                    "priority": (
                        getattr(rec.recommendation, "priority", "medium")
                        if hasattr(rec, "recommendation")
                        else rec.get("priority", "medium")
                    ),
                    "question_score": (
                        getattr(rec, "question_score", 0)
                        if hasattr(rec, "question_score")
                        else rec.get("question_score", 0)
                    ),
                }
                for rec in recommendations
            ],
            "timestamp": datetime.now().isoformat(),
        }
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="Download JSON Results",
            data=json_str,
            file_name=f"cyberscore_results_{assessment_id}.json",
            mime="application/json",
        )

        df_scores = pd.DataFrame(
            [
                {
                    "Security Area": row["area_name"],
                    "Score (%)": row["score"],
                    "Weighted Score (%)": row["weighted_score"],
                }
                for row in export_data["area_scores"]
            ]
        )
        st.download_button(
            label="Download CSV Scores",
            data=df_scores.to_csv(index=False),
            file_name=f"cyberscore_scores_{assessment_id}.csv",
            mime="text/csv",
        )


def show_about_page():
    st.markdown(
        '<h2 class="sub-header">ℹ️ About CyberScore</h2>', unsafe_allow_html=True
    )
    st.markdown(
        """
    CyberScore is an information security maturity assessment tool aligned to ISO/IEC 27001, NIST CSF, and CIS Controls.
    It features 25 questions across 5 areas, weighted scoring, visual analytics, and actionable recommendations.
    """
    )


if __name__ == "__main__":
    main()
