import { useState, useEffect } from 'react';
import { 
  RiComputerFill, RiUserFill, RiCloseLine, 
  RiTimerFill, RiUserForbidFill, RiToolsFill, RiSettings3Fill
} from 'react-icons/ri';
import AdminLayout from './AdminLayout';

export default function MonitorMock() {
  const [selectedSeatNum, setSelectedSeatNum] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  const [showMockPanel, setShowMockPanel] = useState(false);
  const [controlSeatNum, setControlSeatNum] = useState(1); 

  const [dbBookings, setDbBookings] = useState([]);
  
  const [mockCameraState, setMockCameraState] = useState(() => {
    const initialState = {};
    for (let i = 1; i <= 30; i++) {
        initialState[i] = { available: 0, pc_on: false, is_mock_booked: false, is_broken: false };
    }
    return initialState;
  });

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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

  // ฟังก์ชันเปลี่ยนค่าจำลองแบบอัจฉริยะ (ผูกค่าเข้าด้วยกัน)
  const updateMockCamera = (seatNum, field, value) => {
      setMockCameraState(prev => {
          const currentSeat = prev[seatNum];
          let newState = { ...currentSeat, [field]: value };
          
          // 1. ถ้ากดเครื่องเสีย ให้รีเซ็ตอันอื่นให้หมด
          if (field === 'is_broken' && value === true) {
              newState.is_mock_booked = false;
              newState.available = 0;
              newState.pc_on = false;
          } else if (field !== 'is_broken') {
              newState.is_broken = false;
          }

          // 2. ผูกสถานะคนนั่ง(available) เข้ากับสถานะจอภาพ(pc_on)
          if (field === 'available') {
              if (value === 1) newState.pc_on = false; // นั่งแต่คอมปิด -> บังคับปิดจอ
              if (value === 2) newState.pc_on = true;  // กำลังใช้งาน -> บังคับเปิดจอ
          } 
          // 3. ถ้าไปกดเปิด/ปิดจอเอง ก็ให้สถานะคนนั่งวิ่งตามด้วย 
          else if (field === 'pc_on') {
              if (value === true && currentSeat.available === 1) {
                  newState.available = 2; // ถ้าคนนั่งอยู่แล้วกดเปิดจอ -> เปลี่ยนเป็น 2
              } else if (value === false && currentSeat.available === 2) {
                  newState.available = 1; // ถ้าคนกำลังใช้งานแล้วกดปิดจอ -> เปลี่ยนเป็น 1
              }
          }

          return {
              ...prev,
              [seatNum]: newState
          };
      });
  };

  const getSeatData = (seatNumber) => {
    const camInfo = mockCameraState[seatNumber];
    const isSitting = camInfo.available > 0; 
    const isPcOn = camInfo.pc_on; 
    const isMockBooked = camInfo.is_mock_booked; 
    const isBroken = camInfo.is_broken;

    const now = new Date();
    const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    
    const activeDbBooking = dbBookings.find(b => 
      String(b.seat_id) === String(seatNumber) && 
      b.start_time <= currentTimeStr && 
      b.end_time >= currentTimeStr
    );

    const isBooked = activeDbBooking || isMockBooked;
    let finalStatus = 'unbooked_empty'; 

    if (isBroken) {
        finalStatus = 'broken';
    } else if (isBooked && isSitting) {
        finalStatus = 'booked_occupied'; 
    } else if (isBooked && !isSitting) {
        finalStatus = 'booked_empty';    
    } else if (!isBooked && isSitting) {
        finalStatus = 'unbooked_occupied'; 
    }

    return {
        number: seatNumber,
        status: finalStatus,
        available: camInfo.available,
        pc_on: isPcOn,
        is_mock_booked: isMockBooked,
        studentName: activeDbBooking ? `นักศึกษา (${activeDbBooking.student_id})` : (isMockBooked ? "นักศึกษา (ข้อมูลจำลอง)" : null), 
        studentId: activeDbBooking?.student_id || (isMockBooked ? "MOCK-123456" : null),
        time: activeDbBooking ? `${activeDbBooking.start_time} - ${activeDbBooking.end_time}` : (isMockBooked ? "09:00 - 12:00 (จำลอง)" : null),
        image: activeDbBooking ? `/data/face_scanner/${activeDbBooking.image_filename}` : null
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
    const isSelected = selectedSeatNum === seatNumber;
    
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
        onClick={() => setSelectedSeatNum(seatNumber)}
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
          border: '2px solid white',
          display: seatData.status === 'broken' ? 'none' : 'block' 
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

  const selectedSeatData = selectedSeatNum ? getSeatData(selectedSeatNum) : null;
  const currentControlData = mockCameraState[controlSeatNum]; 

  return (
    <AdminLayout>
      <div style={{ position: 'relative', display: 'flex', height: '100%', overflow: 'hidden' }}>
        
        <div style={{ flex: 1, padding: isMobile ? '10px' : '30px', overflowY: 'auto', width: '100%', paddingBottom: '100px' }}>
            <h2 style={{ marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '15px', fontSize: isMobile ? '1.1rem' : '1.5rem', maxWidth: '950px', margin: '0 auto 25px' }}>
                Live Monitor (โหมดจำลอง)
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
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiToolsFill color="#9e9e9e" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>เสีย</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ display: 'inline-block', width: '12px', height: '12px', backgroundColor: '#4CAF50', borderRadius: '50%', border: '2px solid #ddd' }}></span>
                    <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>หน้าจอเปิด</span>
                </div>
            </div>
        </div>

        {selectedSeatNum && (
            <div 
                onClick={() => setSelectedSeatNum(null)}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 999 }}
            />
        )}

        <div style={{ 
            position: 'fixed', top: 0, right: selectedSeatNum ? 0 : '-420px', 
            width: '100%', maxWidth: '400px', height: '100%', backgroundColor: 'white',
            boxShadow: '-5px 0 25px rgba(0,0,0,0.15)', transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            display: 'flex', flexDirection: 'column', borderLeft: '1px solid #eee',
            zIndex: 1000 
        }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#f8f9fa' }}>
                <h3 style={{ margin: 0, color: '#2c3e50' }}>ข้อมูลที่นั่ง {selectedSeatData?.number}</h3>
                <div onClick={() => setSelectedSeatNum(null)} style={{ cursor: 'pointer', backgroundColor: '#eee', padding: '5px', borderRadius: '50%', display: 'flex' }}>
                    <RiCloseLine size={24} color="#666" />
                </div>
            </div>

            {selectedSeatData && (
                <div style={{ padding: '25px', overflowY: 'auto', flex: 1 }}>
                    <div style={{ backgroundColor: getStatusDetails(selectedSeatData.status).color + '15', color: getStatusDetails(selectedSeatData.status).color, padding: '15px', borderRadius: '10px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '25px', border: `2px solid ${getStatusDetails(selectedSeatData.status).color}50`, fontSize: '1.1rem' }}>
                        {getStatusDetails(selectedSeatData.status).text}
                    </div>

                    {(selectedSeatData.status === 'booked_occupied' || selectedSeatData.status === 'booked_empty') && (
                        <div style={{ marginBottom: '25px' }}>
                            <h4 style={{ color: '#aaa', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '2px solid #eee', paddingBottom: '8px', marginBottom: '15px' }}>ข้อมูลผู้จอง</h4>
                            <div style={{ lineHeight: '2', fontSize: '1rem', color: '#444' }}>
                                <div><strong style={{color:'#222'}}>รหัสนักศึกษา:</strong> {selectedSeatData.studentId}</div>
                                <div><strong style={{color:'#222'}}>เวลาจอง:</strong> {selectedSeatData.time} น.</div>
                            </div>
                            <div style={{ marginTop: '20px' }}>
                                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '10px', fontWeight: 'bold' }}>ภาพสแกนใบหน้าตอนจอง:</div>
                                {selectedSeatData.image ? (
                                    <img src={selectedSeatData.image} alt="Face Scan" style={{ width: '100%', height: '220px', objectFit: 'cover', borderRadius: '10px', border: '1px solid #ddd', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }} />
                                ) : (
                                    <div style={{ width: '100%', height: '220px', backgroundColor: '#eee', display:'flex', alignItems:'center', justifyContent:'center', borderRadius: '10px', color: '#999', fontSize: '0.9rem', border: '2px dashed #ccc' }}>
                                        {selectedSeatData.is_mock_booked ? 'ไม่มีรูปภาพ (ข้อมูลจำลอง)' : 'ไม่มีรูปภาพ'}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {selectedSeatData.status === 'unbooked_occupied' && (
                        <div style={{ backgroundColor: '#fff1f0', padding: '20px', borderRadius: '10px', border: '2px dashed #ffccc7', color: '#cf1322', fontSize: '1rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.1rem'}}>⚠️ ตรวจพบการใช้งานโดยไม่มีการจอง</strong> <br/><br/>
                            (พื้นที่แสดงภาพจากกล้องแบบ Real-time เพื่อบันทึกผู้กระทำผิด)
                        </div>
                    )}

                    {selectedSeatData.status === 'broken' && (
                        <div style={{ backgroundColor: '#f5f5f5', padding: '20px', borderRadius: '10px', border: '2px dashed #d9d9d9', color: '#595959', fontSize: '1rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.1rem'}}>🛠️ หมายเหตุการแจ้งซ่อม:</strong><br/>
                            เครื่องขัดข้องชั่วคราว (ข้อมูลจำลองจากระบบ Admin)
                        </div>
                    )}
                </div>
            )}
        </div>

        {/* ================= 🎛️ หน้าต่างควบคุม (Floating Panel) ================= */}
        {!showMockPanel && (
            <div 
                onClick={() => setShowMockPanel(true)} 
                style={{ 
                    position: 'fixed', bottom: '25px', left: '25px', backgroundColor: '#db2777', color: 'white', 
                    padding: '12px 20px', borderRadius: '30px', cursor: 'pointer', zIndex: 1999, 
                    fontWeight: 'bold', boxShadow: '0 4px 15px rgba(219,39,119,0.4)', display: 'flex', alignItems: 'center', gap: '8px',
                    transition: 'transform 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <RiSettings3Fill size={20} /> เปิดแผงควบคุม AI จำลอง
            </div>
        )}

        {showMockPanel && (
            <div style={{
                position: 'fixed', bottom: '25px', left: '25px', width: '320px', backgroundColor: 'white',
                borderRadius: '15px', boxShadow: '0 10px 30px rgba(0,0,0,0.2)', border: '2px solid #f472b6', 
                zIndex: 2000, overflow: 'hidden', animation: 'fadeIn 0.2s'
            }}>
                <div style={{ backgroundColor: '#fdf2f8', padding: '15px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #fbcfe8' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                        <h4 style={{ margin: 0, color: '#db2777', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            แผงควบคุม (ทดสอบ)
                        </h4>
                        <div onClick={() => setShowMockPanel(false)} style={{cursor: 'pointer', display: 'flex', backgroundColor: '#fbcfe8', borderRadius: '50%', padding: '2px'}}><RiCloseLine size={20} color="#db2777" /></div>
                    </div>
                </div>

                <div style={{ padding: '20px' }}>
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', fontSize: '0.9rem', color: '#555', marginBottom: '8px', fontWeight: 'bold' }}>เลือกที่นั่งที่ต้องการปรับ</label>
                        <select 
                            value={controlSeatNum}
                            onChange={(e) => setControlSeatNum(parseInt(e.target.value))}
                            style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', outline: 'none', backgroundColor: '#f8fafc', fontSize: '1rem', fontWeight: 'bold' }}
                        >
                            {Array.from({length: 30}, (_, i) => (
                                <option key={i+1} value={i+1}>โต๊ะหมายเลข {i+1}</option>
                            ))}
                        </select>
                    </div>

                    <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '2px dashed #fbcfe8' }}>
                        <label style={{ display: 'block', fontSize: '0.9rem', color: '#555', marginBottom: '8px', fontWeight: 'bold' }}>สถานะอุปกรณ์ (Hardware)</label>
                        <div style={{ display: 'flex', gap: '15px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                <input 
                                    type="radio" 
                                    checked={currentControlData.is_broken === false} 
                                    onChange={() => updateMockCamera(controlSeatNum, 'is_broken', false)}
                                    style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                />
                                ปกติ
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#ef4444' }}>
                                <input 
                                    type="radio" 
                                    checked={currentControlData.is_broken === true} 
                                    onChange={() => updateMockCamera(controlSeatNum, 'is_broken', true)}
                                    style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                />
                                เครื่องเสีย
                            </label>
                        </div>
                    </div>

                    <div style={{ 
                        opacity: currentControlData.is_broken ? 0.3 : 1, 
                        pointerEvents: currentControlData.is_broken ? 'none' : 'auto',
                        transition: 'opacity 0.2s'
                    }}>
                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'block', fontSize: '0.9rem', color: '#555', marginBottom: '8px', fontWeight: 'bold' }}>สถานะการจอง (Booking)</label>
                            <div style={{ display: 'flex', gap: '15px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.is_mock_booked === true} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'is_mock_booked', true)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    จองแล้ว
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.is_mock_booked === false} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'is_mock_booked', false)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    ยังไม่จอง
                                </label>
                            </div>
                        </div>
                        
                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'block', fontSize: '0.9rem', color: '#555', marginBottom: '10px', fontWeight: 'bold' }}>👤 ตรวจจับคนนั่ง (YOLOv8)</label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.available === 0} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'available', 0)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    0 = ว่าง (ไม่มีคนนั่ง)
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.available === 1} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'available', 1)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    1 = นั่ง แต่คอมปิด
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.available === 2} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'available', 2)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    2 = กำลังใช้งาน (คอมเปิด)
                                </label>
                            </div>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '0.9rem', color: '#555', marginBottom: '8px', fontWeight: 'bold' }}>สถานะหน้าจอคอม</label>
                            <div style={{ display: 'flex', gap: '15px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.pc_on === true} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'pc_on', true)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    เปิด
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                                    <input 
                                        type="radio" 
                                        checked={currentControlData.pc_on === false} 
                                        onChange={() => updateMockCamera(controlSeatNum, 'pc_on', false)}
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                    ปิด
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )}

        <style>
            {`
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            `}
        </style>
      </div>
    </AdminLayout>
  );
}