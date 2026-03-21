// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// นำเข้าหน้าเว็บต่างๆ ที่เราสร้างไว้ในโฟลเดอร์ pages
import Booking from './pages/Booking';
import BookingLogs from './pages/admin/BookingLogs';
import Monitor from './pages/admin/Monitor';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* หน้าสำหรับผู้ใช้ทั่วไป (นักศึกษา) */}
        <Route path="/" element={<Booking />} />
        
        {/* หน้าตารางประวัติการจอง สำหรับ Admin */}
        <Route path="/admin" element={<BookingLogs />} />
        
        {/* หน้า Live Monitor สรุปสถานะห้อง สำหรับ Admin */}
        <Route path="/admin/monitor" element={<Monitor />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;