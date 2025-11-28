
import os
import time
from datetime import datetime, timedelta

# Folders to clean
FOLDERS = ['uploads', 'downloads']
AGE_LIMIT = 10 * 60  # 10 minutes in seconds

def cleanup():
    now = time.time()
    for folder in FOLDERS:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > AGE_LIMIT:
                    try:
                        os.remove(filepath)
                        print(f"Deleted old file: {filepath}")
                    except Exception as e:
                        print(f"Error deleting {filepath}: {e}")

if __name__ == '__main__':
    cleanup()
