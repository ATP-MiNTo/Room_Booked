import { RiComputerFill, RiUserFill, RiCheckboxCircleFill } from "react-icons/ri"; // 👈 เพิ่ม RiCheckboxCircleFill เข้ามา
import '../styles/App.css'; 

const Seat = ({ seatNumber, isSelected, isBooked, onClick }) => {
  const isDisabled = isBooked;

  // 🟢 จัดการสัญลักษณ์และสีตามสถานะ
  let IconComponent = RiComputerFill; // ค่าเริ่มต้น (ว่าง)
  let iconColor = "#555"; 

  if (isBooked) {
    IconComponent = RiUserFill;       // จองแล้ว (รูปคน)
    iconColor = "#ef4444";
  } else if (isSelected) {
    IconComponent = RiCheckboxCircleFill; // กำลังเลือก (รูปติ๊กถูก)
    iconColor = "#4CAF50";
  }

  return (
    <div 
      className="seat-item"
      onClick={isDisabled ? null : onClick} 
      style={{ 
        cursor: isDisabled ? 'not-allowed' : 'pointer', 
        opacity: isBooked ? 0.6 : 1,
        transition: 'transform 0.2s'
      }}
      onMouseEnter={(e) => !isDisabled && (e.currentTarget.style.transform = 'scale(1.1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      {/* เรียกใช้ Icon ที่ถูกเลือก */}
      <IconComponent className="seat-icon" color={iconColor} /> 
      <div className="seat-number">{seatNumber}</div>
    </div>
  );
};

const SeatMap = ({ onSelectSeat, selectedSeatId, bookedSeats = [] }) => {
  const seats = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, number: i + 1 }));
  
  const leftSideSeats = seats.filter(seat => (seat.id - 1) % 6 < 3);
  const rightSideSeats = seats.filter(seat => (seat.id - 1) % 6 >= 3);

  const renderSeat = (seat) => {
    const isBooked = bookedSeats.some(booked => String(booked) === String(seat.number));
    
    return (
      <Seat 
        key={seat.id} 
        seatNumber={seat.number} 
        isBooked={isBooked} 
        isSelected={String(selectedSeatId) === String(seat.number)} 
        onClick={() => onSelectSeat(seat.number)}
      />
    );
  };

  return (
    <div className="seat-map-container">
      <h2 style={{ margin: '0 0 15px 0', color: '#333', textAlign: 'center', fontSize: '1.2rem' }}>
        ผังห้องปฏิบัติการคอมพิวเตอร์ B4-302
      </h2>
      
      <div className="screen-label">
        กระดานหน้าชั้นเรียน / จอโปรเจคเตอร์
      </div>
      
      <div className="banks-wrapper">
        <div className="seat-bank">
          {leftSideSeats.map(renderSeat)}
        </div>
        <div className="seat-bank">
          {rightSideSeats.map(renderSeat)}
        </div>
      </div>

      {/* โซนคำอธิบายสัญลักษณ์ (อัปเดตไอคอนใหม่ให้ตรงกัน) */}
      <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '15px', 
          marginTop: '25px', 
          flexWrap: 'wrap',
          padding: '15px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #eee'
      }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiComputerFill color="#555" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>ว่าง</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiCheckboxCircleFill color="#4CAF50" size={20} /> {/* 👈 เปลี่ยนไอคอนตรงนี้ */}
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>กำลังเลือก</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiUserFill color="#ef4444" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>จองแล้ว</span>
          </div>
      </div>

    </div>
  );
}

export default SeatMap;