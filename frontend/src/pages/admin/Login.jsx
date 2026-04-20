import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RiUserLine, RiLockLine, RiEyeLine, RiEyeOffLine, RiArrowLeftLine } from 'react-icons/ri';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (response.ok) {
        const data = await response.json();
        
        sessionStorage.setItem('adminToken', data.token);
        sessionStorage.setItem('adminId', data.admin_id);
        sessionStorage.setItem('adminName', data.admin_name);
        
        navigate('/admin/monitor');
      } else {
        const errorData = await response.json();
        setErrorMessage(typeof errorData.detail === 'string' ? errorData.detail : 'ชื่อผู้ใช้งาน หรือรหัสผ่านไม่ถูกต้อง');
      }
    } catch (error) {
      setErrorMessage('ไม่สามารถติดต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่อีกครั้ง');
    } finally {
      setIsLoading(false);
    }
  };

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
        backgroundColor: '#1a1a2e', 
        justifyContent: 'center', alignItems: 'center', padding: '20px'
    }}>
      
      {/* 🟢 เพิ่ม Style สำหรับซ่อนไอคอนดวงตาเริ่มต้นของเบราว์เซอร์ Edge/Chrome */}
      <style>
          {`
            input[type="password"]::-ms-reveal,
            input[type="password"]::-ms-clear,
            input[type="password"]::-webkit-reveal {
              display: none !important;
            }
          `}
      </style>

      <form onSubmit={handleLogin} style={{ 
          backgroundColor: 'white', padding: '40px', borderRadius: '15px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.3)', width: '100%', maxWidth: '380px'
      }}>
        
        <div style={{ textAlign: 'center', marginBottom: '35px' }}>
            <h2 style={{ margin: 0, color: '#2c3e50', fontSize: '1.6rem' }}>Admin Panel</h2>
            <div style={{ fontSize: '0.9rem', color: '#888', marginTop: '5px' }}>กรุณาเข้าสู่ระบบเพื่อจัดการห้องปฏิบัติการ</div>
        </div>

        {errorMessage && (
            <div style={{ 
                backgroundColor: '#fff1f0', color: '#cf1322', padding: '12px', 
                borderRadius: '8px', border: '1px solid #ffccc7', marginBottom: '20px',
                fontSize: '0.9rem', textAlign: 'center'
            }}>
                {errorMessage}
            </div>
        )}

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

        <div style={inputGroupStyle}>
            <RiLockLine size={20} style={inputIconStyle} />
            <input 
                type={showPassword ? "text" : "password"} placeholder="รหัสผ่าน" required
                value={password} onChange={(e) => setPassword(e.target.value)}
                style={{ ...inputStyle, paddingRight: '45px' }} 
                onFocus={(e) => e.target.style.borderColor = '#1677ff'}
                onBlur={(e) => e.target.style.borderColor = '#ddd'}
            />
            <div 
                onClick={() => setShowPassword(!showPassword)} 
                style={{ position: 'absolute', right: '15px', color: '#888', cursor: 'pointer', display: 'flex' }}>
                {showPassword ? <RiEyeOffLine size={20} /> : <RiEyeLine size={20} />}
            </div>
        </div>

        <button 
            type="submit"
            disabled={isLoading}
            style={{ 
                width: '100%', padding: '12px', backgroundColor: isLoading ? '#ccc' : '#1677ff', 
                color: 'white', border: 'none', borderRadius: '8px', fontSize: '1rem',
                fontWeight: 'bold', cursor: isLoading ? 'not-allowed' : 'pointer', transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#4096ff')}
            onMouseLeave={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#1677ff')}
        >
            {isLoading ? 'กำลังเข้าสู่ระบบ...' : 'เข้าสู่ระบบ'}
        </button>

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