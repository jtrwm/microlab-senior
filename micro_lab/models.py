from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model() # จะชี้ไปที่ auth_user

# --- 1. โมเดลสถานี (ใช้ตาราง 'station' เดิม) ---
class Station(models.Model):
    # ตรวจสอบชื่อฟิลด์ให้ตรงกับคอลัมน์ในตาราง 'station'
    # เช่น ถ้าคอลัมน์ PK คือ 'station_id'
    station_id = models.CharField(max_length=20, primary_key=True)
    station_name = models.CharField(max_length=255) 
    station_details = models.TextField(null=True, blank=True)
    current_status = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'station'
        managed = False           # ***สำคัญ: ห้าม Django จัดการตารางนี้***
    
    def __str__(self):
        return self.station_name

# --- 2. โมเดลการจอง (ใช้ตาราง 'booking' เดิม) ---
class Booking(models.Model):
    # Booking ID: ตรงแล้ว (Char 100)
    booking_id = models.CharField(max_length=100, primary_key=True)
    
    # Station ID: ตรงแล้ว (Char 100)
    station_id = models.CharField(max_length=100)
    
    # *** แก้ตรงนี้: User ID ใน DB เป็น Integer ***
    user_id = models.IntegerField() 

    # Field เวลาและวันที่
    daystart = models.DateTimeField()
    dayend = models.DateTimeField()
    booking_status = models.CharField(max_length=100)
    
    # Field วันที่ตาม DB
    booking_date = models.DateField()      # DEFAULT CURRENT_DATE
    reservation_date = models.DateField()  # NOT NULL
    
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'booking'
        managed = False