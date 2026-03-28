// src/pages/admin/Login.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RiUserLine, RiLockLine, RiEyeLine, RiEyeOffLine, RiArrowLeftLine } from 'react-icons/ri';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  // -----------------------------------------------------------
  // 🚧 ฟังก์ชันแอบดัก (Mock Login) สำหรับทดสอบหน้าตา 🚧
  // (พอฝั่ง Backend ทำ API เสร็จ เราค่อยมาแก้ตรงนี้ครับ)
  // -----------------------------------------------------------
  const handleMockLogin = (e) => {
    e.preventDefault(); // ป้องกันหน้าเว็บรีเฟรช
    setErrorMessage(''); // เคลียร์ข้อความ Error เก่า

    // สมมติรหัสผ่านไว้เทสต์
    if (username === 'admin' && password === '1234') {
        console.log('Login Success (Mock)!');
        // เอา Token สมมติไปเก็บในเครื่อง (เพื่อให้ App.jsx รู้ว่า Login แล้ว)
        sessionStorage.setItem('adminToken', 'mock_token_12345');
        // เด้งไปหน้า Monitor อัตโนมัติ
        navigate('/admin/monitor');
    } else {
        console.log('Login Failed (Mock)!');
        setErrorMessage('ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง (ลองใช้: admin / 1234)');
    }
  };

  // ✅ สไตล์ของ Input Field พร้อมไอคอน
  const inputGroupStyle = {
    position: 'relative', marginBottom: '20px', display: 'flex', alignItems: 'center'
  };

  const inputIconStyle = {
    position: 'absolute', left: '15px', color: '#888'
  };

  const inputStyle = {
    width: '100%', padding: '12px 15px 12px 45px', border: '1px solid #ddd',
    borderRadius: '8px', fontSize: '1rem', outline: 'none', transition: 'border-color 0.2s',
    boxSizing: 'border-box'
  };

  return (
    <div style={{ 
        display: 'flex', height: '100vh', 
        backgroundColor: '#1a1a2e', // สีพื้นหลังเข้มๆ แบบ Tech
        justifyContent: 'center', alignItems: 'center', padding: '20px'
    }}>
      {/* กล่อง Form ขาวๆ ตรงกลาง */}
      <form onSubmit={handleMockLogin} style={{ 
          backgroundColor: 'white', padding: '40px', borderRadius: '15px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.3)', width: '100%', maxWidth: '380px'
      }}>
        
        {/* หัวข้อ */}
        <div style={{ textAlign: 'center', marginBottom: '35px' }}>
            <h2 style={{ margin: 0, color: '#2c3e50', fontSize: '1.6rem' }}>Admin Panel</h2>
            <div style={{ fontSize: '0.9rem', color: '#888', marginTop: '5px' }}>กรุณาเข้าสู่ระบบเพื่อจัดการห้องปฏิบัติการ</div>
        </div>

        {/* แสดงข้อความ Error */}
        {errorMessage && (
            <div style={{ 
                backgroundColor: '#fff1f0', color: '#cf1322', padding: '12px', 
                borderRadius: '8px', border: '1px solid #ffccc7', marginBottom: '20px',
                fontSize: '0.9rem', textAlign: 'center'
            }}>
                {errorMessage}
            </div>
        )}

        {/* ช่อง Username */}
        <div style={inputGroupStyle}>
            <RiUserLine size={20} style={inputIconStyle} />
            <input 
                type="text" placeholder="ชื่อผู้ใช้งาน" required
                value={username} onChange={(e) => setUsername(e.target.value)}
                style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = '#1677ff'}
                onBlur={(e) => e.target.style.borderColor = '#ddd'}
            />
        </div>

        {/* ช่อง Password */}
        <div style={inputGroupStyle}>
            <RiLockLine size={20} style={inputIconStyle} />
            <input 
                type={showPassword ? "text" : "password"} placeholder="รหัสผ่าน" required
                value={password} onChange={(e) => setPassword(e.target.value)}
                style={{ ...inputStyle, paddingRight: '45px' }} // เผื่อที่ให้ปุ่มตา
                onFocus={(e) => e.target.style.borderColor = '#1677ff'}
                onBlur={(e) => e.target.style.borderColor = '#ddd'}
            />
            {/* ปุ่มเปิด/ปิดตาดูรหัส */}
            <div 
                onClick={() => setShowPassword(!showPassword)} 
                style={{ position: 'absolute', right: '15px', color: '#888', cursor: 'pointer', display: 'flex' }}>
                {showPassword ? <RiEyeOffLine size={20} /> : <RiEyeLine size={20} />}
            </div>
        </div>

        {/* ปุ่ม Login */}
        <button 
            type="submit"
            style={{ 
                width: '100%', padding: '12px', backgroundColor: '#1677ff', 
                color: 'white', border: 'none', borderRadius: '8px', fontSize: '1rem',
                fontWeight: 'bold', cursor: 'pointer', transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#4096ff'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#1677ff'}
        >
            เข้าสู่ระบบ
        </button>

        {/* ปุ่มกลับหน้าหลัก */}
        <div 
          onClick={() => navigate('/')}
          style={{ 
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginTop: '25px', color: '#888', fontSize: '0.9rem', cursor: 'pointer', gap: '5px' 
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = '#1677ff'}
          onMouseLeave={(e) => e.currentTarget.style.color = '#888'}
        >
          <RiArrowLeftLine size={18} /> กลับหน้าจองที่นั่ง (นักศึกษา)
        </div>

      </form>
    </div>
  );
}