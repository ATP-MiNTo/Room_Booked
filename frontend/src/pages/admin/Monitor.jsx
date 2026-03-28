import { useState, useEffect } from 'react';
import { 
  RiComputerFill, RiUserFill, RiCloseLine, 
  RiTimerFill, RiUserForbidFill, RiToolsFill 
} from 'react-icons/ri';
import AdminLayout from './AdminLayout';

export default function Monitor() {
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  const [dbBookings, setDbBookings] = useState([]);
  const [cameraData, setCameraData] = useState([]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 📡 ดึงข้อมูลการจองของจริงจาก Database (ดึงทุก 1 นาที)
  useEffect(() => {
    const fetchBookings = async () => {
      try {
        const response = await fetch('/reservations'); 
        if (response.ok) {
          const data = await response.json();
          setDbBookings(data);
        }
      } catch (error) {
        console.error("Error fetching bookings:", error);
      }
    };
    
    fetchBookings();
    const interval = setInterval(fetchBookings, 60000); 
    return () => clearInterval(interval);
  }, []);

  // 🎥 ดึงข้อมูลกล้องผ่าน WebSocket ของจริง
  useEffect(() => {
    // ⚠️ ถ้าเพื่อนรันกล้องอยู่อีกเครื่อง ต้องเปลี่ยน localhost เป็น IP ของเพื่อนนะครับ
    const wsUrl = 'ws://localhost:8000/ws/pc-updates'; 
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setCameraData(data);
      } catch (error) {
        console.error("Error parsing camera data:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket Camera Error:", error);
    };

    return () => ws.close();
  }, []);

  // 🧠 ฟังก์ชันคำนวณสถานะ (เอา DB ชนกับ กล้อง)
  const getSeatData = (seatNumber) => {
    const camInfo = cameraData.find(pc => pc.pc_name === `PC${seatNumber}`) || { available: 0, pc_on: false };
    const isSitting = camInfo.available > 0; 
    const isPcOn = camInfo.pc_on; 

    const now = new Date();
    const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    
    const activeBooking = dbBookings.find(b => 
      String(b.seat_id) === String(seatNumber) && 
      b.start_time <= currentTimeStr && 
      b.end_time >= currentTimeStr
    );

    let finalStatus = 'unbooked_empty';

    if (activeBooking && isSitting) {
        finalStatus = 'booked_occupied'; 
    } else if (activeBooking && !isSitting) {
        finalStatus = 'booked_empty';    
    } else if (!activeBooking && isSitting) {
        finalStatus = 'unbooked_occupied'; 
    }

    return {
        number: seatNumber,
        status: finalStatus,
        available: camInfo.available,
        pc_on: isPcOn,
        studentName: activeBooking ? `นักศึกษา (${activeBooking.student_id})` : null, 
        studentId: activeBooking?.student_id || null,
        time: activeBooking ? `${activeBooking.start_time} - ${activeBooking.end_time}` : null,
        image: activeBooking ? `/data/face_scanner/${activeBooking.image_filename}` : null
    };
  };

  const size = {
    seat: isMobile ? '45px' : '85px',          
    gapWrapper: isMobile ? '20px' : '70px',    
    gapGrid: isMobile ? '10px' : '20px',       
    icon: isMobile ? 22 : 42,                  
    fontSize: isMobile ? '11px' : '16px',      
    containerPadding: isMobile ? '15px' : '40px', 
  };

  const Seat = ({ seatNumber }) => {
    const seatData = getSeatData(seatNumber); 
    const isSelected = selectedSeat?.number === seatNumber;
    
    let iconColor = "#555"; 
    let IconComponent = RiComputerFill;

    if (seatData.status === 'booked_occupied') {
        iconColor = "#4CAF50"; 
        IconComponent = RiUserFill; 
    } else if (seatData.status === 'booked_empty') {
        iconColor = "#facc15"; 
        IconComponent = RiTimerFill; 
    } else if (seatData.status === 'unbooked_occupied') {
        iconColor = "#ef4444"; 
        IconComponent = RiUserForbidFill; 
    } else if (seatData.status === 'broken') {
        iconColor = "#9e9e9e"; 
        IconComponent = RiToolsFill; 
    }

    return (
      <div 
        onClick={() => setSelectedSeat({ number: seatNumber, ...seatData })}
        style={{
            width: size.seat, height: size.seat, 
            backgroundColor: isSelected ? 'rgba(22, 119, 255, 0.1)' : 'white',
            border: isSelected ? '2px solid #1677ff' : '2px solid #eee',
            borderRadius: '12px', display: 'flex', flexDirection: 'column', 
            justifyContent: 'center', alignItems: 'center', cursor: 'pointer',
            transition: 'transform 0.2s', boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
            position: 'relative'
        }}
        onMouseEnter={(e) => !isMobile && (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={(e) => !isMobile && (e.currentTarget.style.transform = 'scale(1)')}
      >
        <IconComponent size={size.icon} color={iconColor} />
        <div style={{ fontSize: size.fontSize, marginTop: '4px', fontWeight: 'bold', color: '#555' }}>{seatNumber}</div>

        <div style={{
          position: 'absolute', top: '8px', right: '8px',
          width: '12px', height: '12px', borderRadius: '50%',
          backgroundColor: seatData.pc_on ? '#4CAF50' : '#ccc',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          border: '2px solid white'
        }} title={seatData.pc_on ? 'หน้าจอเปิดอยู่' : 'หน้าจอปิด'} />
      </div>
    );
  };

  const seats = Array.from({ length: 30 }, (_, i) => i + 1);
  const leftSideSeats = seats.filter(num => (num - 1) % 6 < 3);
  const rightSideSeats = seats.filter(num => (num - 1) % 6 >= 3);

  const getStatusDetails = (status) => {
      switch(status) {
          case 'booked_occupied': return { text: 'จองแล้ว และ มีคนนั่ง', color: '#4CAF50', tag: 'ปกติ' };
          case 'booked_empty': return { text: 'จองแล้ว แต่ ไม่มีคนนั่ง', color: '#facc15', tag: 'อาจมาสาย' };
          case 'unbooked_occupied': return { text: 'ไม่ได้จอง แต่ มีคนนั่ง', color: '#ef4444', tag: 'ผิดปกติ' };
          case 'broken': return { text: 'เครื่องเสีย / งดใช้งาน', color: '#9e9e9e', tag: 'แจ้งซ่อม' };
          default: return { text: 'ว่าง', color: '#555', tag: 'พร้อมใช้งาน' };
      }
  };

  return (
    <AdminLayout>
      <div style={{ position: 'relative', display: 'flex', height: '100%', overflow: 'hidden' }}>
        
        <div style={{ flex: 1, padding: isMobile ? '10px' : '30px', overflowY: 'auto', width: '100%' }}>
            <h2 style={{ marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '15px', fontSize: isMobile ? '1.1rem' : '1.5rem', maxWidth: '950px', margin: '0 auto 25px' }}>
                Live Monitor (สถานะห้องแล็บ B4-302)
            </h2>

            <div style={{ backgroundColor: 'white', padding: size.containerPadding, borderRadius: '15px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', maxWidth: isMobile ? '100%' : '950px', margin: '0 auto', overflowX: 'auto' }}>
                <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#f0f2f5', borderRadius: '8px', marginBottom: isMobile ? '20px' : '35px', minWidth: isMobile ? '360px' : 'auto', fontWeight: 'bold', color: '#666', fontSize: isMobile ? '0.9rem' : '1.1rem' }}>
                    กระดานหน้าชั้นเรียน / จอโปรเจคเตอร์
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'center', gap: size.gapWrapper, minWidth: isMobile ? '360px' : 'auto', paddingBottom: isMobile ? '10px' : '0' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: size.gapGrid }}>
                        {leftSideSeats.map(num => <Seat key={num} seatNumber={num} />)}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: size.gapGrid }}>
                        {rightSideSeats.map(num => <Seat key={num} seatNumber={num} />)}
                    </div>
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', gap: isMobile ? '10px' : '25px', marginTop: '25px', flexWrap: 'wrap', backgroundColor: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', maxWidth: isMobile ? '100%' : '950px', margin: '25px auto 50px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserFill color="#4CAF50" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>จอง&นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiTimerFill color="#facc15" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>จอง&ไม่นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserForbidFill color="#ef4444" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>ไม่จอง&นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiComputerFill color="#555" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>ว่าง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ display: 'inline-block', width: '12px', height: '12px', backgroundColor: '#4CAF50', borderRadius: '50%', border: '2px solid #ddd' }}></span>
                    <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>หน้าจอเปิด</span>
                </div>
            </div>
        </div>

        {selectedSeat && (
            <div 
                onClick={() => setSelectedSeat(null)}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 999 }}
            />
        )}

        <div style={{ 
            position: 'fixed', top: 0, right: selectedSeat ? 0 : '-420px', 
            width: '100%', maxWidth: '400px', height: '100%', backgroundColor: 'white',
            boxShadow: '-5px 0 25px rgba(0,0,0,0.15)', transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            display: 'flex', flexDirection: 'column', borderLeft: '1px solid #eee',
            zIndex: 1000 
        }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#f8f9fa' }}>
                <h3 style={{ margin: 0, color: '#2c3e50' }}>ข้อมูลที่นั่ง {selectedSeat?.number}</h3>
                <div onClick={() => setSelectedSeat(null)} style={{ cursor: 'pointer', backgroundColor: '#eee', padding: '5px', borderRadius: '50%', display: 'flex' }}>
                    <RiCloseLine size={24} color="#666" />
                </div>
            </div>

            {selectedSeat && (
                <div style={{ padding: '25px', overflowY: 'auto', flex: 1 }}>
                    
                    <div style={{ backgroundColor: getStatusDetails(selectedSeat.status).color + '15', color: getStatusDetails(selectedSeat.status).color, padding: '15px', borderRadius: '10px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '25px', border: `2px solid ${getStatusDetails(selectedSeat.status).color}50`, fontSize: '1.1rem' }}>
                        {getStatusDetails(selectedSeat.status).text}
                    </div>

                    {(selectedSeat.status === 'booked_occupied' || selectedSeat.status === 'booked_empty') && (
                        <div style={{ marginBottom: '25px' }}>
                            <h4 style={{ color: '#aaa', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '2px solid #eee', paddingBottom: '8px', marginBottom: '15px' }}>ข้อมูลผู้จอง</h4>
                            <div style={{ lineHeight: '2', fontSize: '1rem', color: '#444' }}>
                                <div><strong style={{color:'#222'}}>รหัสนักศึกษา:</strong> {selectedSeat.studentId}</div>
                                <div><strong style={{color:'#222'}}>เวลาจอง:</strong> {selectedSeat.time} น.</div>
                            </div>
                            <div style={{ marginTop: '20px' }}>
                                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '10px', fontWeight: 'bold' }}>ภาพสแกนใบหน้าตอนจอง:</div>
                                {selectedSeat.image ? (
                                    <img src={selectedSeat.image} alt="Face Scan" style={{ width: '100%', height: '220px', objectFit: 'cover', borderRadius: '10px', border: '1px solid #ddd', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }} />
                                ) : (
                                    <div style={{ width: '100%', height: '220px', backgroundColor: '#eee', display:'flex', alignItems:'center', justifyContent:'center', borderRadius: '10px', color: '#999' }}>ไม่มีรูปภาพ</div>
                                )}
                            </div>
                        </div>
                    )}

                    {selectedSeat.status === 'unbooked_occupied' && (
                        <div style={{ backgroundColor: '#fff1f0', padding: '20px', borderRadius: '10px', border: '2px dashed #ffccc7', color: '#cf1322', fontSize: '1rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.1rem'}}>⚠️ ตรวจพบการใช้งานโดยไม่มีการจอง</strong> <br/><br/>
                            (พื้นที่แสดงภาพจากกล้องแบบ Real-time เพื่อบันทึกผู้กระทำผิด)
                        </div>
                    )}

                    <div style={{ marginTop: '10px' }}>
                        <h4 style={{ color: '#aaa', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '2px solid #eee', paddingBottom: '8px', marginBottom: '15px' }}>สถานะหน้าจอ</h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem', color: '#333' }}>
                            <div style={{ width: '15px', height: '15px', borderRadius: '50%', backgroundColor: selectedSeat.pc_on ? '#4CAF50' : '#ccc' }}></div>
                            {selectedSeat.pc_on ? 'เปิดใช้งานอยู่' : 'ปิดการใช้งาน'}
                        </div>
                    </div>

                </div>
            )}
        </div>
      </div>
    </AdminLayout>
  );
}