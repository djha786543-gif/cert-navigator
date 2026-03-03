import json
import sqlite3
import argparse
import sys
import logging
import requests
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_telegram(token, chat_id, message):
    if not token or not chat_id:
        logger.warning("Telegram credentials missing, skipping notification.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def build_digest(db_path, threshold=70, limit=5):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT r.id, r.title, r.company, s.score, s.tier, r.url
    FROM jobs_raw r
    JOIN jobs_scored s ON r.id = s.id
    WHERE s.score >= ? AND s.applied = 0
    ORDER BY s.score DESC
    LIMIT ?
    ''', (threshold, limit))
    
    top_jobs = cursor.fetchall()
    conn.close()
    
    if not top_jobs:
        return "No high-scoring jobs found today."
        
    msg = "<b>🔥 Top IT Audit Matches Today</b>\n\n"
    for job in top_jobs:
        job_id, title, company, score, tier, url = job
        icon = "🔴" if score >= 85 else ("🟡" if score >= 75 else "🔵")
        msg += f"{icon} <b>{title}</b> @ {company}\n"
        msg += f"Score: <b>{score:.1f}</b> | Tier: <b>{tier}</b>\n"
        msg += f"<a href='{url}'>Apply Here</a>\n\n"
        
    return msg

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json")
    parser.add_argument("--db", type=str, default="db/jobs.sqlite")
    parser.add_argument("--test", action="store_true", help="Print digest instead of sending")
    args = parser.parse_args()
    
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file {args.config} not found.")
        sys.exit(1)
        
    token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    
    digest = build_digest(args.db)
    
    if args.test or not token or not chat_id:
        logger.info("Test mode or missing Telegram credentials. Printing digest:")
        print(digest)
    else:
        logger.info("Sending Telegram notification...")
        send_telegram(token, chat_id, digest)
