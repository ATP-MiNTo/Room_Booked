import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  RiMenuFoldLine, RiMenuUnfoldLine,
  RiDashboardLine, RiFileList3Line,
  RiLogoutBoxRLine, RiMenuLine,
  RiGroupLine, RiSettings4Line, RiDatabase2Line,
  RiBarChartBoxLine, RiUserFill
} from 'react-icons/ri';

const MENU_ITEMS = [
  { name: 'Live Monitor',       icon: <RiDashboardLine size={24} />,   path: '/admin/monitor' },
  { name: 'Analytics',          icon: <RiBarChartBoxLine size={24} />, path: '/admin/stats' },
  { name: 'Booking History',    icon: <RiFileList3Line size={24} />,   path: '/admin/booking-history' },
  { name: 'Student Info',       icon: <RiGroupLine size={24} />,       path: '/admin/student-info' },
  { name: 'Backup & Migration', icon: <RiDatabase2Line size={24} />,   path: '/admin/backup-restore' },
  { name: 'Settings',           icon: <RiSettings4Line size={24} />,   path: '/admin/system-manage' },
];

const SYSTEM_NAME = 'ระบบจองห้อง Complab';

export default function AdminLayout({ children }) {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [isSidebarOpen, setIsSidebarOpen] = useState(!isMobile);
  const navigate = useNavigate();
  const location = useLocation();

  const adminId   = sessionStorage.getItem('adminId')   || 'Unknown';
  const adminName = sessionStorage.getItem('adminName') || `Admin (${adminId})`;

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setIsSidebarOpen(!mobile);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const sidebarWidth = isMobile
    ? (isSidebarOpen ? '260px' : '0px')
    : (isSidebarOpen ? '260px' : '80px');

  const handleLogout = () => {
    sessionStorage.removeItem('adminToken');
    sessionStorage.removeItem('adminId');
    sessionStorage.removeItem('adminName');
    navigate('/admin/login');
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#f3f4f6', overflow: 'hidden', position: 'relative' }}>

      {isMobile && isSidebarOpen && (
        <div
          onClick={() => setIsSidebarOpen(false)}
          style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 10 }}
        />
      )}

      <div style={{
        width: sidebarWidth, backgroundColor: '#1e1e2d', color: 'white',
        transition: 'width 0.3s ease', display: 'flex', flexDirection: 'column',
        boxShadow: '4px 0 10px rgba(0,0,0,0.1)', zIndex: 20,
        position: isMobile ? 'fixed' : 'relative', height: '100%',
        overflow: 'hidden', whiteSpace: 'nowrap',
      }}>

        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: (isSidebarOpen && !isMobile) ? 'space-between' : 'center',
          padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          {isSidebarOpen && (
            <div style={{ fontSize: '1rem', fontWeight: 'bold', marginLeft: isMobile ? '10px' : '0', lineHeight: 1.3 }}>
              {SYSTEM_NAME}
            </div>
          )}
          {!isMobile && (
            <div onClick={() => setIsSidebarOpen(!isSidebarOpen)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
              {isSidebarOpen ? <RiMenuFoldLine size={24} /> : <RiMenuUnfoldLine size={24} />}
            </div>
          )}
        </div>

        <div style={{ flex: 1, padding: '20px 0', overflowY: 'auto' }}>
          {MENU_ITEMS.map((item) => {
            const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');
            return (
              <div
                key={item.path}
                onClick={() => { navigate(item.path); if (isMobile) setIsSidebarOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center',
                  justifyContent: (isSidebarOpen || isMobile) ? 'flex-start' : 'center',
                  padding: '15px 20px', cursor: 'pointer',
                  backgroundColor: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                  borderLeft: isActive ? '4px solid #1677ff' : '4px solid transparent',
                  transition: 'background 0.2s', marginBottom: '5px',
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = isActive ? 'rgba(255,255,255,0.1)' : 'transparent'}
              >
                <div style={{ minWidth: '30px', display: 'flex', justifyContent: 'center', color: isActive ? '#1677ff' : 'white' }}>
                  {item.icon}
                </div>
                {isSidebarOpen && (
                  <div style={{ marginLeft: '15px', fontSize: '1rem', color: isActive ? '#1677ff' : 'white', fontWeight: isActive ? 'bold' : 'normal' }}>
                    {item.name}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: (isSidebarOpen || isMobile) ? 'space-between' : 'center',
          padding: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', gap: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#1677ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <RiUserFill size={20} />
            </div>
            {isSidebarOpen && (
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: 'white', overflow: 'hidden', textOverflow: 'ellipsis' }}>{adminName}</div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>{adminId}</div>
              </div>
            )}
          </div>
          {isSidebarOpen && (
            <div
              onClick={handleLogout}
              title="ออกจากระบบ"
              style={{ cursor: 'pointer', color: 'rgba(255,255,255,0.5)', flexShrink: 0 }}
              onMouseEnter={(e) => e.currentTarget.style.color = '#ff4d4f'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(255,255,255,0.5)'}
            >
              <RiLogoutBoxRLine size={20} />
            </div>
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {isMobile && (
          <div style={{ display: 'flex', alignItems: 'center', padding: '15px 20px', backgroundColor: 'white', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', zIndex: 5 }}>
            <div onClick={() => setIsSidebarOpen(true)} style={{ cursor: 'pointer', marginRight: '15px' }}>
              <RiMenuLine size={24} />
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{SYSTEM_NAME}</div>
          </div>
        )}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {children}
        </div>
      </div>
    </div>
  );
}