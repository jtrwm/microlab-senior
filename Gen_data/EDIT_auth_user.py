import pandas as pd
import random
from datetime import datetime, timedelta, timezone

# ------------------------
# USERS
# ------------------------

access = []

def generate_pg_timestamp():
    dt = datetime(2025,1,1, tzinfo=timezone.utc) + timedelta(
        days=random.randint(0,365),
        hours=random.randint(0,23),
        minutes=random.randint(0,59),
        seconds=random.randint(0,59),
        microseconds=random.randint(0,999999)
    )
    
    # format ให้ตรง PostgreSQL
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f+00")

for i in range(1,501):
    access.append({
        "log_id": f"L{i:05}",
        "user_id": random.randint(1,50),
        "access_time": generate_pg_timestamp(),
        "access_type": random.choice(["Check-in","Check-out"])
    })

access_df = pd.DataFrame(access)
access_df.to_csv("lab_access_new.csv", index=False)

print("Dataset generated successfully!")