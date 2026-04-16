import pandas as pd
import random
from datetime import datetime, timedelta, timezone

# ------------------------
# USERS
# ------------------------

users = []

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

for i in range(1, 51):
    users.append({
        "id": i,
        "password": "pbkdf2_sha256$dummyhashedpassword",  # dummy
        "last_login": generate_pg_timestamp(),
        "is_superuser": random.choice([True, False]),
        "username": f"user{i}",
        "first_name": f"Name{i}",
        "last_name": f"Surname{i}",
        "email": f"user{i}@lab.com",
        "is_staff": random.choice([True, False]),
        "is_active": True,
        "date_joined": generate_pg_timestamp()
    })

users_df = pd.DataFrame(users)
users_df.to_csv("auth_user.csv", index=False)

# ------------------------
# EQUIPMENT
# ------------------------

equipments = []
for i in range(1,11):
    equipments.append({
        "equip_id": f"E{i:03}",
        "equip_name": f"Microscope_{i}",
        "status": random.choice(["Available","In Use","Maintenance"])
    })

equipment_df = pd.DataFrame(equipments)
equipment_df.to_csv("equipment.csv", index=False)

# ------------------------
# SLIDES
# ------------------------

tissues = ["Liver","Kidney","Brain","Muscle","Skin"]
stains = ["H&E","PAS","Trichrome","Gram"]

slides = []
for i in range(1,201):
    slides.append({
        "slide_id": f"S{i:04}",
        "sample_code": f"SP{i:04}",
        "tissue_type": random.choice(tissues),
        "stain_type": random.choice(stains),
        "loction": f"Cabinet-{random.randint(1,10)}"
    })

slides_df = pd.DataFrame(slides)
slides_df.to_csv("slide.csv", index=False)

# ------------------------
# EQUIPMENT USAGE (500 rows)
# ------------------------

usage = []

for i in range(1,501):

    # เลือก user (บางคนใช้บ่อย)
    user_id = random.choices(
        population=range(1,51),
        weights=[5 if x < 10 else 1 for x in range(1,51)]
    )[0]

    # เลือกเครื่อง (มีแค่ 10)
    equip_id = f"E{random.randint(1,10):03}"

    # เวลา (ทำให้เหมือน lab จริง = ใช้กลางวัน)
    start = datetime(2025,1,1) + timedelta(
        days=random.randint(0,120),
        hours=random.randint(8,18)
    )

    end = start + timedelta(hours=random.randint(1,3))

    usage.append({
        "usage_id": i,
        "equip_id": equip_id,
        "user_id": user_id,
        "slide_id": f"S{random.randint(1,200):04}",
        "start_time": start,
        "end_time": end,
        "purpose": random.choice(["Research","Teaching","Diagnosis"])
    })

usage_df = pd.DataFrame(usage)
usage_df.to_csv("equipment_usage.csv", index=False)

# ------------------------
# LAB ACCESS (500 rows)
# ------------------------

access = []

for i in range(1,501):
    access.append({
        "log_id": f"L{i:05}",
        "user_id": random.randint(1,50),
        "access_time": generate_pg_timestamp(),
        "access_type": random.choice(["Check-in","Check-out"])
    })

access_df = pd.DataFrame(access)
access_df.to_csv("lab_access.csv", index=False)

print("Dataset generated successfully!")