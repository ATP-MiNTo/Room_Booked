// src/App.jsx
import { useState, useMemo, forwardRef } from 'react'; // 👉 เพิ่ม forwardRef เข้ามา
import { RiCalendarEventFill } from 'react-icons/ri'; 
import DatePicker from 'react-datepicker'; // 👉 นำเข้าไลบรารีปฏิทินตัวใหม่
import 'react-datepicker/dist/react-datepicker.css'; // 👉 นำเข้า CSS ของปฏิทิน
import SeatMap from './components/SeatMap';
import ReservationForm from './components/ReservationForm';
import TimeSelector from './components/TimeSelector';
import './styles/App.css'; 

function App() {
  // --- 1. State Management ---
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date()); // เปลี่ยนมาเก็บเป็น Date Object ของจริง
  const [startTime, setStartTime] = useState("08:30");
  const [endTime, setEndTime] = useState("09:30"); 

  // --- 2. Logic ---
  
  // แปลง Date เป็นภาษาไทยแบบเดิม
  const formatThaiDate = (dateObj) => {
    if (!dateObj) return "";
    return dateObj.toLocaleDateString('th-TH', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  };

  const allTimeSlots = [ "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00" ];
  const mockBookings = { };

  const getDisplayEndTime = (time) => {
    if (!time) return "";
    const [hourStr, minStr] = time.split(":");
    let hour = parseInt(hourStr);
    let min = parseInt(minStr);
    if (min === 0) { hour -= 1; min = 59; } 
    else if (min === 30) { min = 29; }
    return `${hour.toString().padStart(2, '0')}:${min}`;
  };

  const occupiedSeats = useMemo(() => {
    if (!startTime || !endTime) return [];
    const busySet = new Set();
    const startIndex = allTimeSlots.indexOf(startTime);
    const endIndex = allTimeSlots.indexOf(endTime);
    for (let i = startIndex; i < endIndex; i++) {
      const timeSlot = allTimeSlots[i];
      const bookingsInSlot = mockBookings[timeSlot] || [];
      bookingsInSlot.forEach(seat => busySet.add(seat));
    }
    return Array.from(busySet);
  }, [startTime, endTime]); 

  const handleStartTimeChange = (newStart) => {
    setStartTime(newStart);
    const startIndex = allTimeSlots.indexOf(newStart);
    const nextSlot = allTimeSlots[startIndex + 1];
    if (nextSlot) setEndTime(nextSlot); else setEndTime("");
    setSelectedSeat(null); 
  };

  const handleConfirmReservation = (data) => {
    alert(`ยืนยันการจอง!\n\nวันที่: ${formatThaiDate(selectedDate)}\nเวลา: ${startTime} - ${getDisplayEndTime(endTime)}\nโต๊ะ: ${selectedSeat}\nชื่อ: ${data.firstName} ${data.lastname}\nสาขา: ${data.major}\nวัตถุประสงค์: ${data.purpose || 'ไม่ระบุ'}`);
  };

  // 👉 1. สร้างปุ่มดีไซน์โปร่งใสของเรา เพื่อเอาไปเป็น "ปุ่มกดเรียกปฏิทิน"
  const CustomDateInput = forwardRef(({ onClick }, ref) => (
    <div 
      onClick={onClick}
      ref={ref}
      style={{ 
        width: '100%', 
        backgroundColor: 'transparent', 
        padding: '5px 0', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        boxSizing: 'border-box',
        border: 'none', 
        cursor: 'pointer',
        transition: 'opacity 0.2s'
      }}
      onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'} 
      onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
    >
        <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: 'white' }}>
            {formatThaiDate(selectedDate)}
        </div>
        <RiCalendarEventFill size={42} color="white" />
    </div>
  ));

  // 👉 2. ฟังก์ชันตรวจสอบวัน (0 = อาทิตย์, 1 = จันทร์, ..., 6 = เสาร์)
  const isNotSunday = (date) => {
    const day = date.getDay();
    return day !== 0; // ถ้าไม่ใช่วันอาทิตย์ (0) จะกดได้ปกติ
  };

  // --- 3. Render ---
  return (
    <div className="main-layout">
      
      {/* ฝั่งซ้าย */}
      <div className="layout-left">
        <div className="seat-map-wrapper">
          <SeatMap 
            selectedSeatId={selectedSeat} 
            bookedSeats={occupiedSeats} 
            onSelectSeat={(id) => setSelectedSeat(selectedSeat === id ? null : id)} 
          />
        </div>
      </div>

      {/* ฝั่งขวา */}
      <div className="layout-right">
        
        {/* กล่องสีกรม */}
        <div style={{ 
            backgroundColor: '#2c3e50', 
            color: 'white', 
            padding: '20px', 
            borderRadius: '10px', 
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
            {/* ข้อความ "วันที่จอง" ริมซ้าย */}
            <div style={{ fontSize: '0.95rem', opacity: 0.8, marginBottom: '5px', textAlign: 'left', width: '100%' }}>
                วันที่จอง
            </div>

            {/* 👉 3. เรียกใช้งานปฏิทินตัวใหม่ */}
            <DatePicker
              selected={selectedDate}
              onChange={(date) => {
                setSelectedDate(date);
                setSelectedSeat(null);
              }}
              minDate={new Date()} // ล็อคไม่ให้จองวันในอดีต
              filterDate={isNotSunday} // 👈 หัวใจสำคัญ: ทำให้วันอาทิตย์เป็นสีเทา กดไม่ได้!
              customInput={<CustomDateInput />} // ใส่ดีไซน์ดั้งเดิมของเราครอบทับเข้าไป
              dateFormat="yyyy-MM-dd"
            />
        </div>

        <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #4CAF50', paddingBottom: '10px', marginTop: '0' }}>
          รายละเอียดการจอง
        </h2>

        {/* ตัวเลือกเวลา */}
        <TimeSelector 
          startTime={startTime}
          endTime={endTime}
          allTimeSlots={allTimeSlots}
          onChangeStart={handleStartTimeChange}
          onChangeEnd={(val) => { setEndTime(val); setSelectedSeat(null); }}
        />

        {/* เงื่อนไขการแสดงฟอร์ม */}
        {selectedSeat && endTime ? (
          <ReservationForm 
            selectedSeat={selectedSeat}
            startTime={startTime}
            displayEndTime={getDisplayEndTime(endTime)}
            onConfirm={handleConfirmReservation}
          />
        ) : (
          !selectedSeat && (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#aaa', textAlign: 'center', border: '2px dashed #eee', borderRadius: '12px', marginTop: '20px', padding: '20px' }}>
               <div style={{ fontSize: '40px', marginBottom: '10px' }}>👈</div>
               <div>
                  เลือกเวลาที่ต้องการ<br/>
                  และคลิกที่นั่งฝั่ง{window.innerWidth > 768 ? 'ซ้าย' : 'บน'}
               </div>
             </div>
          )
        )}
      </div>
    </div>
  );
}

export default App;