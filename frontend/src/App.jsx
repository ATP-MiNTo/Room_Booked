// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'; // 👈 เพิ่ม Navigate
import Booking from './pages/Booking';
import BookingHistory from './pages/admin/BookingHistory'; // 👈 เปลี่ยนชื่อไฟล์
import Monitor from './pages/admin/Monitor';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* หน้าสำหรับผู้ใช้ทั่วไป (นักศึกษา) */}
        <Route path="/" element={<Booking />} />
        
        {/* หน้า Admin Routes */}
        {/* ถ้าเข้า URL /admin เฉยๆ ให้เด้งไปหน้า monitor อัตโนมัติ */}
        <Route path="/admin" element={<Navigate to="/admin/monitor" replace />} />
        
        {/* หน้า Live Monitor (สรุปสถานะห้อง) */}
        <Route path="/admin/monitor" element={<Monitor />} />
        
        {/* หน้าประวัติการจอง (Booking History) */}
        <Route path="/admin/booking-history" element={<BookingHistory />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;