import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from dotenv import load_dotenv
from supabase import create_client, Client

from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder


# ============================================================
# 0. Setup
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

os.makedirs("ai_models", exist_ok=True)
os.makedirs("ai_outputs", exist_ok=True)


# ============================================================
# 1. Helper: Load table from Supabase
# ============================================================

def load_table(table_name, columns="*", batch_size=1000, max_rows=10000):
    all_rows = []
    start = 0

    while start < max_rows:
        end = start + batch_size - 1

        response = (
            supabase
            .table(table_name)
            .select(columns)
            .range(start, end)
            .execute()
        )

        rows = response.data

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < batch_size:
            break

        start += batch_size

    return pd.DataFrame(all_rows)


# ============================================================
# 2. Load Data
# ============================================================

chemical_usage = load_table(
    "chemical_usage",
    "usage_id, inv_id, user_id, usage_date, value_use"
)

chemical_inventory = load_table(
    "chemical_inventory",
    "*"
)

chemical = load_table(
    "chemical",
    "*"
)

print("chemical_usage:", chemical_usage.shape)
print("chemical_inventory:", chemical_inventory.shape)
print("chemical:", chemical.shape)

if chemical_usage.empty:
    raise ValueError("chemical_usage is empty. Check RLS policy or Supabase key.")


# ============================================================
# 3. Data Cleaning
# ============================================================

chemical_usage["usage_date"] = pd.to_datetime(
    chemical_usage["usage_date"],
    errors="coerce"
)

chemical_usage["value_use"] = pd.to_numeric(
    chemical_usage["value_use"],
    errors="coerce"
)

chemical_usage = chemical_usage.dropna(
    subset=["usage_date", "inv_id", "user_id", "value_use"]
)

chemical_usage["date"] = chemical_usage["usage_date"].dt.date
chemical_usage["date"] = pd.to_datetime(chemical_usage["date"])

print("Cleaned chemical_usage:", chemical_usage.shape)


# ============================================================
# 4. Create Daily Demand Dataset
# ============================================================

daily_demand = (
    chemical_usage
    .groupby(["date", "inv_id"], as_index=False)
    .agg(
        total_value_use=("value_use", "sum"),
        avg_value_use=("value_use", "mean"),
        transaction_count=("usage_id", "count"),
        unique_users=("user_id", "nunique")
    )
)

daily_demand = daily_demand.sort_values(["inv_id", "date"])

daily_demand["year"] = daily_demand["date"].dt.year
daily_demand["month"] = daily_demand["date"].dt.month
daily_demand["day"] = daily_demand["date"].dt.day
daily_demand["day_of_week"] = daily_demand["date"].dt.dayofweek
daily_demand["is_weekend"] = daily_demand["day_of_week"].isin([5, 6]).astype(int)

# Rolling features per inventory item
daily_demand["rolling_3day_avg"] = (
    daily_demand
    .groupby("inv_id")["total_value_use"]
    .transform(lambda x: x.rolling(3, min_periods=1).mean())
)

daily_demand["rolling_7day_avg"] = (
    daily_demand
    .groupby("inv_id")["total_value_use"]
    .transform(lambda x: x.rolling(7, min_periods=1).mean())
)

daily_demand["lag_1day"] = (
    daily_demand
    .groupby("inv_id")["total_value_use"]
    .shift(1)
)

daily_demand["lag_1day"] = daily_demand["lag_1day"].fillna(
    daily_demand["total_value_use"].mean()
)

print("daily_demand:")
print(daily_demand.head())


# ============================================================
# 5. AI Model 1: Chemical Demand Forecasting
# ============================================================

inv_encoder = LabelEncoder()
daily_demand["inv_id_encoded"] = inv_encoder.fit_transform(daily_demand["inv_id"])

features = [
    "inv_id_encoded",
    "year",
    "month",
    "day",
    "day_of_week",
    "is_weekend",
    "transaction_count",
    "unique_users",
    "rolling_3day_avg",
    "rolling_7day_avg",
    "lag_1day"
]

target = "total_value_use"

X = daily_demand[features]
y = daily_demand[target]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

forecast_model = RandomForestRegressor(
    n_estimators=300,
    max_depth=12,
    random_state=42
)

forecast_model.fit(X_train, y_train)

y_pred = forecast_model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\n=== Chemical Demand Forecasting ===")
print(f"MAE: {mae:.2f}")
print(f"R2 Score: {r2:.2f}")

