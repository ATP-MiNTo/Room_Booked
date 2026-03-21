// src/pages/admin/Monitor.jsx
import { useState, useEffect } from 'react';
import { RiComputerFill, RiUserFill, RiCloseLine } from 'react-icons/ri';
import { PiExclamationMarkFill } from 'react-icons/pi'; 
import AdminLayout from './AdminLayout';

export default function Monitor() {
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // --------------------------------------------------------
  // ✨ อัปเกรดขนาดให้ใหญ่สะใจ สำหรับหน้าจอคอมพิวเตอร์ ✨
  // --------------------------------------------------------
  const size = {
    seat: isMobile ? '45px' : '85px',          // 👈 โต๊ะใหญ่ขึ้นเป็น 85px
    gapWrapper: isMobile ? '20px' : '70px',    // 👈 ระยะห่างซ้าย-ขวา กว้างขึ้น
    gapGrid: isMobile ? '10px' : '20px',       // 👈 ระยะห่างระหว่างโต๊ะ กว้างขึ้น
    icon: isMobile ? 22 : 42,                  // 👈 ไอคอนใหญ่ขึ้น
    fontSize: isMobile ? '11px' : '16px',      // 👈 ตัวหนังสือใหญ่ขึ้น
    containerPadding: isMobile ? '15px' : '40px', 
  };

  const mockLabStatus = {
    1: { status: 'booked_occupied', studentName: 'สมชาย ใจดี', studentId: '1650901111', major: 'วิศวกรรมคอมพิวเตอร์และหุ่นยนต์', time: '09:00 - 10:30', image: 'https://via.placeholder.com/150' },
    2: { status: 'booked_empty', studentName: 'สมหญิง รักเรียน', studentId: '1650902222', major: 'วิศวกรรมไฟฟ้า', time: '09:00 - 11:00', image: 'https://via.placeholder.com/150' },
    3: { status: 'unbooked_occupied' }, 
    4: { status: 'unbooked_empty' },    
    5: { status: 'broken', note: 'จอภาพเปิดไม่ติด แจ้งซ่อมเมื่อวาน' }, 
    ...Array.from({ length: 25 }).reduce((acc, _, i) => ({ ...acc, [i + 6]: { status: 'unbooked_empty' } }), {})
  };

  const Seat = ({ seatNumber }) => {
    const seatData = mockLabStatus[seatNumber] || { status: 'unbooked_empty' };
    const isSelected = selectedSeat?.number === seatNumber;
    
    let iconColor = "#555"; 
    let IconComponent = RiComputerFill;

    if (seatData.status === 'booked_occupied') {
        iconColor = "#4CAF50"; 
        IconComponent = RiUserFill;
    } else if (seatData.status === 'booked_empty') {
        iconColor = "#facc15"; 
        IconComponent = RiUserFill;
    } else if (seatData.status === 'unbooked_occupied') {
        iconColor = "#ef4444"; 
        IconComponent = RiUserFill;
    } else if (seatData.status === 'broken') {
        iconColor = "#9e9e9e"; 
        IconComponent = PiExclamationMarkFill;
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
            position: 'relative',
            animation: seatData.status === 'unbooked_occupied' ? 'pulseRed 2s infinite' : 'none'
        }}
        onMouseEnter={(e) => !isMobile && (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={(e) => !isMobile && (e.currentTarget.style.transform = 'scale(1)')}
      >
        <IconComponent size={size.icon} color={iconColor} />
        <div style={{ fontSize: size.fontSize, marginTop: '4px', fontWeight: 'bold', color: '#555' }}>{seatNumber}</div>
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
        
        {/* ================= ซ้าย: แผนผังห้องแล็บ ================= */}
        <div style={{ flex: 1, padding: isMobile ? '10px' : '30px', overflowY: 'auto', width: '100%' }}>
            
            {/* ✨ จัด Header ให้อยู่ตรงกลางด้วย ✨ */}
            <h2 style={{ marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '15px', fontSize: isMobile ? '1.1rem' : '1.5rem', maxWidth: '950px', margin: '0 auto 25px' }}>
                Live Monitor (สถานะห้องแล็บ B4-302)
            </h2>

            {/* ✨ ผังที่นั่ง (margin: '0 auto' บังคับให้อยู่ตรงกลางเป๊ะ) ✨ */}
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

            {/* ✨ คำอธิบายสัญลักษณ์ (ให้อยู่ตรงกลางด้วย) ✨ */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: isMobile ? '10px' : '25px', marginTop: '25px', flexWrap: 'wrap', backgroundColor: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', maxWidth: isMobile ? '100%' : '950px', margin: '25px auto 50px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserFill color="#4CAF50" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>จอง&นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserFill color="#facc15" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>จอง&ไม่นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserFill color="#ef4444" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>ไม่จอง&นั่ง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><RiComputerFill color="#555" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>ว่าง</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><PiExclamationMarkFill color="#9e9e9e" size={20} /> <span style={{fontSize: isMobile ? '0.85rem' : '1rem', fontWeight: 'bold', color: '#555'}}>เสีย</span></div>
            </div>
        </div>

        {/* ================= ขวา: ลิ้นชักรายละเอียด (Side Panel) ================= */}
        {selectedSeat && (
            <div 
                onClick={() => setSelectedSeat(null)}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 999 }}
            />
        )}

        {/* เปลี่ยนให้ลิ้นชักลอยทับเสมอ (fixed) ทั้งคอมและมือถือ จะได้ไม่ไปดันแผนผังให้เบี้ยว */}
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
                                <div><strong style={{color:'#222'}}>ชื่อ-สกุล:</strong> {selectedSeat.studentName}</div>
                                <div><strong style={{color:'#222'}}>รหัสนักศึกษา:</strong> {selectedSeat.studentId}</div>
                                <div><strong style={{color:'#222'}}>สาขา:</strong> {selectedSeat.major}</div>
                                <div><strong style={{color:'#222'}}>เวลาจอง:</strong> {selectedSeat.time} น.</div>
                            </div>
                            <div style={{ marginTop: '20px' }}>
                                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '10px', fontWeight: 'bold' }}>ภาพสแกนใบหน้าตอนจอง:</div>
                                <img src={selectedSeat.image} alt="Face Scan" style={{ width: '100%', height: '220px', objectFit: 'cover', borderRadius: '10px', border: '1px solid #ddd', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }} />
                            </div>
                        </div>
                    )}

                    {selectedSeat.status === 'unbooked_occupied' && (
                        <div style={{ backgroundColor: '#fff1f0', padding: '20px', borderRadius: '10px', border: '2px dashed #ffccc7', color: '#cf1322', fontSize: '1rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.1rem'}}>⚠️ ตรวจพบการใช้งานโดยไม่มีการจอง</strong> <br/><br/>
                            (พื้นที่แสดงภาพจากกล้องแบบ Real-time เพื่อบันทึกผู้กระทำผิด)
                        </div>
                    )}

                    {selectedSeat.status === 'broken' && (
                        <div style={{ backgroundColor: '#f5f5f5', padding: '20px', borderRadius: '10px', border: '2px dashed #d9d9d9', color: '#595959', fontSize: '1rem', marginBottom: '25px', lineHeight: '1.6' }}>
                            <strong style={{fontSize: '1.1rem'}}>🛠️ หมายเหตุการแจ้งซ่อม:</strong><br/>
                            {selectedSeat.note}
                        </div>
                    )}

                    <div style={{ marginTop: '10px' }}>
                        <h4 style={{ color: '#aaa', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', borderBottom: '2px solid #eee', paddingBottom: '8px', marginBottom: '15px' }}>ภาพจากกล้องวงจรปิด (Live)</h4>
                        <div style={{ width: '100%', height: '180px', backgroundColor: '#e2e8f0', borderRadius: '10px', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#94a3b8', fontSize: '1rem', border: '3px dashed #cbd5e1' }}>
                            [ รอเชื่อมต่อ API กล้อง ]
                        </div>
                    </div>

                </div>
            )}
        </div>

        <style>
            {`
            @keyframes pulseRed {
                0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
                100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
            }
            ::-webkit-scrollbar { width: 8px; height: 8px; }
            ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
            ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
            `}
        </style>
      </div>
    </AdminLayout>
  );
}