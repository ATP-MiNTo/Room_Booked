// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Booking from './pages/Booking';
import BookingLogs from './pages/admin/BookingLogs'; 
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* หน้าสำหรับผู้ใช้ทั่วไป (นักศึกษา) */}
        <Route path="/" element={<Booking />} />
        
        {/* หน้าสำหรับ Admin */}
        <Route path="/admin" element={<BookingLogs />} /> {/*  */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;