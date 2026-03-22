// src/pages/admin/AdminLayout.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  RiMenuFoldLine, RiMenuUnfoldLine, 
  RiDashboardLine, RiFileList3Line, 
  RiLogoutBoxRLine, RiMenuLine 
} from 'react-icons/ri';

export default function AdminLayout({ children }) {
  // ตรวจสอบขนาดหน้าจอตอนเริ่มต้น
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  // ถ้าเป็นมือถือ ให้ซ่อนเมนูไว้ก่อน
  const [isSidebarOpen, setIsSidebarOpen] = useState(!isMobile);
  const navigate = useNavigate();

  // อัปเดตสถานะมือถือ/คอม อัตโนมัติเวลาย่อขยายจอ
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setIsSidebarOpen(!mobile);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // คำนวณความกว้าง: มือถือซ่อนเหลือ 0px, คอมพิวเตอร์ย่อเหลือ 80px
  const sidebarWidth = isMobile ? (isSidebarOpen ? '260px' : '0px') : (isSidebarOpen ? '260px' : '80px');

  const menuItems = [
    { name: 'Booking History', icon: <RiFileList3Line size={24} />, path: '/admin/booking-history' },
    { name: 'Live Monitor', icon: <RiDashboardLine size={24} />, path: '/admin/monitor' },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#f3f4f6', overflow: 'hidden', position: 'relative' }}>
      
      {/* ✨ พื้นหลังสีดำจางๆ บนมือถือเวลาเปิดเมนู ✨ */}
      {isMobile && isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)}
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 10
          }}
        />
      )}

      {/* 🟢 Sidebar ด้านซ้าย */}
      <div style={{ 
        width: sidebarWidth, 
        backgroundColor: '#1e1e2d', 
        color: 'white', 
        transition: 'width 0.3s ease',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '4px 0 10px rgba(0,0,0,0.1)',
        zIndex: 20,
        position: isMobile ? 'fixed' : 'relative', // บนมือถือให้ลอยทับ
        height: '100%',
        overflow: 'hidden',
        whiteSpace: 'nowrap'
      }}>
        {/* ส่วนหัว Sidebar */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: (isSidebarOpen && !isMobile) ? 'space-between' : 'center',
          padding: '20px',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          {isSidebarOpen && <div style={{ fontSize: '1.2rem', fontWeight: 'bold', marginLeft: isMobile ? '10px' : '0' }}>Admin Panel</div>}
          {!isMobile && (
            <div 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
              style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            >
              {isSidebarOpen ? <RiMenuFoldLine size={24} /> : <RiMenuUnfoldLine size={24} />}
            </div>
          )}
        </div>

        {/* รายการเมนู */}
        <div style={{ flex: 1, padding: '20px 0' }}>
          {menuItems.map((item, index) => (
            <div 
              key={index}
              onClick={() => { 
                navigate(item.path);
                if (isMobile) setIsSidebarOpen(false); // กดปุ๊บ ซ่อนเมนูออโต้
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: (isSidebarOpen || isMobile) ? 'flex-start' : 'center',
                padding: '15px 20px',
                cursor: 'pointer',
                backgroundColor: window.location.pathname === item.path ? 'rgba(255,255,255,0.1)' : 'transparent',
                borderLeft: window.location.pathname === item.path ? '4px solid #4CAF50' : '4px solid transparent',
                transition: 'background 0.2s',
                marginBottom: '5px'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = window.location.pathname === item.path ? 'rgba(255,255,255,0.1)' : 'transparent'}
            >
              <div style={{ minWidth: '30px', display: 'flex', justifyContent: 'center' }}>{item.icon}</div>
              {isSidebarOpen && <div style={{ marginLeft: '15px', fontSize: '1rem' }}>{item.name}</div>}
            </div>
          ))}
        </div>

        {/* ปุ่มออกจากระบบ */}
        <div 
          onClick={() => {
            localStorage.removeItem('adminToken'); // 🗑️ ฉีกบัตรผ่านทิ้ง
            navigate('/admin/login'); // 🏃‍♂️ เด้งกลับไปหน้า Login
          }}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: (isSidebarOpen || isMobile) ? 'flex-start' : 'center',
            padding: '20px', cursor: 'pointer', borderTop: '1px solid rgba(255,255,255,0.1)',
            color: '#ff6b6b'
          }}
        >
          <div style={{ minWidth: '30px', display: 'flex', justifyContent: 'center' }}><RiLogoutBoxRLine size={24} /></div>
          {isSidebarOpen && <div style={{ marginLeft: '15px', fontWeight: 'bold' }}>ออกจากระบบ</div>}
        </div>
      </div>

      {/* ⚪️ พื้นที่ Content ด้านขวา */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        
        {/* ✨ แถบเมนูจำลองสำหรับมือถือ (จะโผล่มาเฉพาะจอมือถือ) ✨ */}
        {isMobile && (
          <div style={{ padding: '15px 20px', backgroundColor: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', display: 'flex', alignItems: 'center', zIndex: 5 }}>
            <RiMenuLine size={24} onClick={() => setIsSidebarOpen(true)} style={{ cursor: 'pointer', color: '#2c3e50' }} />
            <span style={{ marginLeft: '15px', fontWeight: 'bold', fontSize: '1.1rem', color: '#2c3e50' }}>Admin Panel</span>
          </div>
        )}
        
        {/* ส่วนเนื้อหาหลัก */}
        <div style={{ flex: 1, padding: isMobile ? '10px' : '30px', overflowY: 'auto' }}>
          {children}
        </div>

      </div>

    </div>
  );
}