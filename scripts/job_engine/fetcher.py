import json
import sqlite3
import argparse
import sys
import logging
import requests
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_adzuna(app_id, api_key, query, results=50):
    url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        'app_id': app_id,
        'app_key': api_key,
        'results_per_page': results,
        'what': query,
        'content-type': 'application/json'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except Exception as e:
        logger.error(f"Error fetching from Adzuna for query '{query}': {e}")
        return []

def store_raw_jobs(db_path, jobs, source):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    count = 0
    for job in jobs:
        # Generate a unique ID if not present, Adzuna has 'id'
        job_id = str(job.get('id', ''))
        
        # Fallback ID generation if missing
        if not job_id:
            title = job.get('title', '')
            company = job.get('company', {}).get('display_name', '')
            job_id = hashlib.sha256(f"{title}{company}{source}".encode()).hexdigest()
            
        title = job.get('title', '')
        company = job.get('company', {}).get('display_name', '')
        location = job.get('location', {}).get('display_name', '')
        description = job.get('description', '')
        url = job.get('redirect_url', '')
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        posted_date = job.get('created', '')
        raw_data = json.dumps(job)
        
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO jobs_raw (id, title, company, location, description, url, salary_min, salary_max, posted_date, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, title, company, location, description, url, salary_min, salary_max, posted_date, source, raw_data))
            
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            logger.error(f"Error inserting job {job_id}: {e}")
            
    conn.commit()
    conn.close()
    return count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json")
    parser.add_argument("--db", type=str, default="db/jobs.sqlite")
    # Provide dummy default so script can run without failing in Turbo Mode if config is missing keys
    parser.add_argument("--test", action="store_true", help="Run with mock data instead of calling API")
    args = parser.parse_args()
    
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file {args.config} not found.")
        sys.exit(1)
        
    app_id = config.get('adzuna_api_id', 'TEST_ID')
    api_key = config.get('adzuna_api_key', 'TEST_KEY')
    queries = config.get('queries', ["IT Audit Manager AI"])
    
    # For testing, we won't call Adzuna if --test or empty credentials
    if args.test or not app_id or not api_key:
        logger.info("Running in test mode or missing API keys. Generating mock data.")
        mock_jobs = [
            {
                "id": "mock_sys_1",
                "title": "Senior Manager, IT Audit (AI Focus)",
                "company": {"display_name": "TechGlobal Solutions"},
                "location": {"display_name": "Los Angeles, CA"},
                "description": "We are seeking an IT Audit Manager with strong skills in SOX, ITGC, and AI governance. NIST AI RMF experience required. Cloud AWS and SAP.",
                "redirect_url": "https://example.com/job/mock_sys_1",
                "salary_min": 140000,
                "salary_max": 160000,
                "created": "2026-03-01T10:00:00Z"
            },
            {
                "id": "mock_sys_2",
                "title": "Junior Staff Auditor",
                "company": {"display_name": "Local Bank"},
                "location": {"display_name": "Torrance, CA"},
                "description": "Entry level role for recent graduates. Basic excel skills.",
                "redirect_url": "https://example.com/job/mock_sys_2",
                "salary_min": 60000,
                "salary_max": 75000,
                "created": "2026-03-02T10:00:00Z"
            },
            {
                "id": "mock_sys_3",
                "title": "AI Risk Governance Lead",
                "company": {"display_name": "FinTech Innovate"},
                "location": {"display_name": "Remote"},
                "description": "Lead our AI Risk initiatives. Must know EU AI Act, GenAI, and LLM security. CISA or AAIA preferred. AWS environment.",
                "redirect_url": "https://example.com/job/mock_sys_3",
                "salary_min": 150000,
                "salary_max": 180000,
                "created": "2026-03-02T12:00:00Z"
            }
        ]
        
        count = store_raw_jobs(args.db, mock_jobs, "mock_adzuna")
        logger.info(f"Stored {count} new mock jobs.")
    else:
        total_new = 0
        for query in queries:
            logger.info(f"Fetching for query: {query}")
            jobs = fetch_adzuna(app_id, api_key, query)
            logger.info(f"Found {len(jobs)} jobs for query.")
            if jobs:
                new_added = store_raw_jobs(args.db, jobs, "adzuna")
                total_new += new_added
                logger.info(f"Added {new_added} new jobs.")
                
        logger.info(f"Fetch complete. Total new jobs added: {total_new}")
