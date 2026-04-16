import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import urllib.parse
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from statsmodels.tsa.seasonal import seasonal_decompose

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================

db_url = "postgresql://postgres.sqastdkrowpwfactzncc:LABBIOHDS1925@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(db_url)

def get_full_dataset():
    # JOIN ข้อมูลสารเคมี (Usage) กับคลังสินค้า (Inventory) 
    # และใช้ booking_date เป็นวันที่อ้างอิง (เนื่องจาก usege_date มีแค่เวลา)
    query = """
    SELECT 
        b.booking_date as date,
        c.chem_name,
        u.value_use,
        i.chem_value as stock_balance
    FROM public.chemical_usege u
    JOIN public.chemical_inventory i ON u.inv_id = i.inv_id
    JOIN public.chemical c ON i.chem_id = c.chem_id
    JOIN public.booking b ON u.user_id = b.user_id
    ORDER BY b.booking_date ASC;
    """
    return pd.read_sql(query, engine)

# ==========================================
# 2. DATA PREPROCESSING & FEATURE ENGINEERING
# ==========================================
def preprocess_data(df):
    # รวมยอดการใช้อ้างอิงตามวันที่
    df['date'] = pd.to_datetime(df['date'])
    daily_df = df.groupby('date').agg({'value_use': 'sum'}).reset_index()
    daily_df.set_index('date', inplace=True)
    
    # สร้าง Features สำหรับ AI
    daily_df['day_of_week'] = daily_df.index.dayofweek
    daily_df['is_weekend'] = daily_df['day_of_week'].isin([5, 6]).astype(int)
    daily_df['lag_1'] = daily_df['value_use'].shift(1) # ยอดใช้เมื่อวาน
    daily_df['rolling_mean_3'] = daily_df['value_use'].rolling(window=3).mean() # เฉลี่ย 3 วัน
    
    return daily_df.dropna()

# ==========================================
# 3. AI MODELING (REGRESSION)
# ==========================================
def train_ai_model(df):
    X = df[['day_of_week', 'is_weekend', 'lag_1', 'rolling_mean_3']]
    y = df['value_use']
    
    # แบ่งข้อมูล 80% สอน, 20% ทดสอบ
    split = int(len(df) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    
    # พยากรณ์
    y_pred = model.predict(X_test)
    
    # วัดผล (ใช้ในรายงานโปรเจกต์)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    return model, y_test, y_pred, mae, r2

# ==========================================
# 4. EXECUTION & VISUALIZATION
# ==========================================
try:
    print("🚀 Starting AI Resource Analysis System...")
    raw_data = get_full_dataset()
    clean_data = preprocess_data(raw_data)
    
    # วิเคราะห์แนวโน้ม (Time Series Analysis)
    print("📈 Analyzing Trends...")
    res = seasonal_decompose(clean_data['value_use'], model='additive', period=min(len(clean_data)//2, 7))
    res.plot()
    plt.show()

    # สอน AI
    print("🤖 Training AI Model...")
    model, y_test, y_pred, mae, r2 = train_ai_model(clean_data)
    
    print(f"✅ Training Complete!")
    print(f"📊 Accuracy (R2 Score): {r2:.2f}")
    print(f"📉 Average Error: {mae:.2f} units")

    # พยากรณ์ค่าสำหรับวันพรุ่งนี้
    last_row = clean_data.iloc[-1:]
    next_day_pred = model.predict(last_row[['day_of_week', 'is_weekend', 'lag_1', 'rolling_mean_3']])
    print(f"🔮 Predicted Chemical Usage for Tomorrow: {next_day_pred[0]:.2f}")

except Exception as e:
    print(f"❌ Error: {e}")