import pandas as pd
import random
from datetime import datetime, timedelta, timezone

# ------------------------
# USERS
# ------------------------

def generate_timestamp():
    dt = datetime(2025,1,1, tzinfo=timezone.utc) + timedelta(
        days=random.randint(0,120),
        hours=random.randint(8,18),
        minutes=random.randint(0,59),
        seconds=random.randint(0,59)
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S+00")

data = []

for i in range(1,201):
    data.append({
        "usege_id": f"USE{i:03}",
        "inv_id": f"INV{random.randint(1,20):03}",
        "user_id": random.randint(1,50),
        "usege_date": generate_timestamp(),
        "value_use": round(random.uniform(0.5,5.0),2)
    })

df = pd.DataFrame(data)
df.to_csv("chemical_usege.csv", index=False)

print("Done!")