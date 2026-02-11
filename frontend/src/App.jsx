// src/App.jsx
import { useState, useMemo, useEffect } from 'react';
import SeatMap from './components/SeatMap';
import ReservationForm from './components/ReservationForm';
import TimeSelector from './components/TimeSelector';
import './styles/App.css'; // สำคัญ: ต้อง Import CSS ที่เราเพิ่งแก้

function App() {
  // --- 1. State Management (ส่วนจัดการข้อมูล) ---
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [startTime, setStartTime] = useState("08:30");
  const [endTime, setEndTime] = useState("09:30"); 
  
  // State สำหรับนาฬิกา
  const [now, setNow] = useState(new Date());

  // --- 2. Logic & Effects (ส่วนการทำงาน) ---

  // นาฬิกาเดินทุก 1 วินาที
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // แปลงวันที่และเวลาเป็นภาษาไทย
  const dateStr = now.toLocaleDateString('th-TH', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  });
  const timeStr = now.toLocaleTimeString('th-TH');

  // ข้อมูลช่วงเวลาทั้งหมด
  const allTimeSlots = [ "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00" ];

  // ข้อมูลจำลองการจอง (ถ้ามี)
  const mockBookings = { };

  // ฟังก์ชันคำนวณเวลาสิ้นสุดให้สวยงาม
  const getDisplayEndTime = (time) => {
    if (!time) return "";
    const [hourStr, minStr] = time.split(":");
    let hour = parseInt(hourStr);
    let min = parseInt(minStr);
    if (min === 0) { hour -= 1; min = 59; } 
    else if (min === 30) { min = 29; }
    return `${hour.toString().padStart(2, '0')}:${min}`;
  };

  // คำนวณที่นั่งที่ไม่ว่างในช่วงเวลาที่เลือก
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

  // เมื่อเปลี่ยนเวลาเริ่ม
  const handleStartTimeChange = (newStart) => {
    setStartTime(newStart);
    const startIndex = allTimeSlots.indexOf(newStart);
    const nextSlot = allTimeSlots[startIndex + 1];
    if (nextSlot) setEndTime(nextSlot); else setEndTime("");
    setSelectedSeat(null); // รีเซ็ตการเลือกที่นั่ง
  };

  // เมื่อกดยืนยันการจอง
  const handleConfirmReservation = (data) => {
    alert(`ยืนยันการจอง!\n\nโต๊ะ: ${selectedSeat}\nเวลา: ${startTime} - ${getDisplayEndTime(endTime)}\nชื่อ: ${data.firstName} ${data.lastname}\nสาขา: ${data.major}\nวัตถุประสงค์: ${data.purpose}`);
  };

  // --- 3. Render (ส่วนแสดงผล) ---
  return (
    <div className="main-layout">
      
      {/* ฝั่งซ้าย (คอม) หรือ บน (มือถือ): ผังที่นั่ง */}
      <div className="layout-left">
        {/* Wrapper นี้สำคัญมาก! ช่วยสร้างกรอบขาวและจัดกึ่งกลาง */}
        <div className="seat-map-wrapper">
          <SeatMap 
            selectedSeatId={selectedSeat} 
            bookedSeats={occupiedSeats} 
            onSelectSeat={(id) => setSelectedSeat(selectedSeat === id ? null : id)} 
          />
        </div>
      </div>

      {/* ฝั่งขวา (คอม) หรือ ล่าง (มือถือ): ฟอร์มข้อมูล */}
      <div className="layout-right">
        
        {/* การ์ดแสดงเวลา */}
        <div style={{ 
            backgroundColor: '#2c3e50', 
            color: 'white', 
            padding: '15px', 
            borderRadius: '10px', 
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
            <div style={{ fontSize: '0.9rem', opacity: 0.9, marginBottom: '5px' }}>
                {dateStr}
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', letterSpacing: '2px', lineHeight: '1' }}>
                {timeStr}
            </div>
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
               <div style={{ fontSize: '40px', marginBottom: '10px' }}></div>
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