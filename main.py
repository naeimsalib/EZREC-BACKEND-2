#!/usr/bin/env python3
"""
EZREC Backend - Main service file
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime

# Create basic structure first
print("EZREC Backend Starting...")

# Setup basic logging
LOG_DIR = Path('/opt/ezrec-backend/logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'ezrec.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("EZREC Backend service started")
    
    while True:
        try:
            logger.info("Service running...")
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Service stopped")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main() 