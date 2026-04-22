from django.shortcuts import render, redirect
from django.db import transaction
from .models import Station, Booking, User, Slide
from django.utils import timezone
import datetime
import calendar
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import uuid
import json
from django.http import JsonResponse
from datetime import date
from django.contrib.auth.decorators import login_required 
from .forms import RegisterForm
from django.core.paginator import Paginator

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

def home_view(request):  
    # ตั้งค่าเดือน/ปีเป้าหมาย (ใช้เดือนปัจจุบันหากต้องการให้เป็น Dynamic)
    today = datetime.date.today()
    try:
        target_year = int(request.GET.get('year', today.year))
        target_month = int(request.GET.get('month', today.month))
    except ValueError:
        target_year = today.year
        target_month = today.month
    # เดือนก่อนหน้า
    if target_month == 1:
        prev_month = 12
        prev_year = target_year - 1
    else:
        prev_month = target_month - 1
        prev_year = target_year

    # เดือนถัดไป
    if target_month == 12:
        next_month = 1
        next_year = target_year + 1
    else:
        next_month = target_month + 1
        next_year = target_year
        
    available_stations = get_processed_stations(selected_pk=None)
    current_month_str = datetime.date(target_year, target_month, 1).strftime("%B %Y")
    
    bookings_qs = Booking.objects.filter(
        reservation_date__year=target_year,
        reservation_date__month=target_month,
        booking_status='CONFIRMED'
    ).order_by('station_id', 'daystart')
    
    # 4. จัดกลุ่มการจองลงใน Dictionary โดยใช้ 'วันที่' เป็น Key
    # โครงสร้าง: { 21: [booking1, booking2], 22: [...] }
    bookings_by_day = {}
    for b in bookings_qs:
        day = b.reservation_date.day
        if day not in bookings_by_day:
            bookings_by_day[day] = []
        
        # จัดฟอร์แมตเวลาให้สั้นลง (เช่น 01:00 PM -> 1 PM)
        start_t = b.daystart.strftime('%I:%M %p').lstrip('0').lower()
        end_t = b.dayend.strftime('%I:%M %p').lstrip('0').lower()
        
        bookings_by_day[day].append({
            'station_id': b.station_id,
            'time_range': f"{start_t} - {end_t}"
        })
    
    # สร้างโครงสร้างปฏิทิน
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_calendar = cal.monthdays2calendar(target_year, target_month)
    
    # สร้างข้อมูลวันที่พร้อมสถานะสำหรับ Template
    calendar_data = []
    
    for week in month_calendar:
        week_data = []
        for day, weekday in week:
            if day == 0:
                week_data.append({'day': '', 'status': 'empty', 'bookings': []})
            else:
                # ดึงรายการจองของวันนั้นๆ มาจาก Dictionary ที่เราเตรียมไว้
                daily_bookings = bookings_by_day.get(day, [])
                
                status = 'available'
                if daily_bookings:
                    status = 'booked'
                
                week_data.append({
                    'day': day, 
                    'status': status, 
                    'weekday': weekday,
                    'bookings': daily_bookings # 🚀 ส่ง List ของการจองไปให้หน้า Home
                })
        calendar_data.append(week_data)

    context = {
        'stations': available_stations,
        'current_month': current_month_str,
        'calendar_data': calendar_data,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'micro_lab/calendar_partial.html', context)
    
    # ถ้าเป็นการเข้าหน้าเว็บปกติ ให้ส่งหน้าเต็มไป
    return render(request, 'micro_lab/home.html', context)

@require_http_methods(["GET", "POST"])
@login_required
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
                print(f"DEBUG POST START: {start_date_str}")
                print(f"DEBUG POST END: {end_date_str}")
                new_booking = Booking.objects.create(
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
            return redirect('booking_complete', booking_id=new_booking.booking_id)

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
        
    #stations = get_processed_stations() # เรียกใช้ฟังก์ชันที่ปรับปรุงแล้ว
    #available_stations = stations # ใช้ชื่อตัวแปรให้ชัดเจน
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

def api_get_booked_slots(request):
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'booked_slots': []})

    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # ดึงการจองของวันที่เลือก ที่ยืนยันแล้ว
    existing_bookings = Booking.objects.filter(
        reservation_date=target_date,
        booking_status='CONFIRMED'
    )

    booked_slots = []
    for b in existing_bookings:
        start_dt = b.daystart
        end_dt = b.dayend
        
        if timezone.is_naive(start_dt): start_dt = timezone.make_aware(start_dt, datetime.timezone.utc)
        if timezone.is_naive(end_dt): end_dt = timezone.make_aware(end_dt, datetime.timezone.utc)

        local_start = timezone.localtime(start_dt)
        local_end = timezone.localtime(end_dt)

        booked_slots.append({
            'station_id': str(b.station_id).strip(),
            'start': local_start.strftime('%I:%M %p'),
            'end': local_end.strftime('%I:%M %p')
        })

    return JsonResponse({'booked_slots': booked_slots})

@login_required
def booking_complete(request, booking_id):
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        booking_obj = Booking.objects.get(booking_id=booking_id)
        station_obj = Station.objects.get(station_id=booking_obj.station_id)
        booking_obj.station_name = station_obj.station_name
        # แก้ตรงนี้: เติม micro_lab/ นำหน้าชื่อไฟล์
        return render(request, 'micro_lab/booking_complete.html', {'booking': booking_obj})
    except (Booking.DoesNotExist, Station.DoesNotExist):
        return render(request, 'micro_lab/404.html')
    
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save() # บันทึก User ลงฐานข้อมูล
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login') # สมัครเสร็จให้เด้งไปหน้า Login
    else:
        form = RegisterForm()
    return render(request, 'micro_lab/register.html', {'form': form})

def all_slides_view(request):
    # ดึงข้อมูลทั้งหมดจากตาราง slides ใน Supabase
    slides = Slide.objects.all() 
    return render(request, 'micro_lab/all_slides.html', {'slides': slides})

def all_slides_view(request):
    slide_list = Slide.objects.prefetch_related('images').all()
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10
    paginator = Paginator(slide_list, per_page)
    page_number = request.GET.get('page')
    slides = paginator.get_page(page_number)
    total_results = paginator.count
    start_index = slides.start_index()
    end_index = slides.end_index()
    context = {
        'slides': slides,
        'per_page': per_page,
        'total_results': total_results,
        'start_index': start_index,
        'end_index': end_index,
    }
    return render(request, 'micro_lab/all_slides.html', context)