joblib.dump(forecast_model, "ai_models/chemical_demand_forecast_model.pkl")
joblib.dump(inv_encoder, "ai_models/inv_encoder.pkl")


# ============================================================
# 6. Forecast Next 7 Days
# ============================================================

def forecast_next_days(days=7):
    latest_date = daily_demand["date"].max()
    future_rows = []

    for inv_id in daily_demand["inv_id"].unique():
        inv_history = daily_demand[daily_demand["inv_id"] == inv_id].sort_values("date")

        last_row = inv_history.iloc[-1]

        for i in range(1, days + 1):
            future_date = latest_date + pd.Timedelta(days=i)

            future_rows.append({
                "inv_id": inv_id,
                "date": future_date,
                "inv_id_encoded": inv_encoder.transform([inv_id])[0],
                "year": future_date.year,
                "month": future_date.month,
                "day": future_date.day,
                "day_of_week": future_date.dayofweek,
                "is_weekend": int(future_date.dayofweek in [5, 6]),
                "transaction_count": last_row["transaction_count"],
                "unique_users": last_row["unique_users"],
                "rolling_3day_avg": last_row["rolling_3day_avg"],
                "rolling_7day_avg": last_row["rolling_7day_avg"],
                "lag_1day": last_row["total_value_use"]
            })

    future_df = pd.DataFrame(future_rows)

    future_df["predicted_usage"] = forecast_model.predict(future_df[features])
    future_df["predicted_usage"] = future_df["predicted_usage"].round(2)

    return future_df


future_7days = forecast_next_days(days=7)

future_7days.to_csv("ai_outputs/predicted_chemical_usage_next_7_days.csv", index=False)

print("\nFuture 7 days prediction:")
print(future_7days.head())


# ============================================================
# 7. AI Model 2: Shortage Risk Prediction
# ============================================================

# รวม predicted usage 7 วันต่อ inv_id
predicted_7day_usage = (
    future_7days
    .groupby("inv_id", as_index=False)
    .agg(predicted_7day_usage=("predicted_usage", "sum"))
)

# เตรียม inventory
if not chemical_inventory.empty:
    chemical_inventory["chem_value"] = pd.to_numeric(
        chemical_inventory.get("chem_value"),
        errors="coerce"
    )

    risk_df = predicted_7day_usage.merge(
        chemical_inventory,
        on="inv_id",
        how="left"
    )

    def classify_shortage_risk(row):
        current_stock = row.get("chem_value")
        predicted_usage = row.get("predicted_7day_usage")

        if pd.isna(current_stock):
            return "Unknown"

        if current_stock <= 0:
            return "High Risk"

        ratio = predicted_usage / current_stock

        if ratio >= 0.8:
            return "High Risk"
        elif ratio >= 0.5:
            return "Medium Risk"
        else:
            return "Low Risk"

    risk_df["shortage_risk"] = risk_df.apply(classify_shortage_risk, axis=1)

    risk_df.to_csv("ai_outputs/chemical_shortage_risk.csv", index=False)

    print("\n=== Shortage Risk Result ===")
    print(risk_df[["inv_id", "predicted_7day_usage", "chem_value", "shortage_risk"]].head())

else:
    risk_df = pd.DataFrame()
    print("chemical_inventory is empty. Skip shortage risk prediction.")


# ============================================================
# 8. AI Model 3: Anomaly Detection
# ============================================================

anomaly_features = [
    "value_use"
]

anomaly_df = chemical_usage.copy()

anomaly_df["hour"] = anomaly_df["usage_date"].dt.hour
anomaly_df["day_of_week"] = anomaly_df["usage_date"].dt.dayofweek

anomaly_features = [
    "value_use",
    "hour",
    "day_of_week"
]

anomaly_model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42
)

anomaly_df["anomaly_score"] = anomaly_model.fit_predict(
    anomaly_df[anomaly_features]
)

anomaly_df["anomaly_label"] = anomaly_df["anomaly_score"].map({
    1: "Normal",
    -1: "Anomaly"
})

anomaly_df.to_csv("ai_outputs/chemical_usage_anomaly_detection.csv", index=False)

joblib.dump(anomaly_model, "ai_models/chemical_anomaly_model.pkl")

print("\n=== Anomaly Detection ===")
print(anomaly_df["anomaly_label"].value_counts())


