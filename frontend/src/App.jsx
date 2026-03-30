// C:\Users\user\Downloads\นิพนธ์\complab-reservation\frontend\src\App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Booking from './pages/Booking';
import BookingHistory from './pages/admin/BookingHistory';
import Login from './pages/admin/Login';
import ProtectedRoute from './components/ProtectedRoute';

import Monitor from './pages/admin/Monitor';
import MonitorMock from './pages/admin/MonitorMock'; // นำเข้าหน้า Monitor โหมดจำลอง

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

        {/* เส้นทางสำหรับหน้า Monitor โหมดจำลอง */}
        <Route 
            path="/admin/monitor-mock" 
            element={ <ProtectedRoute><MonitorMock /></ProtectedRoute> } 
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