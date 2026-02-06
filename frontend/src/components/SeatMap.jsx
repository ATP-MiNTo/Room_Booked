// src/components/SeatMap.jsx
import { RiComputerFill, RiUserFill } from "react-icons/ri"; 
import '../styles/App.css'; 

const Seat = ({ seatNumber, isSelected, isBooked, onClick }) => {
  let iconColor = "#555"; 
  if (isBooked) iconColor = "#ef4444";     
  else if (isSelected) iconColor = "#4CAF50"; 

  return (
    <div 
      className="seat-item"
      onClick={isBooked ? null : onClick} 
      style={{ 
        cursor: isBooked ? 'not-allowed' : 'pointer', 
        opacity: isBooked ? 0.6 : 1,
        transition: 'transform 0.2s'
      }}
      onMouseEnter={(e) => !isBooked && (e.currentTarget.style.transform = 'scale(1.1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      {(isBooked || isSelected) ? (
        <RiUserFill className="seat-icon" color={iconColor} /> 
      ) : (
        <RiComputerFill className="seat-icon" color={iconColor} /> 
      )}
      <div className="seat-number">{seatNumber}</div>
    </div>
  );
};

const SeatMap = ({ onSelectSeat, selectedSeatId, bookedSeats = [] }) => {
  const seats = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, number: `${i + 1}` }));
  
  // แบ่งซ้าย-ขวา
  const leftSideSeats = seats.filter(seat => (seat.id - 1) % 6 < 3);
  const rightSideSeats = seats.filter(seat => (seat.id - 1) % 6 >= 3);

  const renderSeat = (seat) => {
    const isBooked = bookedSeats.includes(seat.number);
    return (
      <Seat 
        key={seat.id} 
        seatNumber={seat.number} 
        isBooked={isBooked} 
        isSelected={selectedSeatId === seat.number}
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
      
      {/* Wrapper นี้จะเป็นตัวจัดการช่องว่างตรงกลาง */}
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