# ============================================================
# 9. Graphs
# ============================================================

STATIC_AI_OUTPUT_DIR = "static/images/ai_outputs"
os.makedirs(STATIC_AI_OUTPUT_DIR, exist_ok=True)

# Graph 1: Actual vs Predicted
result_df = pd.DataFrame({
    "Actual": y_test,
    "Predicted": y_pred
})

plt.figure(figsize=(8, 6))
sns.scatterplot(data=result_df, x="Actual", y="Predicted")
plt.title("Actual vs Predicted Chemical Usage")
plt.xlabel("Actual Usage")
plt.ylabel("Predicted Usage")
plt.tight_layout()
plt.savefig(f"{STATIC_AI_OUTPUT_DIR}/actual_vs_predicted_chemical_usage.png", dpi=300)
plt.close()


# Graph 2: Feature Importance
importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": forecast_model.feature_importances_
}).sort_values(by="Importance", ascending=False)

plt.figure(figsize=(9, 6))
sns.barplot(data=importance_df, x="Importance", y="Feature")
plt.title("Feature Importance for Chemical Demand Forecasting")
plt.xlabel("Importance")
plt.ylabel("Feature")
plt.tight_layout()
plt.savefig(f"{STATIC_AI_OUTPUT_DIR}/feature_importance_chemical_forecast.png", dpi=300)
plt.close()


# Graph 3: Predicted Demand Next 7 Days
top_inv = (
    predicted_7day_usage
    .sort_values("predicted_7day_usage", ascending=False)
    .head(5)["inv_id"]
)

plot_future = future_7days[future_7days["inv_id"].isin(top_inv)]

plt.figure(figsize=(12, 6))
ax = sns.lineplot(
    data=plot_future,
    x="date",
    y="predicted_usage",
    hue="inv_id",
    marker="o"
)

plt.title("Predicted Chemical Demand for Next 7 Days")
plt.xlabel("Date")
plt.ylabel("Predicted Usage")
plt.xticks(rotation=45)

# ย้าย legend ออกไปด้านขวานอกกราฟ
plt.legend(
    title="inv_id",
    loc="upper left",
    bbox_to_anchor=(1.02, 1),
    borderaxespad=0
)

# เว้นพื้นที่ด้านขวาไว้ให้ legend
plt.tight_layout(rect=[0, 0, 0.85, 1])

plt.savefig(
    f"{STATIC_AI_OUTPUT_DIR}/predicted_demand_next_7_days.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()

# Graph 4: Shortage Risk Count
if not risk_df.empty:
    plt.figure(figsize=(7, 5))
    sns.countplot(
        data=risk_df,
        x="shortage_risk",
        order=["Low Risk", "Medium Risk", "High Risk", "Unknown"]
    )
    plt.title("Chemical Shortage Risk Level")
    plt.xlabel("Risk Level")
    plt.ylabel("Number of Inventory Items")
    plt.tight_layout()
    plt.savefig(f"{STATIC_AI_OUTPUT_DIR}/chemical_shortage_risk_count.png", dpi=300)
    plt.close()


# Graph 5: Anomaly Detection
plt.figure(figsize=(10, 5))
sns.scatterplot(
    data=anomaly_df,
    x="usage_date",
    y="value_use",
    hue="anomaly_label"
)
plt.title("Chemical Usage Anomaly Detection")
plt.xlabel("Usage Date")
plt.ylabel("Value Use")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(f"{STATIC_AI_OUTPUT_DIR}/chemical_usage_anomaly_detection.png", dpi=300)
plt.close()


# ============================================================
# 10. Save Summary
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_AI_OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "micro_lab",
    "static",
    "images",
    "ai_outputs"
)

os.makedirs(STATIC_AI_OUTPUT_DIR, exist_ok=True)

summary = {
    "model": "RandomForestRegressor + IsolationForest",
    "forecast_mae": mae,
    "forecast_r2": r2,
    "total_records": len(chemical_usage),
    "daily_demand_records": len(daily_demand),
    "anomaly_count": int((anomaly_df["anomaly_label"] == "Anomaly").sum())
}

summary_df = pd.DataFrame([summary])
summary_df.to_csv(f"{STATIC_AI_OUTPUT_DIR}/model_summary.csv", index=False)

print("\nAll AI processes completed successfully.")
print("Saved models in: ai_models/")
print("Saved outputs in: ai_outputs/")