from django.shortcuts import render, redirect
from django.db import transaction
from .models import Station, Booking, User
from django.utils import timezone
import datetime
import calendar
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import uuid
import json

def get_processed_stations(selected_pk=None):
    """
    ดึงข้อมูลสถานีทั้งหมด และเพิ่ม Attribute สถานะ/สี สำหรับ Template
    """
    # ** แก้ปัญหา N+1 Query: ดึงข้อมูลที่จำเป็นล่วงหน้า **
    # ถ้า Station มี FK ชี้ไปที่ตารางอื่น ควรใช้ select_related
    stations_qs = Station.objects.all()
    
    processed_stations = []
    
    for station in stations_qs:
        # กำหนดสถานะ Available/Not Available และสี ตาม Logic จำลอง
        # (สมมติว่า Station 5, 6 ไม่ว่าง)
        if station.pk in [5, 6]: 
            station.status_text = 'Not Available'
            station.status_color = 'not-available-text' # Class ใน booking.css
            station.is_available = False
        else:
            station.status_text = 'Available'
            station.status_color = 'available-text' # Class ใน booking.css
            station.is_available = True
            
        # กำหนดสถานะถูกเลือก
        if selected_pk and station.pk == selected_pk:
            station.is_selected = True
        else:
            station.is_selected = False
        
        processed_stations.append(station)
        
    return processed_stations

# ----------------------------------------------------------------------
# 1. Home View (แสดง Station Grid และ Calendar)
# ----------------------------------------------------------------------

def home_view(request):
    
    # ดึงสถานีที่ผ่านการประมวลผล (ไม่มีการเลือกสถานีเริ่มต้นในหน้า Home)
    available_stations = get_processed_stations(selected_pk=None)
    
    # ตั้งค่าเดือน/ปีเป้าหมาย (ใช้เดือนปัจจุบันหากต้องการให้เป็น Dynamic)
    today = datetime.date.today()
    target_year = today.year
    target_month = today.month
    
    current_month_str = datetime.date(target_year, target_month, 1).strftime("%B %Y")
    
    # ดึงข้อมูลการจองทั้งหมดสำหรับเดือนนั้น
    # ใช้ค่า Booking.booking_date ที่มีอยู่จริงในตาราง
    booked_dates_qs = Booking.objects.filter(
        booking_date__year=target_year,
        booking_date__month=target_month
    ).values_list('booking_date', flat=True) 
    
    # แปลงเป็นเซ็ตของวันที่เพื่อให้ค้นหาได้เร็ว 
    booked_dates_set = {date.day for date in booked_dates_qs}
    
    # สร้างโครงสร้างปฏิทิน
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_calendar = cal.monthdays2calendar(target_year, target_month)
    
    # สร้างข้อมูลวันที่พร้อมสถานะสำหรับ Template
    calendar_data = []
    
    for week in month_calendar:
        week_data = []
        for day, weekday in week:
            if day == 0:
                # วันที่ว่าง (วันที่ 0 คือช่องว่างในปฏิทิน)
                week_data.append({'day': '', 'status': 'empty'})
            else:
                status = 'available'
                if day in booked_dates_set:
                    status = 'booked'
                
                week_data.append({
                    'day': day, 
                    'status': status, 
                    'weekday': weekday
                })
        calendar_data.append(week_data)

    context = {
        'stations': available_stations,
        'current_month': current_month_str,
        'calendar_data': calendar_data, 
    }
    return render(request, 'micro_lab/home.html', context)

