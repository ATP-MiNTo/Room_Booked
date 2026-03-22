// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// นำเข้าหน้าเว็บต่างๆ
import Booking from './pages/Booking';
import BookingHistory from './pages/admin/BookingHistory';
import Monitor from './pages/admin/Monitor';
import Login from './pages/admin/Login';

// ✨ นำเข้ายามเฝ้าประตู ✨
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* หน้าสำหรับผู้ใช้ทั่วไป (นักศึกษา) - เข้าได้อิสระ */}
        <Route path="/" element={<Booking />} />
        
        {/* หน้า Login สำหรับ Admin - เข้าได้อิสระ */}
        <Route path="/admin/login" element={<Login />} />
        
        {/* 🔒 กลุ่มหน้าจอ Admin ที่โดนล็อคประตู (ต้องมี Token เท่านั้น) 🔒 */}
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