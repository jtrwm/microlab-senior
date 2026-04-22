var calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    timeZone: 'local',
    events: '/api/calendar-events/',
    
    // 🚀 เพิ่มบรรทัดนี้เพื่อให้แสดงผลเป็นแถบ (Bars) แทนที่จะเป็นแค่จุด
    eventDisplay: 'block', 
    
    // จัดรูปแบบเวลาให้ดูง่าย
    eventTimeFormat: {
        hour: 'numeric',
        minute: '2-digit',
        meridiem: 'short',
        hour12: true
    }
});