# ----------------------------------------------------------------------
# 2. Booking Detail View (แสดง Station Grid และ Booking Panel)
# ----------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def booking_view(request):
    selected_date_str = request.GET.get('date') 
    if selected_date_str:
        target_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.date.today()

    # 2. จากนั้นค่อยเอา target_date ไป Filter การจอง
    # ถ้าคุณเอาบรรทัดนี้ไปไว้ข้างบนสุด มันจะดึงของ "วันนี้" ตลอดเวลา
    existing_bookings = Booking.objects.filter(
        reservation_date=target_date, # ต้องใช้ตัวแปรที่รับมาจากด้านบน
        booking_status='CONFIRMED'
    )
    
    # --- 1. จัดการ POST Request (บันทึกข้อมูล) ---
    if request.method == 'POST':
        try:
            # 1. Debug: ตรวจสอบว่า POST Request ถูกรับค่า
            print("--- POST Data Received ---")
            print(f"Station ID: {request.POST.get('selected_station_id')}")
            
            # 2. รับค่าจาก Hidden Inputs
            station_id = request.POST.get('selected_station_id')
            start_date_str = request.POST.get('start_date')     
            start_time_str = request.POST.get('start_time')     
            end_date_str = request.POST.get('end_date')         
            end_time_str = request.POST.get('end_time')         
            # is_all_day = request.POST.get('is_all_day') == 'true'

            # 3. ดึง Station Object
            selected_station = Station.objects.get(pk=station_id)
            
            # 4. กำหนด Date/Time 
            DATE_FORMAT = '%Y-%m-%d'
            TIME_FORMAT = '%I:%M %p' 
            
            start_datetime_str = f"{start_date_str} {start_time_str}"
            end_datetime_str = f"{end_date_str} {end_time_str}"

            start_datetime = datetime.datetime.strptime(start_datetime_str, f"{DATE_FORMAT} {TIME_FORMAT}")
            end_datetime = datetime.datetime.strptime(end_datetime_str, f"{DATE_FORMAT} {TIME_FORMAT}")

            # ทำให้เป็น Aware Datetime เพื่อลด RuntimeWarning
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

            # 5. Validation: เวลาเริ่มต้องน้อยกว่าเวลาจบ
            if start_datetime >= end_datetime:
                raise ValueError("เวลาเริ่มต้นต้องมาก่อนเวลาสิ้นสุด")
            
            overlapping_bookings = Booking.objects.filter(
                station_id=selected_station.pk,      # 1. เช็คเฉพาะ Station ที่เลือก
                booking_status='CONFIRMED',          # 2. เช็คเฉพาะรายการที่ยืนยันแล้ว
                
                # 3. สูตรเช็คเวลาชน (Overlap Logic)
                # "เวลาเริ่มของเรา ต้องมาก่อนเวลาจบของเขา" และ "เวลาจบของเรา ต้องมาหลังเวลาเริ่มของเขา"
                # ถ้าเงื่อนไขนี้เป็นจริง แสดงว่าช่วงเวลาซ้อนทับกัน
                daystart__lt=end_datetime, 
                dayend__gt=start_datetime
            )
            
            if overlapping_bookings.exists():
                # ถ้าเจอรายการที่ชนกัน ให้แจ้ง Error ว่า "Unavailable"
                messages.error(request,f"Station นี้ไม่ว่าง (Unavailable) ในช่วงเวลา {start_datetime.strftime('%H:%M')} - {end_datetime.strftime('%H:%M')} กรุณาเลือกเวลาอื่น")
                return redirect('booking')
            # 6. เตรียมข้อมูลสำหรับ Database Field
            booking_pk = str(uuid.uuid4())
            
            if request.user.is_authenticated:
                user_pk = request.user.id  # ส่ง ID จริง (เช่น 1, 2, 5)
            else:
                user_pk = 1  
            
            booking_status_default = 'CONFIRMED'
            
            print(f"DEBUG: Booking ID type: {type(booking_pk)}")
            print(f"DEBUG: Station ID type: {type(selected_station.pk)} Value: {selected_station.pk}")
            print(f"DEBUG: User ID type: {type(user_pk)} Value: {user_pk}")
            # 7. บันทึกลง Database ด้วย Transaction
            with transaction.atomic():
                Booking.objects.create(
                    booking_id=booking_pk, 
                    station_id=selected_station.pk, 
                    
                    # ส่ง user_pk ที่เป็นตัวเลข (Integer) ไป
                    user_id=user_pk,           
                    
                    booking_status=booking_status_default,
                    daystart=start_datetime,
                    dayend=end_datetime,
                    
                    # ส่งให้ครบ 2 วันที่
                    reservation_date=start_datetime.date(), 
                    booking_date=datetime.date.today(), 
                )
                
                # เปลี่ยนสถานะ Station (ถ้าต้องการ)
                # selected_station.current_status = 'Unavailable'
                # selected_station.save()

            # 8. แจ้งเตือนและ Redirect
            print("--- SAVE SUCCESSFUL ---")
            messages.success(request, 'บันทึกการจองเรียบร้อยแล้ว')
            return redirect('home')

        except Station.DoesNotExist:
            messages.error(request, 'ไม่พบ Station ที่ถูกเลือก')
        except ValueError as ve:
            messages.error(request, f'ข้อมูลไม่ถูกต้อง: {ve}')
        except Exception as e:
            print(f"Booking Save Error: {e}")
            messages.error(request, f'เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}')
        except Exception as e:
            import traceback
            print("---------------- ERROR LOG ----------------")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e}")
            print("Traceback:")
            print(traceback.format_exc()) # บรรทัดนี้จะบอกจุดตาย
            print("-------------------------------------------")
            messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
            return redirect('booking_url_name')
            
    # --- 2. จัดการ GET Request (แสดงหน้าเว็บ) ---
    selected_date_str = request.GET.get('date') 
    if selected_date_str:
        target_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.date.today()
    
    stations_list = get_processed_stations(target_date=target_date)
    
    # 1. ดึงรายการจองที่ยืนยันแล้วของ "วันที่เลือก" เท่านั้น
    existing_bookings = Booking.objects.filter(
        reservation_date=target_date,
        booking_status='CONFIRMED'
    )

    # 2. แปลงเป็น List เพื่อส่งให้ JavaScript
    booked_slots = []
    for b in existing_bookings:
        start_dt = b.daystart
        # เช็คและทำให้เป็น Aware โดยใช้ datetime.timezone.utc
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt, datetime.timezone.utc)
            
        end_dt = b.dayend
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt, datetime.timezone.utc)

        # แปลงเป็นเวลาไทย
        local_start = timezone.localtime(start_dt)
        local_end = timezone.localtime(end_dt)

        booked_slots.append({
            'station_id': str(b.station_id).strip(),
            'start': local_start.strftime('%I:%M %p'),
            'end': local_end.strftime('%I:%M %p')
    })
    
    # ส่ง error_message (ถ้ามีจาก catch block ด้านบน แต่ปกติ redirect จะทำงานก่อน)
    context = {
        'stations': stations_list,
        'booked_slots_json': json.dumps(booked_slots),
        'selected_date': target_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'micro_lab/booking.html', context)
        
