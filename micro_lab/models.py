from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
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
        ordering = ['pk']
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
        
class Slide(models.Model):
    slide_id = models.CharField(primary_key=True, max_length=50, db_column='slide_id')
    sample_code = models.CharField(max_length=100, db_column='sample_code')
    tissue_type = models.CharField(max_length=100, db_column='tissue_type')
    stain_type = models.CharField(max_length=100, db_column='stain_type')
    location = models.CharField(max_length=100, db_column='loction') # ⚠️ สะกดตาม DB จริงของคุณ

    class Meta:
        db_table = 'slide' # ชื่อตารางใน Supabase
        managed = False  
        
class SlideImage(models.Model):
    iimage_id = models.AutoField(primary_key=True, db_column='image_id')
    slide = models.ForeignKey(Slide, on_delete=models.DO_NOTHING, db_column='slide_id', related_name='images')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, db_column='user_id')
    recorddate = models.DateTimeField(auto_now_add=True, db_column='recorddate')
    image_url = models.TextField(db_column='image_url') # คอลัมน์ที่เพิ่มใหม่
    magnification = models.CharField(max_length=50, db_column='magnification')

    class Meta:
        db_table = 'image' # ชื่อตารางรูปภาพใน Supabase
        managed = False
        
