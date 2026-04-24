import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  RiComputerFill, RiUserFill, RiCloseLine, 
  RiTimerFill, RiUserForbidFill, RiToolsFill, RiSettings3Fill, RiArrowGoBackFill, RiLockFill,
  RiDashboard2Fill, RiCameraLensFill, RiCpuLine
} from 'react-icons/ri';
import AdminLayout from '../../components/admin/AdminLayout';

import { formatThaiDate, DAY_NAMES_EN } from '../../utils/dateUtils';
import { btnStyles, pageStyles } from '../../utils/uiConstants';
import { authFetch } from '../../utils/authFetch';

export default function MonitorMock() {
  const [selectedSeatNum, setSelectedSeatNum] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const navigate = useNavigate();

  const [showMockPanel, setShowMockPanel] = useState(false);
  const [controlSeatNum, setControlSeatNum] = useState(1); 

  const [dbBookings, setDbBookings] = useState([]);
  const [schedules, setSchedules] = useState([]); 
  const [brokenSeats, setBrokenSeats] = useState([]); 
  
  const [mockCameraState, setMockCameraState] = useState(() => {
    const initialState = {};
    for (let i = 1; i <= 30; i++) {
        initialState[i] = { available: 0, pc_on: false, is_mock_booked: false, is_broken: false, is_locked: false };
    }
    return initialState;
  });

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        const [resBookings, resSchedules, resBroken] = await Promise.all([
            fetch('/reservations'),
            authFetch('/api/system/schedules'),
            authFetch('/api/system/broken-seats')
        ]);
        
        if (resBookings.ok) setDbBookings(await resBookings.json());
        if (resSchedules.ok) setSchedules(await resSchedules.json());
        if (resBroken.ok) {
            const data = await resBroken.json();
            const brokenIds = data.filter(item => item.status === 'broken').map(item => item.seat_no);
            setBrokenSeats(brokenIds);

            setMockCameraState(prev => {
                const newState = { ...prev };
                brokenIds.forEach(id => {
                    if(newState[id]) newState[id].is_broken = true;
                });
                return newState;
            });
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); 
    return () => clearInterval(interval);
  }, []);

  const updateMockCamera = (seatNum, field, value) => {
      setMockCameraState(prev => {
          const currentSeat = prev[seatNum];
          let newState = { ...currentSeat, [field]: value };
          
          if (field === 'is_broken' && value === true) {
              newState.is_mock_booked = false;
              newState.available = 0;
              newState.pc_on = false;
          } else if (field !== 'is_broken') {
              newState.is_broken = false;
          }

          if (field === 'available') {
              if (value === 1) newState.pc_on = false; 
              if (value === 2) newState.pc_on = true;  
          } 
          else if (field === 'pc_on') {
              if (value === true && currentSeat.available === 1) {
                  newState.available = 2; 
              } else if (value === false && currentSeat.available === 2) {
                  newState.available = 1; 
              }
          }

          return { ...prev, [seatNum]: newState };
      });
  };

  const getSeatData = (seatNumber) => {
    const camInfo = mockCameraState[seatNumber];
    const isSitting = camInfo.available > 0; 
    const isPcOn = camInfo.pc_on; 
    const isMockBooked = camInfo.is_mock_booked; 
    const isBroken = camInfo.is_broken;

    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    
    // 🟢 เรียกใช้ DAY_NAMES_EN
    const todayName = DAY_NAMES_EN[now.getDay()];
    
    const activeSchedule = schedules.find(s => {
        return (
            s.start_date <= todayStr && s.end_date >= todayStr &&
            s.day_of_week === todayName &&
            s.start_time <= currentTimeStr && s.end_time >= currentTimeStr &&
            (s.seat_no === null || s.seat_no === seatNumber)
        );
    });

    const activeDbBooking = dbBookings.find(b => 
      String(b.seat_id) === String(seatNumber) && 
      b.reserve_date === todayStr && 
      b.start_time <= currentTimeStr && 
      b.end_time >= currentTimeStr
    );

    const isBooked = activeDbBooking || isMockBooked;
    let finalStatus = 'unbooked_empty'; 

    if (isBroken) finalStatus = 'broken';
    else if (activeSchedule) finalStatus = 'locked';
    else if (isBooked && isSitting) finalStatus = 'booked_occupied'; 
    else if (isBooked && !isSitting) finalStatus = 'booked_empty';    
    else if (!isBooked && isSitting) finalStatus = 'unbooked_occupied'; 

    return {
        number: seatNumber,
        status: finalStatus,
        available: camInfo.available,
        pc_on: isPcOn,
        is_mock_booked: isMockBooked,
        studentName: activeDbBooking ? `นักศึกษา (${activeDbBooking.student_id})` : (isMockBooked ? "ข้อมูลจำลอง (MOCK)" : (activeSchedule ? `ถูกล็อก: ${activeSchedule.purpose}` : null)), 
        studentId: activeDbBooking?.student_id || (isMockBooked ? "MOCK-123456" : null),
        time: activeDbBooking ? `${activeDbBooking.start_time?.substring(0,5)} - ${activeDbBooking.end_time?.substring(0,5)}` : (isMockBooked ? "09:00 - 12:00 (จำลอง)" : (activeSchedule ? `${activeSchedule.start_time.slice(0,5)} - ${activeSchedule.end_time.slice(0,5)}` : null)),
        image: activeDbBooking ? (activeDbBooking.image_filename?.startsWith('http') ? activeDbBooking.image_filename : `/data/face_scanner/${activeDbBooking.reserve_date}/${activeDbBooking.image_filename}`) : null,
        note: activeSchedule ? activeSchedule.note : null
    };
  };

  const size = {
    icon: isMobile ? 18 : 30,
    fontSize: isMobile ? '10px' : '14px',
  };

  const Seat = ({ seatNumber }) => {
    const seatData = getSeatData(seatNumber); 
    const isSelected = selectedSeatNum === seatNumber;
    
    let iconColor = "#555"; 
    let bgStyle = 'white';
    let IconComponent = RiComputerFill;

    if (seatData.status === 'booked_occupied') {
        iconColor = "#4CAF50"; 
        bgStyle = '#f6ffed';
        IconComponent = RiUserFill; 
    } else if (seatData.status === 'booked_empty') {
        iconColor = "#faad14"; 
        bgStyle = '#fffbe6';
        IconComponent = RiTimerFill; 
    } else if (seatData.status === 'unbooked_occupied') {
        iconColor = "#ef4444"; 
        bgStyle = '#fff1f0';
        IconComponent = RiUserForbidFill; 
    } else if (seatData.status === 'broken') {
        iconColor = "#9e9e9e"; 
        bgStyle = '#f5f5f5';
        IconComponent = RiToolsFill; 
    } else if (seatData.status === 'locked') {
        iconColor = "#9333ea"; 
        bgStyle = '#f3e8ff';
        IconComponent = RiLockFill;
    }

    return (
      <div 
        onClick={() => setSelectedSeatNum(seatNumber)}
        style={{
            width: size.seat, height: size.seat, 
            backgroundColor: isSelected ? 'rgba(219, 39, 119, 0.15)' : bgStyle,
            border: isSelected ? '2px solid #db2777' : `2px solid ${iconColor}40`,
            borderRadius: '12px', display: 'flex', flexDirection: 'column', 
            justifyContent: 'center', alignItems: 'center', cursor: 'pointer',
            transition: 'transform 0.2s, box-shadow 0.2s', 
            boxShadow: isSelected ? '0 4px 12px rgba(219,39,119,0.3)' : '0 2px 4px rgba(0,0,0,0.05)',
            position: 'relative'
        }}
        onMouseEnter={(e) => !isMobile && (e.currentTarget.style.transform = 'translateY(-3px)')}
        onMouseLeave={(e) => !isMobile && (e.currentTarget.style.transform = 'translateY(0)')}
      >
        <IconComponent size={size.icon} color={iconColor} />
        <div style={{ fontSize: size.fontSize, marginTop: '4px', fontWeight: 'bold', color: iconColor }}>{seatNumber}</div>

        <div style={{
          position: 'absolute', top: '6px', right: '6px',
          width: '10px', height: '10px', borderRadius: '50%',
          backgroundColor: seatData.pc_on ? '#52c41a' : '#d9d9d9',
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          border: '1.5px solid white',
          display: seatData.status === 'broken' ? 'none' : 'block' 
        }} title={seatData.pc_on ? 'หน้าจอเปิดอยู่' : 'หน้าจอปิด'} />
      </div>
    );
  };

  const seats = Array.from({ length: 30 }, (_, i) => i + 1);
  const leftSideSeats = seats.filter(num => (num - 1) % 6 < 3);
  const rightSideSeats = seats.filter(num => (num - 1) % 6 >= 3);

  const stats = { total: 30, broken: 0, active: 0, empty: 0 };
  seats.forEach(num => {
    const s = getSeatData(num);
    if(s.status === 'broken') stats.broken++;
    else if(s.status === 'booked_occupied' || s.status === 'unbooked_occupied') stats.active++;
    else if(s.status === 'unbooked_empty') stats.empty++;
  });

  const getStatusDetails = (status) => {
      switch(status) {
          case 'booked_occupied': return { text: 'กำลังใช้งานปกติ', color: '#4CAF50', tag: 'ปกติ' };
          case 'booked_empty': return { text: 'จองแล้ว แต่ไม่อยู่ที่โต๊ะ', color: '#faad14', tag: 'อาจมาสาย' };
          case 'unbooked_occupied': return { text: 'ตรวจพบผู้ใช้งานไม่ได้จอง', color: '#ef4444', tag: 'ผิดปกติ' };
          case 'broken': return { text: 'เครื่องเสีย / งดใช้งาน', color: '#9e9e9e', tag: 'แจ้งซ่อม' };
          case 'locked': return { text: 'ล็อกที่นั่ง / ติดเรียน', color: '#9333ea', tag: 'ห้ามใช้งาน' };
          default: return { text: 'ที่นั่งว่าง', color: '#555', tag: 'พร้อมใช้งาน' };
      }
  };

  const selectedSeatData = selectedSeatNum ? getSeatData(selectedSeatNum) : null;
  const currentControlData = mockCameraState[controlSeatNum]; 

  return (
    <AdminLayout>
      <div style={{ position: 'relative', display: 'flex', height: '100%', overflow: 'hidden', backgroundColor: '#fffdfc' }}>
        
        <div style={{ flex: 1, padding: isMobile ? '10px' : '20px', overflowY: 'auto', width: '100%', paddingBottom: '100px' }}>
            
            {/* 🟢 Header มาตรฐาน 1200px แบบ Mock Theme */}
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                <div style={{ ...pageStyles.header, borderBottom: '2px solid #fbcfe8' }}>
                    <h2 style={{ ...pageStyles.title, color: '#db2777' }}>
                        <RiDashboard2Fill /> Live Monitor 
                        <span style={{fontSize: '0.8rem', backgroundColor: '#db2777', color: 'white', padding: '4px 10px', borderRadius: '20px', verticalAlign: 'middle', marginLeft: '10px'}}>โหมดจำลอง (MOCK)</span>
                    </h2>
                    <button
                        onClick={() => navigate('/admin/monitor')}
                        style={{ ...btnStyles.export, backgroundColor: '#fdf2f8', color: '#db2777', borderColor: '#fbcfe8' }}
                    >
                        <RiArrowGoBackFill size={18} /> กลับโหมดปกติ
                    </button>
                </div>

                {/* 🟢 Stats Card Mock Theme */}
                <div style={{ display: 'flex', gap: '20px', marginBottom: '25px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '150px', background: '#fdf2f8', border: '1px solid #fbcfe8', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: '0 4px 15px rgba(219,39,119,0.05)' }}>
                        <div style={{ color: '#db2777', fontSize: '2.2rem', fontWeight: '900' }}>{stats.active}</div>
                        <div style={{ color: '#ec4899', fontSize: '0.95rem', fontWeight: 'bold', marginTop: '5px' }}>กำลังใช้งาน (จำลอง)</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '150px', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: '0 4px 15px rgba(0,0,0,0.03)' }}>
                        <div style={{ color: '#475569', fontSize: '2.2rem', fontWeight: '900' }}>{stats.empty}</div>
                        <div style={{ color: '#64748b', fontSize: '0.95rem', fontWeight: 'bold', marginTop: '5px' }}>ว่างพร้อมใช้</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '150px', background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: '0 4px 15px rgba(0,0,0,0.03)' }}>
                        <div style={{ color: '#cf1322', fontSize: '2.2rem', fontWeight: '900' }}>{stats.broken}</div>
                        <div style={{ color: '#f5222d', fontSize: '0.95rem', fontWeight: 'bold', marginTop: '5px' }}>เครื่องเสีย</div>
                    </div>
                </div>

                {/* 🟢 Seat Map Card Mock Theme */}
                <div style={{ ...pageStyles.card, border: '2px solid #fbcfe8', boxShadow: '0 4px 15px rgba(219,39,119,0.08)' }}>
                    <div style={{ textAlign: 'center', padding: '10px', backgroundColor: '#831843', borderRadius: '8px', marginBottom: isMobile ? '20px' : '35px', fontWeight: 'bold', color: 'white', fontSize: isMobile ? '0.9rem' : '1.1rem', letterSpacing: '2px' }}>
                        กระดาน (หน้าห้อง)
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 0.4fr 1fr 1fr 1fr', gap: '8px' }}>
                        {Array.from({ length: 30 }, (_, i) => i + 1).map(num => {
                          const col = ((num - 1) % 6) + 1;
                          const gridColumn = col > 3 ? col + 1 : col;
                          return <div key={num} style={{ gridColumn }}><Seat seatNumber={num} /></div>;
                        })}
                    </div>
                </div>

                {/* 🟢 Legend Card Mock Theme */}
                <div style={{ ...pageStyles.card, border: '1px solid #fce7f3', display: 'flex', justifyContent: 'center', gap: isMobile ? '15px' : '25px', marginTop: '20px', flexWrap: 'wrap', marginBottom: '50px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiUserFill color="#4CAF50" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ใช้งานปกติ</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiTimerFill color="#faad14" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>จอง&ไม่นั่ง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiUserForbidFill color="#ef4444" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ไม่จอง&นั่ง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiComputerFill color="#64748b" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ว่าง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiLockFill color="#9333ea" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ล็อก/เรียน</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiToolsFill color="#9e9e9e" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>เสีย</span></div>
                </div>
            </div>
        </div>

        {selectedSeatNum && (
            <div 
                onClick={() => setSelectedSeatNum(null)}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 999, backdropFilter: 'blur(2px)' }}
            />
        )}

        <div style={{ 
            position: 'fixed', top: 0, right: selectedSeatNum ? 0 : '-420px', 
            width: '100%', maxWidth: '400px', height: '100%', backgroundColor: 'white',
            boxShadow: '-5px 0 30px rgba(0,0,0,0.2)', transition: 'right 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)',
            display: 'flex', flexDirection: 'column', borderLeft: '3px solid #db2777',
            zIndex: 1000 
        }}>
            <div style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fdf2f8', borderBottom: '1px solid #fbcfe8' }}>
                <h3 style={{ margin: 0, color: '#9d174d', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <RiComputerFill color="#db2777" /> โต๊ะหมายเลข {selectedSeatData?.number}
                </h3>
                <div onClick={() => setSelectedSeatNum(null)} style={{ cursor: 'pointer', backgroundColor: '#fce7f3', padding: '6px', borderRadius: '50%', display: 'flex', transition: 'background 0.2s' }} onMouseEnter={e => e.currentTarget.style.backgroundColor='#fbcfe8'} onMouseLeave={e => e.currentTarget.style.backgroundColor='#fce7f3'}>
                    <RiCloseLine size={20} color="#db2777" />
                </div>
            </div>

            {selectedSeatData && (
                <div style={{ padding: '25px', overflowY: 'auto', flex: 1 }}>
                    <div style={{ backgroundColor: getStatusDetails(selectedSeatData.status).color + '15', color: getStatusDetails(selectedSeatData.status).color, padding: '15px', borderRadius: '8px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '25px', border: `1px solid ${getStatusDetails(selectedSeatData.status).color}50`, fontSize: '1.1rem' }}>
                        {getStatusDetails(selectedSeatData.status).text}
                    </div>

                    {(selectedSeatData.status === 'booked_occupied' || selectedSeatData.status === 'booked_empty') && (
                        <div style={{ marginBottom: '25px' }}>
                            <h4 style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', marginBottom: '15px' }}>ข้อมูลผู้จองปัจจุบัน</h4>
                            <div style={{ lineHeight: '1.8', fontSize: '1rem', color: '#334155', background: '#f8fafc', padding: '15px', borderRadius: '8px' }}>
                                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                    <span style={{color:'#64748b'}}>รหัสนักศึกษา:</span> 
                                    <strong style={{color:'#0f172a'}}>{selectedSeatData.studentId}</strong>
                                </div>
                                <div style={{display: 'flex', justifyContent: 'space-between', marginTop: '5px'}}>
                                    <span style={{color:'#64748b'}}>ช่วงเวลา:</span> 
                                    <strong style={{color:'#0f172a'}}>{selectedSeatData.time}</strong>
                                </div>
                            </div>
                            
                            <div style={{ marginTop: '20px' }}>
                                <div style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '10px', fontWeight: 'bold' }}>ภาพยืนยันตัวตน:</div>
                                {selectedSeatData.image ? (
                                    <img 
                                        src={selectedSeatData.image} 
                                        alt="Face Scan" 
                                        style={{ width: '100%', height: '240px', objectFit: 'cover', backgroundColor: '#f1f5f9', borderRadius: '8px', border: '1px solid #e2e8f0'}} 
                                    />
                                ) : (
                                    <div style={{ width: '100%', height: '200px', backgroundColor: '#f8fafc', display:'flex', alignItems:'center', justifyContent:'center', borderRadius: '8px', color: '#94a3b8', border: '1px dashed #cbd5e1' }}>
                                        {selectedSeatData.is_mock_booked ? 'ไม่มีรูปภาพ (ข้อมูลจำลอง)' : 'ไม่มีรูปภาพ'}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {selectedSeatData.status === 'unbooked_occupied' && (
                        <div style={{ backgroundColor: '#fff1f0', padding: '20px', borderRadius: '8px', border: '1px dashed #ffa39e', color: '#cf1322', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiUserForbidFill/> ตรวจพบผู้ลักลอบใช้งาน</strong> <br/>
                            พบว่ามีบุคคลกำลังนั่งอยู่ที่โต๊ะนี้ โดยไม่มีข้อมูลการจองในระบบ ณ เวลาปัจจุบัน
                        </div>
                    )}

                    {selectedSeatData.status === 'broken' && (
                        <div style={{ backgroundColor: '#f5f5f5', padding: '20px', borderRadius: '8px', border: '1px dashed #d9d9d9', color: '#595959', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiToolsFill/> เครื่องขัดข้องชั่วคราว</strong> <br/>
                            ที่นั่งนี้ถูกระบุว่าชำรุดในระบบ ไม่สามารถใช้งานได้
                        </div>
                    )}

                    {selectedSeatData.status === 'locked' && (
                        <div style={{ backgroundColor: '#f3e8ff', padding: '20px', borderRadius: '8px', border: '1px dashed #d8b4fe', color: '#6b21a8', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiLockFill/> ถูกล็อกโดยตารางเรียน</strong> <br/>
                            <div style={{marginTop: '10px'}}>
                                <div><strong style={{color:'#4c1d95'}}>เวลา:</strong> {selectedSeatData.time}</div>
                                <div><strong style={{color:'#4c1d95'}}>วัตถุประสงค์:</strong> {selectedSeatData.studentName}</div>
                            </div>
                        </div>
                    )}

                    <div style={{ marginTop: 'auto', background: '#f8fafc', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                        <h4 style={{ color: '#64748b', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', margin: '0 0 10px 0' }}>สถานะฮาร์ดแวร์</h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1rem', color: '#334155', fontWeight: 'bold' }}>
                            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: selectedSeatData.pc_on ? '#52c41a' : '#cbd5e1', boxShadow: '0 0 0 2px white, 0 0 0 3px ' + (selectedSeatData.pc_on ? '#b7eb8f' : '#e2e8f0') }}></div>
                            {selectedSeatData.pc_on ? 'หน้าจอเปิดใช้งานอยู่' : 'หน้าจอปิดอยู่ (Standby)'}
                        </div>
                    </div>
                </div>
            )}
        </div>

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
                position: 'fixed', bottom: '25px', left: '25px', width: '340px', backgroundColor: 'white',
                borderRadius: '16px', boxShadow: '0 10px 40px rgba(0,0,0,0.15)', border: '1px solid #fbcfe8', 
                zIndex: 2000, overflow: 'hidden', animation: 'fadeIn 0.2s ease-out'
            }}>
                <div style={{ backgroundColor: '#fdf2f8', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #fbcfe8' }}>
                    <h4 style={{ margin: 0, color: '#9d174d', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.05rem' }}>
                        <RiSettings3Fill /> MOCK CONTROL PANEL
                    </h4>
                    <div onClick={() => setShowMockPanel(false)} style={{cursor: 'pointer', display: 'flex', backgroundColor: '#fce7f3', borderRadius: '50%', padding: '4px', transition: 'background 0.2s'}} onMouseEnter={e => e.currentTarget.style.backgroundColor='#fbcfe8'} onMouseLeave={e => e.currentTarget.style.backgroundColor='#fce7f3'}>
                        <RiCloseLine size={20} color="#db2777" />
                    </div>
                </div>

                <div style={{ padding: '20px' }}>
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '8px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Target Seat (ที่นั่ง)</label>
                        <select 
                            value={controlSeatNum}
                            onChange={(e) => setControlSeatNum(parseInt(e.target.value))}
                            style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', backgroundColor: '#f8fafc', fontSize: '1rem', fontWeight: 'bold', color: '#334155', cursor: 'pointer' }}
                        >
                            {Array.from({length: 30}, (_, i) => (
                                <option key={i+1} value={i+1}>โต๊ะหมายเลข {i+1}</option>
                            ))}
                        </select>
                    </div>

                    <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px dashed #e2e8f0' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.85rem', color: '#64748b', marginBottom: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}><RiCpuLine/> Hardware Status</label>
                        <div style={{ display: 'flex', gap: '15px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                <input type="radio" checked={currentControlData.is_broken === false} onChange={() => updateMockCamera(controlSeatNum, 'is_broken', false)} style={{ transform: 'scale(1.2)' }} />
                                ใช้งานปกติ
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#ef4444' }}>
                                <input type="radio" checked={currentControlData.is_broken === true} onChange={() => updateMockCamera(controlSeatNum, 'is_broken', true)} style={{ transform: 'scale(1.2)' }} />
                                เครื่องเสีย
                            </label>
                        </div>
                    </div>

                    <div style={{ 
                        opacity: currentControlData.is_broken ? 0.4 : 1, 
                        pointerEvents: currentControlData.is_broken ? 'none' : 'auto',
                        transition: 'opacity 0.2s'
                    }}>
                        <div style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px dashed #e2e8f0' }}>
                            <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}>Booking (การจอง)</label>
                            <div style={{ display: 'flex', gap: '15px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.is_mock_booked === true} onChange={() => updateMockCamera(controlSeatNum, 'is_mock_booked', true)} style={{ transform: 'scale(1.2)' }} />
                                    มีคิวจอง
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.is_mock_booked === false} onChange={() => updateMockCamera(controlSeatNum, 'is_mock_booked', false)} style={{ transform: 'scale(1.2)' }} />
                                    ยังไม่จอง
                                </label>
                            </div>
                        </div>
                        
                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.85rem', color: '#db2777', marginBottom: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}><RiCameraLensFill/> YOLOv8 Detection</label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', background: '#fdf2f8', padding: '12px', borderRadius: '8px', border: '1px solid #fbcfe8' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.available === 0} onChange={() => updateMockCamera(controlSeatNum, 'available', 0)} style={{ transform: 'scale(1.2)' }} />
                                    0 = ไม่มีคนนั่ง (ว่าง)
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.available === 1} onChange={() => updateMockCamera(controlSeatNum, 'available', 1)} style={{ transform: 'scale(1.2)' }} />
                                    1 = นั่ง แต่คอมดับ
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.available === 2} onChange={() => updateMockCamera(controlSeatNum, 'available', 2)} style={{ transform: 'scale(1.2)' }} />
                                    2 = นั่ง และคอมเปิด
                                </label>
                            </div>
                        </div>

                        <div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.85rem', color: '#64748b', marginBottom: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}><RiComputerFill/> PC Screen</label>
                            <div style={{ display: 'flex', gap: '15px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.pc_on === true} onChange={() => updateMockCamera(controlSeatNum, 'pc_on', true)} style={{ transform: 'scale(1.2)' }} />
                                    เปิดจอ
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.95rem', color: '#334155' }}>
                                    <input type="radio" checked={currentControlData.pc_on === false} onChange={() => updateMockCamera(controlSeatNum, 'pc_on', false)} style={{ transform: 'scale(1.2)' }} />
                                    ปิดจอ
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