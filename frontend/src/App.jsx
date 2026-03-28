// C:\Users\user\Downloads\นิพนธ์\complab-reservation\frontend\src\App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Booking from './pages/Booking';
import BookingHistory from './pages/admin/BookingHistory';
import Login from './pages/admin/Login';
import ProtectedRoute from './components/ProtectedRoute';

// สวิตช์สลับโหมด (ให้เปิดใช้งานแค่อันใดอันหนึ่ง) 
/* โหมดทดสอบอยู่ (มีแผงสีชมพู) */
// import Monitor from './pages/admin/MonitorMock';
/* โหมดจริง */
import Monitor from './pages/admin/Monitor';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* หน้าสำหรับผู้ใช้ทั่วไป (นักศึกษา) */}
        <Route path="/" element={<Booking />} />
        
        {/* หน้า Login สำหรับ Admin */}
        <Route path="/admin/login" element={<Login />} />
        
        {/* กลุ่มหน้าจอ Admin ที่โดนล็อคประตู (ต้อง Login ก่อน) */}
        <Route 
            path="/admin" 
            element={ <ProtectedRoute><Navigate to="/admin/monitor" replace /></ProtectedRoute> } 
        />
        
        <Route 
            path="/admin/monitor" 
            element={ <ProtectedRoute><Monitor /></ProtectedRoute> } 
        />
        
        <Route 
            path="/admin/booking-history" 
            element={ <ProtectedRoute><BookingHistory /></ProtectedRoute> } 
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;