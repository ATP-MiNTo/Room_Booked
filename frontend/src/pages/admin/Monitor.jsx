import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import { 
  RiComputerFill, RiUserFill, RiCloseLine, 
  RiTimerFill, RiUserForbidFill, RiToolsFill, RiFlaskFill, RiLockFill,
  RiDashboard2Fill, RiStopCircleLine, RiRefreshLine
} from 'react-icons/ri';
import AdminLayout from '../../components/admin/AdminLayout';

import { formatThaiDate, DAY_NAMES_EN } from '../../utils/dateUtils';
import { btnStyles, pageStyles } from '../../utils/uiConstants';
import { authFetch } from '../../utils/authFetch';

export default function Monitor() {
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const navigate = useNavigate();

  const [dbBookings, setDbBookings] = useState([]);
  const [cameraData, setCameraData] = useState([]);
  const [schedules, setSchedules] = useState([]); 
  const [brokenSeats, setBrokenSeats] = useState([]); 

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
          setBrokenSeats(data.filter(item => item.status === 'broken').map(item => item.seat_no));
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); 
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/pc-updates`; 
    
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setCameraData(data);
      } catch (error) {
        console.error("Error parsing camera data:", error);
      }
    };
    ws.onerror = (error) => console.error("WebSocket Camera Error:", error);
    return () => ws.close();
  }, []);

  const getSeatData = (seatNumber) => {
    const camInfo = cameraData.find(pc => pc.pc_name === `PC${seatNumber}`) || { available: 0, pc_on: false };
    const isSitting = camInfo.available > 0; 
    const isPcOn = camInfo.pc_on; 

    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    
    const isBroken = brokenSeats.includes(seatNumber);

    const todayName = DAY_NAMES_EN[now.getDay()];
    
    const activeSchedule = schedules.find(s => {
        return (
            s.start_date <= todayStr && s.end_date >= todayStr &&
            s.day_of_week === todayName &&
            s.start_time <= currentTimeStr && s.end_time >= currentTimeStr &&
            (s.seat_no === null || s.seat_no === seatNumber)
        );
    });

    const activeBooking = dbBookings.find(b => 
      String(b.seat_id) === String(seatNumber) && 
      b.reserve_date === todayStr && 
      b.start_time <= currentTimeStr && 
      b.end_time >= currentTimeStr
    );

    let finalStatus = 'unbooked_empty';

    if (isBroken) finalStatus = 'broken';
    else if (activeSchedule) finalStatus = 'locked';
    else if (activeBooking && isSitting) finalStatus = 'booked_occupied'; 
    else if (activeBooking && !isSitting) finalStatus = 'booked_empty';    
    else if (!activeBooking && isSitting) finalStatus = 'unbooked_occupied'; 

    return {
        number: seatNumber,
        status: finalStatus,
        available: camInfo.available,
        pc_on: isPcOn,
        booking_ref: activeBooking,
        studentName: activeBooking ? `นักศึกษา (${activeBooking.student_id})` : (activeSchedule ? `ถูกล็อก: ${activeSchedule.purpose}` : null), 
        studentId: activeBooking?.student_id || null,
        time: activeBooking ? `${activeBooking.start_time} - ${activeBooking.end_time}` : (activeSchedule ? `${activeSchedule.start_time.slice(0,5)} - ${activeSchedule.end_time.slice(0,5)}` : null),
        image: activeBooking ? `/data/face_scanner/${activeBooking.reserve_date}/${activeBooking.image_filename}` : null,
        note: activeSchedule ? activeSchedule.note : null
    };
  };

  const forceEndBooking = async (studentId) => {
    const confirm = await Swal.fire({
      title: 'ต้องการยกเลิกการจอง?',
      text: `บังคับยกเลิกการจองของรหัส ${studentId} ทันที`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonText: 'ยกเลิก',
      confirmButtonText: 'ใช่, ยกเลิกเลย'
    });

    if (confirm.isConfirmed) {
        Swal.fire('สำเร็จ', 'ยกเลิกการจองเรียบร้อยแล้ว', 'success');
        setSelectedSeat(null);
        fetchAllData();
    }
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
        onClick={() => setSelectedSeat({ number: seatNumber, ...seatData })}
        style={{
            width: size.seat, height: size.seat, 
            backgroundColor: isSelected ? 'rgba(22, 119, 255, 0.15)' : bgStyle,
            border: isSelected ? '2px solid #1677ff' : `2px solid ${iconColor}40`,
            borderRadius: '12px', display: 'flex', flexDirection: 'column', 
            justifyContent: 'center', alignItems: 'center', cursor: 'pointer',
            transition: 'transform 0.2s, box-shadow 0.2s', 
            boxShadow: isSelected ? '0 4px 12px rgba(22,119,255,0.3)' : '0 2px 4px rgba(0,0,0,0.05)',
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

  const stats = {
    total: 30,
    broken: brokenSeats.length,
    active: 0,
    empty: 0
  };
  
  seats.forEach(num => {
    const s = getSeatData(num);
    if(s.status === 'booked_occupied' || s.status === 'unbooked_occupied') stats.active++;
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

  return (
    <AdminLayout>
      <div style={{ position: 'relative', display: 'flex', height: '100%', overflow: 'hidden' }}>
        
        <div style={{ flex: 1, padding: isMobile ? '10px' : '20px', overflowY: 'auto', width: '100%' }}>
            
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                <div style={pageStyles.header}>
                    <h2 style={pageStyles.title}>
                        <RiDashboard2Fill color="#1677ff" /> Live Monitor (ห้อง B4-302)
                    </h2>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        {}
                        <button
                            onClick={() => navigate('/admin/monitor-mock')}
                            style={{ ...btnStyles.export, backgroundColor: '#fdf2f8', color: '#db2777', borderColor: '#fbcfe8' }}
                        >
                            <RiFlaskFill size={18} /> โหมดจำลอง AI
                        </button>
                        <button onClick={fetchAllData} style={btnStyles.refresh}>
                            <RiRefreshLine size={18} /> Refresh
                        </button>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '20px', marginBottom: '25px', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '150px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: '0 4px 15px rgba(0,0,0,0.03)' }}>
                        <div style={{ color: '#389e0d', fontSize: '2.2rem', fontWeight: '900' }}>{stats.active}</div>
                        <div style={{ color: '#52c41a', fontSize: '0.95rem', fontWeight: 'bold', marginTop: '5px' }}>กำลังใช้งาน</div>
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

                <div style={pageStyles.card}>
                    <div style={{ textAlign: 'center', padding: '10px', backgroundColor: '#1e293b', borderRadius: '8px', marginBottom: isMobile ? '20px' : '35px', minWidth: isMobile ? '360px' : 'auto', fontWeight: 'bold', color: 'white', fontSize: isMobile ? '0.9rem' : '1.1rem', letterSpacing: '2px' }}>
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

                <div style={{ ...pageStyles.card, display: 'flex', justifyContent: 'center', gap: isMobile ? '15px' : '25px', marginTop: '20px', flexWrap: 'wrap', marginBottom: '50px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiUserFill color="#4CAF50" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ใช้งานปกติ</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiTimerFill color="#faad14" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>จอง&ไม่นั่ง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiUserForbidFill color="#ef4444" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ไม่จอง&นั่ง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiComputerFill color="#64748b" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ว่าง</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiLockFill color="#9333ea" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>ล็อก/เรียน</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><RiToolsFill color="#9e9e9e" size={20} /> <span style={{fontSize: '0.95rem', color: '#475569', fontWeight: 'bold'}}>เสีย</span></div>
                </div>

            </div>
        </div>

        {selectedSeat && (
            <div 
                onClick={() => setSelectedSeat(null)}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 999, backdropFilter: 'blur(2px)' }}
            />
        )}

        <div style={{ 
            position: 'fixed', top: 0, right: selectedSeat ? 0 : '-420px', 
            width: '100%', maxWidth: '400px', height: '100%', backgroundColor: 'white',
            boxShadow: '-5px 0 30px rgba(0,0,0,0.2)', transition: 'right 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)',
            display: 'flex', flexDirection: 'column',
            zIndex: 1000 
        }}>
            <div style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#f8f9fa', borderBottom: '2px solid #eee' }}>
                <h3 style={{ margin: 0, color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <RiComputerFill color="#1677ff" /> โต๊ะหมายเลข {selectedSeat?.number}
                </h3>
                <div onClick={() => setSelectedSeat(null)} style={{ cursor: 'pointer', backgroundColor: '#e2e8f0', padding: '6px', borderRadius: '50%', display: 'flex', transition: 'background 0.2s' }} onMouseEnter={e => e.currentTarget.style.backgroundColor='#cbd5e1'} onMouseLeave={e => e.currentTarget.style.backgroundColor='#e2e8f0'}>
                    <RiCloseLine size={20} color="#475569" />
                </div>
            </div>

            {selectedSeat && (
                <div style={{ padding: '25px', overflowY: 'auto', flex: 1 }}>
                    
                    <div style={{ backgroundColor: getStatusDetails(selectedSeat.status).color + '15', color: getStatusDetails(selectedSeat.status).color, padding: '15px', borderRadius: '8px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '25px', border: `1px solid ${getStatusDetails(selectedSeat.status).color}50`, fontSize: '1.1rem' }}>
                        {getStatusDetails(selectedSeat.status).text}
                    </div>

                    {(selectedSeat.status === 'booked_occupied' || selectedSeat.status === 'booked_empty') && (
                        <div style={{ marginBottom: '25px' }}>
                            <h4 style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px', marginBottom: '15px' }}>ข้อมูลผู้จองปัจจุบัน</h4>
                            <div style={{ lineHeight: '1.8', fontSize: '1rem', color: '#334155', background: '#f8fafc', padding: '15px', borderRadius: '8px' }}>
                                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                    <span style={{color:'#64748b'}}>รหัสนักศึกษา:</span> 
                                    <strong style={{color:'#0f172a'}}>{selectedSeat.studentId}</strong>
                                </div>
                                <div style={{display: 'flex', justifyContent: 'space-between', marginTop: '5px'}}>
                                    <span style={{color:'#64748b'}}>ช่วงเวลา:</span> 
                                    <strong style={{color:'#0f172a'}}>{selectedSeat.time} น.</strong>
                                </div>
                            </div>
                            
                            <div style={{ marginTop: '20px' }}>
                                <div style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '10px', fontWeight: 'bold' }}>ภาพยืนยันตัวตน:</div>
                                {selectedSeat.image ? (
                                    <img 
                                        src={selectedSeat.image} 
                                        alt="Face Scan" 
                                        style={{ 
                                            width: '100%', height: '240px', objectFit: 'cover', backgroundColor: '#f1f5f9', 
                                            borderRadius: '8px', border: '1px solid #e2e8f0',
                                        }} 
                                    />
                                ) : (
                                    <div style={{ width: '100%', height: '200px', backgroundColor: '#f8fafc', display:'flex', alignItems:'center', justifyContent:'center', borderRadius: '8px', color: '#94a3b8', border: '1px dashed #cbd5e1' }}>ไม่มีรูปภาพอ้างอิง</div>
                                )}
                            </div>

                            <button 
                                onClick={() => forceEndBooking(selectedSeat.studentId)}
                                style={{ width: '100%', padding: '12px', marginTop: '20px', backgroundColor: '#fff1f0', color: '#cf1322', border: '1px solid #ffa39e', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', transition: 'background 0.2s' }}
                                onMouseEnter={e => e.currentTarget.style.backgroundColor='#ffccc7'}
                                onMouseLeave={e => e.currentTarget.style.backgroundColor='#fff1f0'}
                            >
                                <RiStopCircleLine size={20} /> บังคับยกเลิกการจอง
                            </button>
                        </div>
                    )}

                    {selectedSeat.status === 'unbooked_occupied' && (
                        <div style={{ backgroundColor: '#fff1f0', padding: '20px', borderRadius: '8px', border: '1px dashed #ffa39e', color: '#cf1322', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiUserForbidFill/> ตรวจพบผู้ลักลอบใช้งาน</strong> <br/>
                            พบว่ามีบุคคลกำลังนั่งอยู่ที่โต๊ะนี้ โดยไม่มีข้อมูลการจองในระบบ ณ เวลาปัจจุบัน
                        </div>
                    )}

                    {selectedSeat.status === 'broken' && (
                        <div style={{ backgroundColor: '#f5f5f5', padding: '20px', borderRadius: '8px', border: '1px dashed #d9d9d9', color: '#595959', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiToolsFill/> เครื่องขัดข้องชั่วคราว</strong> <br/>
                            ที่นั่งนี้ถูกระบุว่าชำรุดในระบบ ไม่สามารถใช้งานได้
                        </div>
                    )}

                    {selectedSeat.status === 'locked' && (
                        <div style={{ backgroundColor: '#f3e8ff', padding: '20px', borderRadius: '8px', border: '1px dashed #d8b4fe', color: '#6b21a8', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '5px'}}><RiLockFill/> ถูกล็อกโดยตารางเรียน</strong> <br/>
                            <div style={{marginTop: '10px'}}>
                                <div><strong style={{color:'#4c1d95'}}>เวลา:</strong> {selectedSeat.time} น.</div>
                                <div><strong style={{color:'#4c1d95'}}>วัตถุประสงค์:</strong> {selectedSeat.studentName}</div>
                            </div>
                        </div>
                    )}

                    <div style={{ marginTop: 'auto', background: '#f8fafc', padding: '15px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                        <h4 style={{ color: '#64748b', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', margin: '0 0 10px 0' }}>สถานะฮาร์ดแวร์</h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1rem', color: '#334155', fontWeight: 'bold' }}>
                            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: selectedSeat.pc_on ? '#52c41a' : '#cbd5e1', boxShadow: '0 0 0 2px white, 0 0 0 3px ' + (selectedSeat.pc_on ? '#b7eb8f' : '#e2e8f0') }}></div>
                            {selectedSeat.pc_on ? 'หน้าจอเปิดใช้งานอยู่' : 'หน้าจอปิดอยู่ (Standby)'}
                        </div>
                    </div>

                </div>
            )}
        </div>
      </div>
    </AdminLayout>
  );
}