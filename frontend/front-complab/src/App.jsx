// src/App.jsx
import { useState, useMemo, useEffect } from 'react'; // ✅ เพิ่ม useEffect
import SeatMap from './components/SeatMap';
import ReservationForm from './components/ReservationForm';
import TimeSelector from './components/TimeSelector';
import { RiTimeFill, RiCalendarTodoFill } from "react-icons/ri"; // ✅ (Optional) เพิ่มไอคอนถ้าต้องการ
import './styles/App.css'; 

function App() {
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [startTime, setStartTime] = useState("08:30");
  const [endTime, setEndTime] = useState("09:30"); 

  // ✅ 1. เพิ่ม State สำหรับนาฬิกา
  const [now, setNow] = useState(new Date());

  // ✅ 2. สั่งให้นาฬิกาเดินทุก 1 วินาที
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => clearInterval(timer); // ล้าง timer เมื่อปิดหน้าเว็บ
  }, []);

  // แปลงวันที่เป็นภาษาไทย
  const dateStr = now.toLocaleDateString('th-TH', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  });
  const timeStr = now.toLocaleTimeString('th-TH');


  const allTimeSlots = [ "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00" ];

  const mockBookings = {
    "08:30": ["1", "2"], "09:00": ["1", "2", "5"], "09:30": ["1", "8"], "10:00": ["10", "11"], "13:00": ["20", "21"], "18:00": ["29", "30"]
  };

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
    alert(`ยืนยันการจอง!\n\nโต๊ะ: ${selectedSeat}\nเวลา: ${startTime} - ${getDisplayEndTime(endTime)}\nชื่อ: ${data.name}\nคณะ: ${data.faculty}\nสาขา: ${data.major}`);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      
      {/* ฝั่งซ้าย */}
      <div style={{ flex: 7, position: 'relative' }}>
        <SeatMap 
          selectedSeatId={selectedSeat} 
          bookedSeats={occupiedSeats} 
          onSelectSeat={(id) => setSelectedSeat(selectedSeat === id ? null : id)} 
        />
      </div>

      {/* ฝั่งขวา */}
      <div style={{ flex: 3, padding: '30px', backgroundColor: 'white', boxShadow: '-5px 0 15px rgba(0,0,0,0.05)', zIndex: 10, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        
        {/* ✅ 3. ส่วนแสดงวันที่และเวลา (อยู่บนสุด) */}
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

        <TimeSelector 
          startTime={startTime}
          endTime={endTime}
          allTimeSlots={allTimeSlots}
          onChangeStart={handleStartTimeChange}
          onChangeEnd={(val) => { setEndTime(val); setSelectedSeat(null); }}
        />

        {selectedSeat && endTime ? (
          <ReservationForm 
            selectedSeat={selectedSeat}
            startTime={startTime}
            displayEndTime={getDisplayEndTime(endTime)}
            onConfirm={handleConfirmReservation}
          />
        ) : (
          !selectedSeat && (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#aaa', textAlign: 'center', border: '2px dashed #eee', borderRadius: '12px', marginTop: '20px' }}>
               <div style={{ fontSize: '40px', marginBottom: '10px' }}>👈</div>
               <div>เลือกเวลาที่ต้องการ<br/>และคลิกที่นั่งฝั่งซ้าย</div>
             </div>
          )
        )}
      </div>
    </div>
  )
}

export default App;