def get_processed_stations(selected_pk=None, target_date=None):
    
    # 1. ถ้าไม่ได้ระบุวัน ให้ใช้วันนี้
    if target_date is None:
        target_date = datetime.date.today()

    # 2. ค้นหา ID ของ Station ที่ "ถูกจองแล้ว" ในวันที่เป้าหมาย
    # เช็คว่ามีการจองที่ status='CONFIRMED' และวันที่ตรงกัน (หรือเวลาเหลื่อมกัน)
    booked_station_ids = Booking.objects.filter(
        reservation_date=target_date, 
        booking_status='CONFIRMED'
    ).values_list('station_id', flat=True)

    # 3. ดึง Station ทั้งหมด
    all_stations = Station.objects.all()
    processed_stations = []

    for station in all_stations:
        # 4. เช็คว่า Station นี้อยู่ในรายการที่ถูกจองหรือไม่?
        if station.pk in booked_station_ids:
            # ถ้ามีคนจองวันนี้ -> ไม่ว่าง
            station.status_text = 'Booked'
            station.status_color = 'not-available-text'
            station.is_available = False
        else:
            # ถ้าไม่มีคนจอง -> ว่าง
            station.status_text = 'Available'
            station.status_color = 'available-text'
            station.is_available = True
            
        # Logic การเลือก (เหมือนเดิม)
        station.is_selected = (selected_pk and str(station.pk) == str(selected_pk))
        processed_stations.append(station)
        
    return processed_stations

# ... และใน booking_view (GET Logic) ...
stations = get_processed_stations() # เรียกใช้ฟังก์ชันที่ปรับปรุงแล้ว
available_stations = stations # ใช้ชื่อตัวแปรให้ชัดเจน