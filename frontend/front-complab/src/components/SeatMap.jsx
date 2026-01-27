import { RiComputerFill, RiUserFill } from "react-icons/ri"; 

const Seat = ({ seatNumber, isSelected, isBooked, onClick }) => {
  const ICON_SIZE = 50; 
  let iconColor = "#555"; 
  if (isBooked) iconColor = "#ef4444";     
  else if (isSelected) iconColor = "#4CAF50"; 

  return (
    <div 
      onClick={isBooked ? null : onClick} 
      style={{ 
        cursor: isBooked ? 'not-allowed' : 'pointer', 
        margin: '10px', 
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '60px',
        opacity: isBooked ? 0.6 : 1, 
        transition: 'transform 0.2s'
      }}
      onMouseEnter={(e) => !isBooked && (e.currentTarget.style.transform = 'scale(1.1)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      {(isBooked || isSelected) ? (
        <RiUserFill size={ICON_SIZE} color={iconColor} /> 
      ) : (
        <RiComputerFill size={ICON_SIZE} color={iconColor} /> 
      )}
      <div style={{ marginTop: '5px', fontSize: '20px', fontWeight: 'bold', color: '#333' }}>
        {seatNumber} 
      </div>
    </div>
  );
};

const SeatMap = ({ onSelectSeat, selectedSeatId, bookedSeats = [] }) => {
  const seats = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, number: `${i + 1}` }));
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
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', width: '100%', backgroundColor: '#f0f2f5' }}>
      <h2 style={{ margin: '0 0 10px 0', color: '#333' }}>ผังห้องปฏิบัติการคอมพิวเตอร์ B4-302</h2>
      <div style={{ marginBottom: '40px', padding: '5px 25px', backgroundColor: '#333', color: 'white', borderRadius: '20px', fontSize: '0.9rem' }}>
        กระดานหน้าชั้นเรียน / จอโปรเจคเตอร์
      </div>
      <div style={{ display: 'flex', gap: '100px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
          {leftSideSeats.map(renderSeat)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
          {rightSideSeats.map(renderSeat)}
        </div>
      </div>
    </div>
  );
}

export default SeatMap;