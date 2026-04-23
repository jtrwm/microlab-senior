import pandas as pd
import random
import string
from datetime import datetime, timedelta, timezone

# =========================
# CONFIG
# =========================
NUM_INVENTORY = 100
NUM_USAGE = 300

# =========================
# Load user จริง
# =========================
df_users = pd.read_csv("auth_user_new.csv")

# สมมติ column ชื่อ id
user_ids = df_users["id"].tolist()

# =========================
# Helper functions
# =========================
def random_id(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

# ✅ ใช้ของคุณเลย
def generate_pg_timestamp():
    dt = datetime(2025,1,1, tzinfo=timezone.utc) + timedelta(
        days=random.randint(0,365),
        hours=random.randint(0,23),
        minutes=random.randint(0,59),
        seconds=random.randint(0,59),
        microseconds=random.randint(0,999999)
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f+00")

# =========================
# 1. Generate chemical_inventory
# =========================
inventory_data = []

chem_ids = [f"CHEM{str(i).zfill(3)}" for i in range(1, 21)]

for _ in range(NUM_INVENTORY):
    inv_id = random_id("INV")
    chem_id = random.choice(chem_ids)
    chem_value = round(random.uniform(10, 500), 2)
    chem_expire = random_date(datetime(2025, 1, 1), datetime(2027, 12, 31)).date()

    inventory_data.append({
        "inv_id": inv_id,
        "chem_id": chem_id,
        "chem_value": chem_value,
        "chem_expire": chem_expire
    })

df_inventory = pd.DataFrame(inventory_data)

# =========================
# 2. Generate chemical_usage
# =========================
usage_data = []

inv_ids = df_inventory["inv_id"].tolist()

for _ in range(NUM_USAGE):
    usage_id = random_id("USE")
    inv_id = random.choice(inv_ids)

    # ✅ ใช้ user จริง
    user_id = random.choice(user_ids)

    value_use = round(random.uniform(1, 50), 2)

    # ✅ ใช้ timestamptz format ของคุณ
    usage_date = generate_pg_timestamp()

    usage_data.append({
        "usage_id": usage_id,
        "inv_id": inv_id,
        "user_id": user_id,
        "value_use": value_use,
        "usage_date": usage_date
    })

df_usage = pd.DataFrame(usage_data)

# =========================
# Save
# =========================
df_inventory.to_csv("chemical_inventory.csv", index=False)
df_usage.to_csv("chemical_usage.csv", index=False)

print("✅ Done (ใช้ user จริง + timestamptz แล้ว)")