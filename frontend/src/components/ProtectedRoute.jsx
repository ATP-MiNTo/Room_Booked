// src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children }) {
  // ลองค้นหาบัตรผ่าน (Token) ในกระเป๋า (localStorage) ของเบราว์เซอร์
  const token = sessionStorage.getItem('adminToken');
  
  // ถ้าไม่มีบัตรผ่าน ให้เด้งไปหน้า Login อัตโนมัติ
  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }
  
  // ถ้ามีบัตรผ่าน ก็ปล่อยให้เข้าไปดูหน้าจอ (children) ได้ตามปกติ
  return children;
}