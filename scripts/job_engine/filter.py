import sqlite3
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_jobs(db_path, threshold=70, limit=10):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT r.title, r.company, s.score, s.tier, r.url
    FROM jobs_raw r
    JOIN jobs_scored s ON r.id = s.id
    WHERE s.score >= ? AND s.applied = 0
    ORDER BY s.score DESC
    LIMIT ?
    ''', (threshold, limit))
    
    top_jobs = cursor.fetchall()
    conn.close()
    
    for job in top_jobs:
        logger.info(f"[{job[2]:.1f}] {job[0]} @ {job[1]} ({job[3]}) - {job[4]}")
        
    return top_jobs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="db/jobs.sqlite")
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    
    jobs = filter_jobs(args.db, args.threshold, args.limit)
    logger.info(f"Found {len(jobs)} jobs meeting threshold {args.threshold}.")
