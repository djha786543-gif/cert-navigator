import json
import sqlite3
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs_raw (
        id TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        location TEXT,
        description TEXT,
        url TEXT,
        salary_min REAL,
        salary_max REAL,
        posted_date TEXT,
        source TEXT,
        raw_data TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs_scored (
        id TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        location TEXT,
        score REAL,
        tier TEXT,
        remote_type TEXT,
        applied INTEGER DEFAULT 0,
        outcome TEXT,
        FOREIGN KEY (id) REFERENCES jobs_raw (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {db_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="db/jobs.sqlite")
    args = parser.parse_args()
    init_db(args.db)
