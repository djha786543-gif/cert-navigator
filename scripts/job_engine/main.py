import subprocess
import os
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_step(cmd):
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Step failed: {result.stderr}")
        sys.exit(1)
    logger.info(result.stdout)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run in test mode (no real API calls)")
    args = parser.parse_args()
    
    test_flag = " --test" if args.test else ""
    
    # Run the pipeline
    run_step("python init_db.py")
    run_step(f"python fetcher.py{test_flag}")
    run_step("python scorer.py")
    run_step("python filter.py")
    run_step(f"python notifier.py{test_flag}")
    
    logger.info("Pipeline complete.")
