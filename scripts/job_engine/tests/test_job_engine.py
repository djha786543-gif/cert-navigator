import pytest
import sqlite3
import os
from fetcher import store_raw_jobs
from scorer import load_resume_vector, extract_skills, match_title, score_jobs
from init_db import init_db

DB_TEST_PATH = "tests/test_jobs.sqlite"
MOCK_RESUME = {
  "target_titles": ["IT Audit Manager"],
  "must_have_skills": ["SOX", "ITGC"],
  "ai_boost_keywords": ["AI governance"],
  "salary_range": {"min": 100000, "max": 150000},
  "locations": ["remote"],
  "experience_years": 10,
  "certifications": ["CISA"],
  "disqualifiers": ["junior"]
}


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_TEST_PATH):
        os.remove(DB_TEST_PATH)
    init_db(DB_TEST_PATH)
    yield
    if os.path.exists(DB_TEST_PATH):
        os.remove(DB_TEST_PATH)

def test_store_raw_jobs():
    mock_jobs = [
        {
            "id": "1",
            "title": "IT Audit Manager",
            "company": {"display_name": "Test Co"},
            "location": {"display_name": "Remote"},
            "description": "Needs SOX",
            "redirect_url": "",
            "salary_min": 100000,
            "salary_max": 100000,
            "created": "today"
        }
    ]
    count = store_raw_jobs(DB_TEST_PATH, mock_jobs, 'test_source')
    assert count == 1
    
    conn = sqlite3.connect(DB_TEST_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs_raw")
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_skill_extraction():
    skills = extract_skills("We need SOX and ITGC.", ["SOX", "ITGC", "AWS"])
    assert "SOX" in skills
    assert "ITGC" in skills
    assert "AWS" not in skills

def test_title_matching():
    assert match_title("Senior IT Audit Manager", ["IT Audit Manager"]) == 20 # Contains manager
    assert match_title("IT Audit Lead", ["IT Audit Manager"]) == 15 # No match but contains 'audit'
    assert match_title("Junior IT Auditor", ["IT Audit Manager"]) == 15

def test_job_scoring():
    mock_jobs = [
         {
             "id": "perfect_match",
             "title": "IT Audit Manager",
             "company": {"display_name": "Test Co"},
             "location": {"display_name": "Remote"},
             "description": "Extensive SOX, ITGC. AI governance is a plus. CISA required.",
             "redirect_url": "http",
             "salary_min": 140000,
             "salary_max": 160000,
             "created": "today"
         },
         {
             "id": "junior_fail",
             "title": "Junior risk analyst",
             "company": {"display_name": "Bank"},
             "location": {"display_name": "New York"},
             "description": "entry level",
             "redirect_url": "http",
             "salary_min": 60000,
             "salary_max": 70000,
             "created": "today"
         }
    ]
    store_raw_jobs(DB_TEST_PATH, mock_jobs, 'test')
    
    # Write mock vector
    import json
    with open('tests/mock_vector.json', 'w') as f:
        json.dump(MOCK_RESUME, f)
        
    scored = score_jobs(DB_TEST_PATH, MOCK_RESUME)
    assert scored == 2
    
    conn = sqlite3.connect(DB_TEST_PATH)
    cursor = conn.cursor()
    
    # Check perfect match
    cursor.execute("SELECT score, tier FROM jobs_scored WHERE id='perfect_match'")
    pm_score, pm_tier = cursor.fetchone()
    assert pm_score >= 70
    assert pm_tier == "MUST APPLY"
    
    # Check disqualified
    cursor.execute("SELECT score, tier FROM jobs_scored WHERE id='junior_fail'")
    jf_score, jf_tier = cursor.fetchone()
    assert jf_score == 0
    assert jf_tier == "DISQUALIFIED"
    
    conn.close()
    os.remove('tests/mock_vector.json')
