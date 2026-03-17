import { RiComputerFill, RiUserFill } from "react-icons/ri"; 
import '../styles/App.css'; 

const Seat = ({ seatNumber, isSelected, isBooked, isLocked, onClick }) => {
  let iconColor = "#555"; 
  if (isBooked) iconColor = "#ef4444";     
  else if (isSelected) iconColor = "#4CAF50"; 
  else if (isLocked) iconColor = "#facc15"; 

  // เช็กว่าโดนจอง หรือมีคนกำลังกดอยู่ (สีเหลือง) จะกดไม่ได้
  const isDisabled = isBooked || isLocked;

  return (
    <div 
      className="seat-item"
      onClick={isDisabled ? null : onClick} 
      style={{ 
        cursor: isDisabled ? 'not-allowed' : 'pointer', 
        opacity: isBooked ? 0.6 : 1,
        transition: 'transform 0.2s',
        animation: isLocked ? 'pulse 2s infinite' : 'none' // แอนิเมชันกระพริบเบาๆ (ถ้าอยากใส่เพิ่มใน css)
      }}
      onMouseEnter={(e) => !isDisabled && (e.currentTarget.style.transform = 'scale(1.1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      {(isBooked || isSelected || isLocked) ? (
        <RiUserFill className="seat-icon" color={iconColor} /> 
      ) : (
        <RiComputerFill className="seat-icon" color={iconColor} /> 
      )}
      <div className="seat-number">{seatNumber}</div>
    </div>
  );
};

const SeatMap = ({ onSelectSeat, selectedSeatId, bookedSeats = [], lockedSeats = [], selectedDate, startTime }) => {
  const seats = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, number: i + 1 }));
  
  const leftSideSeats = seats.filter(seat => (seat.id - 1) % 6 < 3);
  const rightSideSeats = seats.filter(seat => (seat.id - 1) % 6 >= 3);

  const renderSeat = (seat) => {
    const isBooked = bookedSeats.some(booked => String(booked) === String(seat.number));
    
    const dateStr = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
    const seatKey = `${dateStr}_${startTime}_Seat${seat.number}`;
    
    // เช็กว่าโต๊ะนี้อยู่ในรายการ lockedSeats ไหม และต้องไม่ใช่โต๊ะที่เราเลือกอยู่เอง
    const isLocked = lockedSeats.includes(seatKey) && String(selectedSeatId) !== String(seat.number);
    
    return (
      <Seat 
        key={seat.id} 
        seatNumber={seat.number} 
        isBooked={isBooked} 
        isLocked={isLocked} 
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
    </div>
  );
}

export default SeatMap;