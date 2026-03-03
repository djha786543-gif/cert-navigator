import json
import sqlite3
import argparse
import sys
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_resume_vector(path):
    with open(path, 'r') as f:
        return json.load(f)

def extract_skills(text, skill_list):
    text_lower = text.lower()
    return [skill for skill in skill_list if skill.lower() in text_lower]

def match_title(jd_title, target_titles):
    jd_title_lower = jd_title.lower()
    for title in target_titles:
        if title.lower() in jd_title_lower:
            if "manager" in title.lower() or "senior" in title.lower():
                return 20
            return 25
    if any(kw in jd_title_lower for kw in ["audit", "grc", "risk"]):
        return 15
    return 8

def score_jobs(db_path, resume_vector):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get un-scored jobs
    cursor.execute('''
    SELECT r.id, r.title, r.company, r.location, r.description, r.salary_min, r.salary_max
    FROM jobs_raw r
    LEFT JOIN jobs_scored s ON r.id = s.id
    WHERE s.id IS NULL
    ''')
    
    jobs = cursor.fetchall()
    scored_count = 0
    
    for job in jobs:
        job_id, title, company, location, description, salary_min, salary_max = job
        
        # 1: Title
        t_score = match_title(title, resume_vector['target_titles'])
        
        # 2: Skills
        all_skills = resume_vector['must_have_skills'] + resume_vector['certifications']
        jd_skills = extract_skills(description, all_skills)
        sk_score = (len(jd_skills) / max(1, len(all_skills))) * 22
        
        # 3: AI
        ai_kws = resume_vector['ai_boost_keywords']
        ai_hits = sum(1 for kw in ai_kws if kw.lower() in description.lower())
        ai_score = 18 if ai_hits >= 3 else 10 if ai_hits >= 1 else 0
        if "AAIA" in description.upper() or "AIGP" in description.upper():
            ai_score += 5
            
        # 4: Salary
        comp_score = 7 # Neutral fallback
        target_min = resume_vector['salary_range']['min']
        if salary_min:
            if salary_min >= target_min:
                comp_score = 14
            elif salary_min >= target_min * 0.9:
                comp_score = 10
            elif salary_min >= target_min * 0.8:
                comp_score = 6
            else:
                comp_score = 2
                
        # 5: Location
        loc_score = 2
        loc_str = location.lower()
        if "remote" in loc_str:
            loc_score = 10
        elif any(tgt.lower() in loc_str for tgt in resume_vector['locations']):
            if "hybrid" in description.lower():
                loc_score = 10
            elif "ca" in loc_str or "california" in loc_str:
                loc_score = 8
                
        total_score = t_score + sk_score + ai_score + comp_score + loc_score
        
        # Apply Disqualifiers
        is_disqualified = False
        for dq in resume_vector.get('disqualifiers', []):
            if dq.lower() in description.lower() or dq.lower() in title.lower():
                total_score = 0
                is_disqualified = True
                break
                
        tier = "MUST APPLY" if total_score >= 75 else "HIGH PRIORITY" if total_score >= 60 else "GOOD FIT" if total_score >= 45 else "LOW ROI"
        if is_disqualified:
            tier = "DISQUALIFIED"
        
        remote_type = "Remote" if "remote" in loc_str else "Hybrid" if "hybrid" in description.lower() else "Onsite"
        
        cursor.execute('''
        INSERT INTO jobs_scored (id, title, company, location, score, tier, remote_type, applied, outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, '')
        ''', (job_id, title, company, location, total_score, tier, remote_type))
        scored_count += 1
        
    conn.commit()
    conn.close()
    return scored_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", type=str, default="resume_vector.json")
    parser.add_argument("--db", type=str, default="db/jobs.sqlite")
    args = parser.parse_args()
    
    try:
        resume_vector = load_resume_vector(args.resume)
        count = score_jobs(args.db, resume_vector)
        logger.info(f"Scored {count} new jobs.")
    except Exception as e:
        logger.error(f"Error scoring jobs: {e}")
