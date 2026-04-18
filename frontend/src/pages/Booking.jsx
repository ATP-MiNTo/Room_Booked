import { useState, useEffect, forwardRef } from 'react';
import { useNavigate } from 'react-router-dom'; 
import { RiCalendarEventFill, RiSettings3Fill } from 'react-icons/ri'; 
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import Swal from 'sweetalert2'; 

import SeatMap from '../components/SeatMap';
import ReservationForm from '../components/ReservationForm';
import TimeSelector from '../components/TimeSelector';
import FaceScanner from '../components/FaceScanner'; 
import '../styles/App.css'; 
import { BOOKING_TIME_SLOTS, pad } from '../utils/dateUtils';

const getInitialTimeSlots = (timeSlots) => {
  const now = new Date();
  let h = now.getHours();
  let m = now.getMinutes() < 30 ? 0 : 30;

  const timeStr = `${pad(h)}:${pad(m)}`;
  const idx = timeSlots.indexOf(timeStr);

  if (idx !== -1 && idx < timeSlots.length - 1) {
    return { start: timeSlots[idx], end: timeSlots[idx + 1] };
  }
  return { start: timeSlots[0], end: timeSlots[1] };
};

function Booking() {
  const navigate = useNavigate(); 

  const [selectedSeat, setSelectedSeat] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date()); 
  
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState(''); 
  
  const [showScanner, setShowScanner] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [tempData, setTempData] = useState(null);
  const [capturedImageBase64, setCapturedImageBase64] = useState(null);
  const [seatStatuses, setSeatStatuses] = useState({});

  useEffect(() => {
    const initTimes = getInitialTimeSlots(BOOKING_TIME_SLOTS);
    setStartTime(initTimes.start);
    setEndTime(initTimes.end);
  }, []);

  const formatThaiDate = (dateObj) => {
    if (!dateObj) return "";
    return dateObj.toLocaleDateString('th-TH', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  };

  const getDisplayEndTime = (time) => {
    if (!time) return "";
    const [hourStr, minStr] = time.split(":");
    let hour = parseInt(hourStr);
    let min = parseInt(minStr);
    if (min === 0) { hour -= 1; min = 59; } 
    else if (min === 30) { min = 29; }
    return `${pad(hour)}:${pad(min)}`;
  };

  useEffect(() => {
    if (startTime && endTime && selectedDate) {
      const fetchBookedSeats = async () => {
        try {
          const dateStr = `${selectedDate.getFullYear()}-${pad(selectedDate.getMonth() + 1)}-${pad(selectedDate.getDate())}`;
          const response = await fetch(`/booked-seats?reserve_date=${dateStr}&start_time=${startTime}&end_time=${endTime}`);
          if (response.ok) setSeatStatuses(await response.json());
        } catch (error) {
          console.error("Error fetching seats:", error);
        }
      };
      fetchBookedSeats();
    }
  }, [selectedDate, startTime, endTime]);

  const handleStartTimeChange = (newStart) => {
    setStartTime(newStart);
    const startIndex = BOOKING_TIME_SLOTS.indexOf(newStart);
    const nextSlot = BOOKING_TIME_SLOTS[startIndex + 1];
    if (nextSlot) setEndTime(nextSlot); else setEndTime("");
    setSelectedSeat(null); 
  };

  const handleConfirmReservation = (data) => {
    setTempData(data);
    setShowScanner(true); 
  };

  const handleScanComplete = (imageSrc) => {
    setCapturedImageBase64(imageSrc);
    setShowScanner(false); 
    setShowSummary(true);  
  };

  const handleCancelSummary = () => {
    setShowSummary(false);
    setSelectedSeat(null); 
  };

  const handleFinalSubmit = async () => {
    try {
        const res = await fetch(capturedImageBase64);
        const imageBlob = await res.blob();

        const formData = new FormData();
        formData.append("seat_id", selectedSeat);
        formData.append("student_id", tempData.studentId);
        formData.append("user_name", `${tempData.firstName} ${tempData.lastName || tempData.lastname || ''}`);
        formData.append("major", tempData.major || "ไม่ระบุ");
        
        const dateString = `${selectedDate.getFullYear()}-${pad(selectedDate.getMonth() + 1)}-${pad(selectedDate.getDate())}`;
        formData.append("reserve_date", dateString);
        formData.append("start_time", startTime);
        formData.append("end_time", endTime);
        formData.append("purpose", tempData.purpose || "ไม่ระบุ");
        formData.append("image", imageBlob, "face_capture.jpg");

        const response = await fetch("/reserve-with-image", { method: "POST", body: formData });

        if (response.ok) {
            setShowSummary(false); 
            Swal.fire({
                title: 'จองสำเร็จ!',
                text: 'บันทึกข้อมูลและรูปภาพเรียบร้อยแล้ว',
                icon: 'success',
                confirmButtonText: 'ตกลง',
                confirmButtonColor: '#4CAF50'
            }).then((result) => {
                if (result.isConfirmed) window.location.reload();
            });
        } else {
            const errorData = await response.json();
            Swal.fire({ title: 'เกิดข้อผิดพลาด', text: errorData.detail, icon: 'error', confirmButtonText: 'ตกลง', confirmButtonColor: '#d33' });
        }
    } catch (error) {
        console.error("Error saving to DB:", error);
        Swal.fire({ title: 'เชื่อมต่อล้มเหลว', text: 'ไม่สามารถติดต่อเซิร์ฟเวอร์ได้', icon: 'error', confirmButtonText: 'ตกลง', confirmButtonColor: '#d33' });
    }
  };

  const CustomDateInput = forwardRef(({ onClick, value }, ref) => (
    <div 
      onClick={onClick} ref={ref}
      style={{ width: '100%', backgroundColor: 'transparent', padding: '5px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxSizing: 'border-box', border: 'none', cursor: 'pointer', transition: 'opacity 0.2s' }}
      onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'} 
      onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
    >
      <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: 'white' }}>{formatThaiDate(selectedDate)}</div>
      <RiCalendarEventFill size={42} color="white" />
    </div>
  ));

  const isNotSunday = (date) => date.getDay() !== 0;

  return (
    <div className="main-layout">
      
      <div 
        onClick={() => navigate('/admin')}
        style={{ position: 'fixed', bottom: '20px', right: '20px', backgroundColor: 'rgba(44, 62, 80, 0.7)', color: 'white', padding: '12px', borderRadius: '50%', cursor: 'pointer', zIndex: 999, boxShadow: '0 4px 8px rgba(0,0,0,0.3)', display: 'flex', justifyContent: 'center', alignItems: 'center', transition: 'transform 0.2s, background-color 0.2s' }}
        onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.1)'; e.currentTarget.style.backgroundColor = 'rgba(44, 62, 80, 1)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.backgroundColor = 'rgba(44, 62, 80, 0.7)'; }}
        title="สำหรับเจ้าหน้าที่"
      >
        <RiSettings3Fill size={24} />
      </div>

      {showScanner && (
        <FaceScanner onScanComplete={handleScanComplete} onCancel={() => setShowScanner(false)} />
      )}

      {showSummary && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '15px', width: '350px', color: '#333', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
            <h2 style={{ marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #4CAF50', paddingBottom: '10px' }}>ตรวจสอบข้อมูล</h2>
            <div style={{ lineHeight: '1.8', fontSize: '1.05rem', marginBottom: '20px' }}>
              <div><strong>ชื่อ-สกุล:</strong> {tempData.firstName} {tempData.lastName || tempData.lastname}</div>
              <div><strong>รหัสนักศึกษา:</strong> {tempData.studentId}</div>
              <div><strong>สาขา:</strong> {tempData.major || 'ไม่ระบุ'}</div>
              <div><strong>วันที่:</strong> {formatThaiDate(selectedDate)}</div>
              <div><strong>เวลา:</strong> {startTime} - {getDisplayEndTime(endTime)}</div>
              <div><strong>โต๊ะที่:</strong> {selectedSeat}</div>
              <div style={{ color: 'green', fontSize: '0.9rem', marginTop: '10px', fontWeight: 'bold' }}>
                ✓ บันทึกภาพยืนยันตัวตนเรียบร้อย
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={handleFinalSubmit} style={{ flex: 1, padding: '12px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem' }}>
                ยืนยัน
              </button>
              <button onClick={handleCancelSummary} style={{ padding: '12px 20px', backgroundColor: '#e0e0e0', color: '#555', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
                ยกเลิก
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="layout-left">
        <div className="seat-map-wrapper">
          <SeatMap 
            selectedSeatId={selectedSeat} seatStatuses={seatStatuses}
            selectedDate={selectedDate} startTime={startTime}
            onSelectSeat={(id) => setSelectedSeat(selectedSeat === id ? null : id)} 
          />
        </div>
      </div>

      <div className="layout-right">
        <div style={{ backgroundColor: '#2c3e50', color: 'white', padding: '20px', borderRadius: '10px', marginBottom: '20px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.95rem', opacity: 0.8, marginBottom: '5px' }}>วันที่จอง</div>
          <div style={{ width: '100%', display: 'block' }}>
            <style>{`.react-datepicker-wrapper { width: 100%; display: block; }`}</style>
            <DatePicker
                selected={selectedDate}
                onChange={(date) => { setSelectedDate(date); setSelectedSeat(null); }}
                minDate={new Date()} 
                filterDate={isNotSunday}
                customInput={<CustomDateInput />}
                dateFormat="yyyy-MM-dd"
            />
          </div>
        </div>

        <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #4CAF50', paddingBottom: '10px', marginTop: '0' }}>รายละเอียดการจอง</h2>

        <TimeSelector 
          startTime={startTime} endTime={endTime} allTimeSlots={BOOKING_TIME_SLOTS}
          onChangeStart={handleStartTimeChange} 
          onChangeEnd={(val) => { setEndTime(val); setSelectedSeat(null); }}
        />

        {selectedSeat && endTime ? (
          <ReservationForm 
            selectedSeat={selectedSeat} startTime={startTime} displayEndTime={getDisplayEndTime(endTime)}
            onConfirm={handleConfirmReservation}
          />
        ) : (
          !selectedSeat && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#aaa', textAlign: 'center', border: '2px dashed #eee', borderRadius: '12px', marginTop: '20px', padding: '20px' }}>
              <div style={{ fontSize: '40px', marginBottom: '10px' }}></div>
              <div>เลือกเวลาที่ต้องการ<br/>และคลิกที่นั่งฝั่ง{window.innerWidth > 768 ? 'ซ้าย' : 'บน'}</div>
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default Booking;