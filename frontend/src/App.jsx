import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Booking from './pages/Booking';
import BookingHistory from './pages/admin/BookingHistory';
import Login from './pages/admin/Login';
import ProtectedRoute from './components/ProtectedRoute';

import Monitor from './pages/admin/Monitor';
import MonitorMock from './pages/admin/MonitorMock';
import StudentInfo from './pages/admin/StudentInfo';
import SystemManage from './pages/admin/SystemManage';
import BackupRestore from './pages/admin/BackupRestore';
import Analytics from './pages/admin/Analytics';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Booking />} />
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<ProtectedRoute><Navigate to="/admin/monitor" replace /></ProtectedRoute>} />
        <Route path="/admin/monitor" element={<ProtectedRoute><Monitor /></ProtectedRoute>} />
        <Route path="/admin/monitor-mock" element={<ProtectedRoute><MonitorMock /></ProtectedRoute>} />
        <Route path="/admin/booking-history" element={<ProtectedRoute><BookingHistory /></ProtectedRoute>} />
        <Route path="/admin/student-info" element={<ProtectedRoute><StudentInfo /></ProtectedRoute>} />
        <Route path="/admin/system-manage" element={<ProtectedRoute><SystemManage /></ProtectedRoute>} />
        <Route path="/admin/backup-restore" element={<ProtectedRoute><BackupRestore /></ProtectedRoute>} />
        <Route path="/admin/stats" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
