import { RiComputerFill, RiUserFill, RiCheckboxCircleFill, RiLockFill, RiToolsFill } from "react-icons/ri"; 
import '../styles/App.css'; 

// เปลี่ยนมารับ statusData แทน isBooked เพื่อให้รู้ว่าทำไมถึงถูกล็อก
const Seat = ({ seatNumber, isSelected, statusData, onClick }) => {
  const isDisabled = !!statusData; // ถ้ามีข้อมูลแปลว่าถูกล็อก/จอง/เสีย

  // จัดการสัญลักษณ์และสีตามหน้าตาแบบดั้งเดิม
  let IconComponent = RiComputerFill; // ค่าเริ่มต้น (ว่าง)
  let iconColor = "#555"; 
  let tooltip = `โต๊ะหมายเลข ${seatNumber} (พร้อมใช้งาน)`;

  if (statusData) {
    if (statusData.status === 'booked') {
      IconComponent = RiUserFill;       // จองแล้ว (รูปคน)
      iconColor = "#ef4444";
      tooltip = `โต๊ะ ${seatNumber}: ${statusData.reason}`;
    } else if (statusData.status === 'locked') {
      IconComponent = RiLockFill;       // ติดเรียน (แม่กุญแจ)
      iconColor = "#9333ea";
      tooltip = `โต๊ะ ${seatNumber}: ${statusData.reason}`;
    } else if (statusData.status === 'broken') {
      IconComponent = RiToolsFill;      // แจ้งซ่อม (ประแจ)
      iconColor = "#9e9e9e";
      tooltip = `โต๊ะ ${seatNumber}: ${statusData.reason}`;
    }
  } else if (isSelected) {
    IconComponent = RiCheckboxCircleFill; // กำลังเลือก (รูปติ๊กถูก)
    iconColor = "#4CAF50";
    tooltip = `กำลังเลือกโต๊ะ ${seatNumber}`;
  }

  return (
    <div 
      className="seat-item"
      title={tooltip} // เพิ่ม Tooltip เพื่อโชว์ข้อความตอนเอาเมาส์ชี้
      onClick={isDisabled ? null : onClick} 
      style={{ 
        cursor: isDisabled ? 'not-allowed' : 'pointer', 
        opacity: isDisabled ? 0.6 : 1,
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

// เปลี่ยนมารับ seatStatuses (Object) แทน bookedSeats (Array) ให้ตรงกับหน้า Booking.jsx
const SeatMap = ({ onSelectSeat, selectedSeatId, seatStatuses = {} }) => {
  const seats = Array.from({ length: 30 }, (_, i) => ({ id: i + 1, number: i + 1 }));
  
  const leftSideSeats = seats.filter(seat => (seat.id - 1) % 6 < 3);
  const rightSideSeats = seats.filter(seat => (seat.id - 1) % 6 >= 3);

  const renderSeat = (seat) => {
    const statusData = seatStatuses[String(seat.number)];
    
    return (
      <Seat 
        key={seat.id} 
        seatNumber={seat.number} 
        statusData={statusData} // ส่ง statusData เข้าไป
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

      {/* โซนคำอธิบายสัญลักษณ์ (อัปเดตไอคอนใหม่ให้ตรงกันและครบทุกสถานะ) */}
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
              <RiCheckboxCircleFill color="#4CAF50" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>กำลังเลือก</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiUserFill color="#ef4444" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>จองแล้ว</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiLockFill color="#9333ea" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>ติดเรียน/ล็อก</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RiToolsFill color="#9e9e9e" size={20} /> 
              <span style={{fontSize: '0.85rem', color: '#555', fontWeight: 'bold'}}>แจ้งซ่อม</span>
          </div>
      </div>

    </div>
  );
}

export default SeatMap;