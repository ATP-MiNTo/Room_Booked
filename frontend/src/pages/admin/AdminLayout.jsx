// src/pages/admin/AdminLayout.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  RiMenuFoldLine, RiMenuUnfoldLine, 
  RiDashboardLine, RiFileList3Line, 
  RiLogoutBoxRLine 
} from 'react-icons/ri';

export default function AdminLayout({ children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const navigate = useNavigate();

  // ความกว้างของ Sidebar ตอนเปิดและปิด
  const sidebarWidth = isSidebarOpen ? '260px' : '80px';

  const menuItems = [
    { name: 'แดชบอร์ด', icon: <RiDashboardLine size={24} />, path: '#' },
    { name: 'ประวัติการจอง', icon: <RiFileList3Line size={24} />, path: '/admin' },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#f3f4f6', overflow: 'hidden' }}>
      
      {/* 🟢 Sidebar ด้านซ้าย */}
      <div style={{ 
        width: sidebarWidth, 
        backgroundColor: '#1e1e2d', // สีน้ำเงินเข้ม/ดำ แบบในรูปตัวอย่าง
        color: 'white', 
        transition: 'width 0.3s ease',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '4px 0 10px rgba(0,0,0,0.1)',
        zIndex: 10
      }}>
        {/* ส่วนหัว Sidebar (โลโก้ + ปุ่มยุบ/ขยาย) */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: isSidebarOpen ? 'space-between' : 'center',
          padding: '20px',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          {isSidebarOpen && <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>Admin Panel</div>}
          <div 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            title={isSidebarOpen ? "ยุบเมนู" : "ขยายเมนู"}
          >
            {isSidebarOpen ? <RiMenuFoldLine size={24} /> : <RiMenuUnfoldLine size={24} />}
          </div>
        </div>

        {/* รายการเมนู */}
        <div style={{ flex: 1, padding: '20px 0' }}>
          {menuItems.map((item, index) => (
            <div 
              key={index}
              onClick={() => { if(item.path !== '#') navigate(item.path) }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: isSidebarOpen ? 'flex-start' : 'center',
                padding: '15px 20px',
                cursor: 'pointer',
                backgroundColor: item.path === '/admin' ? 'rgba(255,255,255,0.1)' : 'transparent', // ไฮไลท์หน้าปัจจุบัน
                borderLeft: item.path === '/admin' ? '4px solid #4CAF50' : '4px solid transparent',
                transition: 'background 0.2s',
                marginBottom: '5px'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = item.path === '/admin' ? 'rgba(255,255,255,0.1)' : 'transparent'}
            >
              <div style={{ minWidth: '30px', display: 'flex', justifyContent: 'center' }}>{item.icon}</div>
              {isSidebarOpen && <div style={{ marginLeft: '15px', fontSize: '1rem' }}>{item.name}</div>}
            </div>
          ))}
        </div>

        {/* ปุ่มออกจากระบบ (กลับไปหน้าหลัก) */}
        <div 
          onClick={() => navigate('/')}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center',
            padding: '20px', cursor: 'pointer', borderTop: '1px solid rgba(255,255,255,0.1)',
            color: '#ff6b6b'
          }}
        >
          <div style={{ minWidth: '30px', display: 'flex', justifyContent: 'center' }}><RiLogoutBoxRLine size={24} /></div>
          {isSidebarOpen && <div style={{ marginLeft: '15px', fontWeight: 'bold' }}>ออกจากระบบ</div>}
        </div>
      </div>

      {/* ⚪️ พื้นที่ Content ด้านขวา */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '30px' }}>
        {children} {/* 👈 ตรงนี้คือจุดที่จะเอาหน้าตาราง BookingLogs มาเสียบ */}
      </div>

    </div>
  );
}