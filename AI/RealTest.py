import os
import joblib
import pandas as pd

from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score


# =========================
# 1. Database connection
# =========================
# แก้ค่าตรงนี้ให้ตรงกับ Supabase / PostgreSQL ของตัวเอง

DATABASE_URL = "postgresql://postgres:labbiohds1925@db.sqastdkrowpwfactzncc.supabase.co:5432/postgres"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Connected successfully!")


# =========================
# 2. Load data
# =========================
query = """
SELECT
    usage_id,
    inv_id,
    user_id,
    usege_date,
    value_use
FROM chemical_usege
WHERE usege_date IS NOT NULL
  AND value_use IS NOT NULL;
"""

df = pd.read_sql(query, engine)

print("Loaded data:", df.shape)
print(df.head())


# =========================
# 3. Preprocess datetime
# =========================
df["usege_date"] = pd.to_datetime(df["usege_date"], errors="coerce")
df = df.dropna(subset=["usege_date", "value_use", "inv_id", "user_id"])

df["year"] = df["usege_date"].dt.year
df["month"] = df["usege_date"].dt.month
df["day"] = df["usege_date"].dt.day
df["day_of_week"] = df["usege_date"].dt.dayofweek
df["hour"] = df["usege_date"].dt.hour


# =========================
# 4. Encode categorical data
# =========================
inv_encoder = LabelEncoder()
df["inv_id_encoded"] = inv_encoder.fit_transform(df["inv_id"])


# =========================
# 5. Features / target
# =========================
features = [
    "inv_id_encoded",
    "user_id",
    "year",
    "month",
    "day",
    "day_of_week",
    "hour"
]

target = "value_use"

X = df[features]
y = df[target]


# =========================
# 6. Train / test split
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# =========================
# 7. Train model
# =========================
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42,
    max_depth=10
)

model.fit(X_train, y_train)


# =========================
# 8. Evaluate
# =========================
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("Training completed")
print(f"MAE: {mae:.2f}")
print(f"R2 Score: {r2:.2f}")


# =========================
# 9. Save model
# =========================
os.makedirs("ai_models", exist_ok=True)

joblib.dump(model, "ai_models/chemical_usage_model.pkl")
joblib.dump(inv_encoder, "ai_models/inv_encoder.pkl")

print("Model and encoder saved successfully")