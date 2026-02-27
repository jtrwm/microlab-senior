// Global State
let selectedDate = new Date(); 
let initialDate = new Date(); 
let tempDate = new Date(initialDate);
let tempTime = { h: '09', m: '00', ap: 'AM' }; 
let currentPickerTarget = 'start';
let currentCalendarYear = initialDate.getFullYear();
let currentCalendarMonth = initialDate.getMonth() + 1;

document.addEventListener('DOMContentLoaded', () => {
    renderTimeColumns();
    initAllDayToggle();
    initDatePicker();
    initTimePicker();
    validateForm();
});

function selectStation(card, isAvailable) {
    if (isAvailable === 'False') return;
    document.querySelectorAll('.station-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    document.getElementById('inputStationId').value = card.dataset.id;
    validateForm();
}

function initAllDayToggle() {
    const toggle = document.getElementById('allDayToggle');
    const timeSlotStartBtn = document.getElementById('timeSlotStartBtn'); 
    const timeSlotEndBtn = document.getElementById('timeSlotEndBtn');
    const inputAllDay = document.getElementById('inputAllDay');

    if (!toggle || !timeSlotStartBtn || !inputAllDay) {
        console.error("ERROR: All-Day Toggle elements not found.");
        return;
    }

    const updateAllDayState = () => {
        if (toggle.checked) {
            timeSlotStartBtn.style.display = 'none'; 
            timeSlotEndBtn.style.display = 'none'; 
            inputAllDay.value = 'true';
        } else {
            timeSlotStartBtn.style.display = 'flex'; 
            timeSlotEndBtn.style.display = 'flex'; 
            inputAllDay.value = 'false';
        }
        validateForm(); 
    };
    
    updateAllDayState(); 
    toggle.addEventListener('change', updateAllDayState);
}

function initDatePicker() {
    const dateStartBtn = document.getElementById('dateSlotStartBtn');
    const dateEndBtn = document.getElementById('dateSlotEndBtn');
    const dateModal = document.getElementById('dateModal');

    if (!dateStartBtn || !dateEndBtn || !dateModal) {
        console.error("ERROR: Date Picker elements not found.");
        return;
    }

    // ผูก Event Listener คลิกที่ปุ่ม Date
    dateStartBtn.addEventListener('click', () => {
        currentPickerTarget = 'start';
        dateModal.style.display = 'flex'; // เปิด Modal
        renderCalendar(); // ต้องเรียกฟังก์ชันวาดปฏิทิน
    });

    dateEndBtn.addEventListener('click', () => {
        currentPickerTarget = 'end';
        dateModal.style.display = 'flex'; // เปิด Modal
        renderCalendar(); // ต้องเรียกฟังก์ชันวาดปฏิทิน
    });

    // Close Modal on Overlay Click
    document.getElementById('dateModal').addEventListener('click', (e) => {
        if (e.target.id === 'dateModal') e.target.style.display = 'none';
    });
}

function renderCalendar() {
    const grid = document.getElementById('calendarGrid');
    grid.innerHTML = '';
    
    const year = tempDate.getFullYear();
    const month = tempDate.getMonth();
    
    const months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    document.getElementById('calMonthYear').innerText = `${months[month]} ${year}`;

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        grid.innerHTML += `<div class="cal-day empty"></div>`;
    }

    // Days
    for (let i = 1; i <= daysInMonth; i++) {
        const div = document.createElement('div');
        div.className = 'cal-day';
        div.innerText = i;
        
        // Highlight selected
        if (i === tempDate.getDate() && month === tempDate.getMonth() && year === tempDate.getFullYear()) {
            div.classList.add('selected');
        }

        div.onclick = () => {
            tempDate.setDate(i);
            renderCalendar(); // Re-render to show selection
        };
        grid.appendChild(div);
    }
}

function changeMonth(step) {
    tempDate.setMonth(tempDate.getMonth() + step);
    renderCalendar();
}

