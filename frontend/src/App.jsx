// src/App.jsx
import { useState, useMemo, forwardRef } from 'react';
import { RiCalendarEventFill } from 'react-icons/ri'; 
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import SeatMap from './components/SeatMap';
import ReservationForm from './components/ReservationForm';
import TimeSelector from './components/TimeSelector';
import FaceScanner from './components/FaceScanner'; // 👉 นำเข้าตัวสแกนหน้า
import './styles/App.css'; 

function App() {
  // --- 1. State Management ---
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date()); 
  const [startTime, setStartTime] = useState("08:30");
  const [endTime, setEndTime] = useState("09:30"); 
  
  // 👉 เพิ่ม State สำหรับเปิด/ปิด Popup และเก็บข้อมูลระหว่างทาง
  const [showScanner, setShowScanner] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [tempData, setTempData] = useState(null);
  const [capturedImageBase64, setCapturedImageBase64] = useState(null);

  // --- 2. Logic ---
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

  // 👉 STEP 1: กดยืนยันฟอร์ม -> เก็บข้อมูล -> เปิดสแกนหน้า
  const handleConfirmReservation = (data) => {
    setTempData(data);
    setShowScanner(true); 
  };

  // 👉 STEP 2: สแกนเสร็จ -> เก็บรูป -> เปิดหน้าต่างสรุป
  const handleScanComplete = (imageSrc) => {
    setCapturedImageBase64(imageSrc);
    setShowScanner(false); 
    setShowSummary(true);  
  };

  // 👉 STEP 3: กดยืนยันหน้าสรุป -> ยิงเข้า Database
  const handleFinalSubmit = async () => {
    try {
        // แปลงรูป Base64 เป็นไฟล์จริงๆ ก่อนส่ง
        const res = await fetch(capturedImageBase64);
        const imageBlob = await res.blob();

        const formData = new FormData();
        formData.append("seat_id", selectedSeat);
        formData.append("student_id", tempData.studentId);
        formData.append("user_name", `${tempData.firstName} ${tempData.lastname}`);
        
        // แปลงวันที่เป็น YYYY-MM-DD
        const dateString = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
        formData.append("reserve_date", dateString);
        formData.append("start_time", startTime);
        formData.append("end_time", endTime);
        formData.append("purpose", tempData.purpose || "ไม่ระบุ");
        
        // แนบไฟล์รูปลงกล่อง (ส่งเป็น .jpg)
        formData.append("image", imageBlob, "face_capture.jpg");

        // ยิงข้อมูลไปที่หลังบ้าน FastAPI
        const response = await fetch("http://localhost:8000/reserve-with-image", {
            method: "POST",
            body: formData,
        });

        if (response.ok) {
            alert("✅ บันทึกข้อมูลและรูปภาพสำเร็จ!");
            setShowSummary(false); // ปิดหน้าต่าง
            setSelectedSeat(null); // เคลียร์ที่นั่ง
            setTempData(null);
            setCapturedImageBase64(null);
        } else {
            const errorData = await response.json();
            alert(`❌ เกิดข้อผิดพลาด: ${errorData.detail}`);
        }
    } catch (error) {
        console.error("Error saving to DB:", error);
        alert("❌ ไม่สามารถติดต่อเซิร์ฟเวอร์ฐานข้อมูลได้");
    }
  };

  const CustomDateInput = forwardRef(({ onClick }, ref) => (
    <div 
      onClick={onClick}
      ref={ref}
      style={{ 
        width: '100%', backgroundColor: 'transparent', padding: '5px 0', display: 'flex', 
        justifyContent: 'space-between', alignItems: 'center', boxSizing: 'border-box',
        border: 'none', cursor: 'pointer', transition: 'opacity 0.2s'
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

  const isNotSunday = (date) => {
    const day = date.getDay();
    return day !== 0; 
  };

  // --- 3. Render ---
  return (
    <div className="main-layout">
      
      {/* 🔴 Popup 1: สแกนหน้า */}
      {showScanner && (
        <FaceScanner 
            onScanComplete={handleScanComplete} 
            onCancel={() => setShowScanner(false)} 
        />
      )}

      {/* 🟢 Popup 2: สรุปข้อมูล (ก่อนบันทึก) */}
      {showSummary && (
        <div className="summary-overlay" style={{
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999,
            display: 'flex', justifyContent: 'center', alignItems: 'center'
        }}>
            <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '15px', width: '350px', color: '#333', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
                <h2 style={{marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #4CAF50', paddingBottom: '10px'}}>ตรวจสอบข้อมูล</h2>
                
                <div style={{lineHeight: '1.8', fontSize: '1.05rem', marginBottom: '20px'}}>
                    <div><strong>ชื่อ-สกุล:</strong> {tempData.firstName} {tempData.lastname}</div>
                    <div><strong>รหัสนักศึกษา:</strong> {tempData.studentId}</div>
                    <div><strong>วันที่:</strong> {formatThaiDate(selectedDate)}</div>
                    <div><strong>เวลา:</strong> {startTime} - {getDisplayEndTime(endTime)}</div>
                    <div><strong>โต๊ะที่:</strong> {selectedSeat}</div>
                    <div style={{color: 'green', fontSize: '0.9rem', marginTop: '10px', fontWeight: 'bold'}}>
                        <span style={{marginRight: '5px'}}>✓</span> ระบบบันทึกภาพยืนยันตัวตนเรียบร้อยแล้ว
                    </div>
                </div>
                
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button onClick={handleFinalSubmit} style={{flex: 1, padding: '12px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem'}}>
                        ยืนยันการจอง
                    </button>
                    <button onClick={() => setShowSummary(false)} style={{padding: '12px 20px', backgroundColor: '#e0e0e0', color: '#555', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold'}}>
                        ยกเลิก
                    </button>
                </div>
            </div>
        </div>
      )}

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
        <div style={{ backgroundColor: '#2c3e50', color: 'white', padding: '20px', borderRadius: '10px', marginBottom: '20px', display: 'flex', flexDirection: 'column', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: '0.95rem', opacity: 0.8, marginBottom: '5px', textAlign: 'left', width: '100%' }}>วันที่จอง</div>
            <DatePicker
              selected={selectedDate}
              onChange={(date) => { setSelectedDate(date); setSelectedSeat(null); }}
              minDate={new Date()} 
              filterDate={isNotSunday} 
              customInput={<CustomDateInput />} 
              dateFormat="yyyy-MM-dd"
            />
        </div>

        <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #4CAF50', paddingBottom: '10px', marginTop: '0' }}>รายละเอียดการจอง</h2>

        <TimeSelector 
          startTime={startTime} endTime={endTime} allTimeSlots={allTimeSlots}
          onChangeStart={handleStartTimeChange} onChangeEnd={(val) => { setEndTime(val); setSelectedSeat(null); }}
        />

        {selectedSeat && endTime ? (
          <ReservationForm 
            selectedSeat={selectedSeat} startTime={startTime} displayEndTime={getDisplayEndTime(endTime)}
            onConfirm={handleConfirmReservation} // 👉 ผูกเข้ากับการเปิดกล้อง
          />
        ) : (
          !selectedSeat && (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#aaa', textAlign: 'center', border: '2px dashed #eee', borderRadius: '12px', marginTop: '20px', padding: '20px' }}>
               <div style={{ fontSize: '40px', marginBottom: '10px' }}>👈</div>
               <div>เลือกเวลาที่ต้องการ<br/>และคลิกที่นั่งฝั่ง{window.innerWidth > 768 ? 'ซ้าย' : 'บน'}</div>
             </div>
          )
        )}
      </div>
    </div>
  );
}

export default App;