function applyDate() {
    const selectedDate = new Date(tempDate);
    const options = { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' };
    const displayDateStr = selectedDate.toLocaleDateString('en-GB', options);;
    
    // Update Hidden Input (YYYY-MM-DD)
    const yyyy = selectedDate.getFullYear();
    const mm = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const dd = String(selectedDate.getDate()).padStart(2, '0');
    const selectedDateStr = `${yyyy}-${mm}-${dd}`;
    const selectedDateEnd = `${yyyy}-${mm}-${dd}`;

    if (currentPickerTarget === 'start') {
        document.getElementById('displayDateStart').innerText = displayDateStr; 
        document.getElementById('inputStartDate').value = selectedDateStr;
        
    } else { // currentPickerTarget === 'end'
        document.getElementById('displayDateEnd').innerText = displayDateStr; 
        document.getElementById('inputEndDate').value = selectedDateEnd;
    }

    document.getElementById('dateModal').style.display = 'none';
    validateForm();
}

function initTimePicker() {
    const timeStartBtn = document.getElementById('timeSlotStartBtn'); 
    const timeEndBtn = document.getElementById('timeSlotEndBtn'); 
    const timeModal = document.getElementById('timeModal');

    if (!timeStartBtn || !timeEndBtn || !timeModal) {
        console.error("ERROR: Time Picker button elements not found.");
        return;
    }
    
    timeStartBtn.addEventListener('click', () => {
        currentPickerTarget = 'start'; // กำหนดเป้าหมาย
        timeModal.style.display = 'flex'; // เปิด Modal
        // Note: ถ้าคุณมี Logic วาด Time Picker ก็เรียกที่นี่
        renderTimeColumns();
    });

    // 2. ผูก Event Listener สำหรับ End Time
    timeEndBtn.addEventListener('click', () => {
        currentPickerTarget = 'end'; // กำหนดเป้าหมาย
        timeModal.style.display = 'flex'; // เปิด Modal
        // Note: ถ้าคุณมี Logic วาด Time Picker ก็เรียกที่นี่
    });

    timeModal.addEventListener('click', (e) => {
        if (e.target.id === 'timeModal') e.target.style.display = 'none';
    });
}

function renderTimeColumns() {
    const colHour = document.getElementById('colHour');
    const colMinute = document.getElementById('colMinute');
    
    // Hours 01-12
    for(let i=1; i<=12; i++) {
        let val = String(i).padStart(2, '0');
        colHour.innerHTML += `<div class="time-item" onclick="selectTimeItem(this, 'h', '${val}')">${val}</div>`;
    }
    // Minutes 00-55 (Step 5)
    for(let i=0; i<60; i+=5) {
        let val = String(i).padStart(2, '0');
        colMinute.innerHTML += `<div class="time-item" onclick="selectTimeItem(this, 'm', '${val}')">${val}</div>`;
    }
    
    // Default Selection Visuals
    updateTimeVisuals();
}

function selectTimeItem(el, type, val) {
    if (type === 'h') tempTime.h = val;
    if (type === 'm') tempTime.m = val;
    if (type === 'ampm') tempTime.ap = el.innerText;
    
    updateTimeVisuals();
}

function updateTimeVisuals() {
    // Update Preview Text
    document.getElementById('timePreview').innerText = `${tempTime.h} : ${tempTime.m} ${tempTime.ap}`;

    // Highlight Selected Items logic (Simplified for brevity)
    // In real implementation, iterate items and add/remove 'selected' class based on tempTime
}

function applyTime() {
    const timeStr = `${tempTime.h}:${tempTime.m} ${tempTime.ap}`;
    const displayStart = document.getElementById('displayTimeStart');
    const inputStart = document.getElementById('inputStartTime'); 
    const displayEnd = document.getElementById('displayTimeEnd');
    const inputEnd = document.getElementById('inputEndTime');
    
    if (currentPickerTarget === 'start') {
        // อัปเดต Start Time
        if (displayStart && inputStart) { 
            displayStart.innerText = timeStr;
            inputStart.value = timeStr;
        } else {
            // โค้ดจะพิมพ์ข้อความนี้ถ้าหา element ไม่เจอ
            console.error("CRITICAL ERROR: Missing Start Time Input/Display Elements.");
        }
        
    } else { // currentPickerTarget === 'end'
        // อัปเดต End Time
        if (displayEnd && inputEnd) { 
            displayEnd.innerText = timeStr;
            inputEnd.value = timeStr;
        } else {
             // โค้ดจะพิมพ์ข้อความนี้ถ้าหา element ไม่เจอ
            console.error("CRITICAL ERROR: Missing End Time Input/Display Elements.");
        }
    }

   document.getElementById('timeModal').style.display = 'none';
    validateForm();
}

function validateForm() {
    // 1. ดึง Element และค่าอย่างปลอดภัย (จัดการกรณี null)
    const station = document.getElementById('inputStationId').value;
    const allDay = document.getElementById('allDayToggle').checked;

    const dateStart = document.getElementById('inputStartDate');
    const timeStart = document.getElementById('inputStartTime'); 
    const timeEnd = document.getElementById('inputEndTime');

    const btn = document.getElementById('confirmBtn');

    // ดึงค่าอย่างปลอดภัยจาก Element
    const dateStartValue = dateStart ? dateStart.value : '';
    const timeStartValue = timeStart ? timeStart.value : '';
    const timeEndValue = timeEnd ? timeEnd.value : '';
    
    // 2. Logic การตรวจสอบความครบถ้วน
    // ต้องเลือก Station และ Start Date เสมอ
    if (station && dateStart) {
        if (allDay) {
            // เงื่อนไข 1: ถ้า All-day ถูกติ๊ก -> ผ่านได้เลย
            btn.disabled = false;
        } else if (timeStartValue && timeEndValue) { 
            // เงื่อนไข 2: ถ้าไม่ใช่ All-day -> ต้องมี Start Time และ End Time
            btn.disabled = false;
        } else {
            // ขาดเวลา
            btn.disabled = true;
        }
    } else {
        // ขาด Station หรือ Start Date
        btn.disabled = true;
    }
}