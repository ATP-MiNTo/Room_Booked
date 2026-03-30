// C:\Users\user\Downloads\นิพนธ์\complab-reservation\frontend\src\pages\admin\BookingHistory.jsx
import { useState, useEffect } from 'react';
import AdminLayout from './AdminLayout'; 

export default function BookingHistory() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({
    studentId: '', bookingDate: '', startTime: '', endTime: '', branch: ''
  });

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await fetch('/reservations');
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (error) {
      console.error("เกิดข้อผิดพลาดในการดึงข้อมูล:", error);
    }
  };

  const handleFilterChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const resetFilter = () => {
    setFilters({ studentId: '', bookingDate: '', startTime: '', endTime: '', branch: '' });
  };

  // ระบบกรองข้อมูลที่แก้ไขให้ทำงานได้จริงแล้ว
  const filteredLogs = logs.filter(log => {
    const matchStudent = !filters.studentId || log.student_id?.toLowerCase().includes(filters.studentId.toLowerCase());
    const matchDate = !filters.bookingDate || log.reserve_date === filters.bookingDate;
    const matchStartTime = !filters.startTime || log.start_time >= filters.startTime;
    const matchEndTime = !filters.endTime || log.end_time <= filters.endTime;
    
    // ปิดการกรองสาขาไว้ก่อน เพราะ API ยังไม่มีการ Join ข้อมูลสาขามาให้
    const matchBranch = true; 

    return matchStudent && matchDate && matchStartTime && matchEndTime && matchBranch;
  });

  return (
    <AdminLayout>
      <div style={styles.container}>
        <div style={styles.title}>Booking Logs (ประวัติการจอง)</div>

        <div style={styles.filterBar}>
          <input type="text" name="studentId" placeholder="รหัสนักศึกษา" value={filters.studentId} onChange={handleFilterChange} style={styles.input} />
          
          <input type="date" name="bookingDate" value={filters.bookingDate} onChange={handleFilterChange} style={styles.input} />
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontSize: '14px', color: '#555' }}>ตั้งแต่เวลา:</span>
            <input type="time" name="startTime" value={filters.startTime} onChange={handleFilterChange} style={styles.input} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontSize: '14px', color: '#555' }}>ถึงเวลา:</span>
            <input type="time" name="endTime" value={filters.endTime} onChange={handleFilterChange} style={styles.input} />
          </div>
          
          <button onClick={resetFilter} style={{...styles.button, ...styles.resetBtn}}>รีเซ็ต (Reset)</button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>รหัสนักศึกษา</th>
                <th style={styles.th}>ที่นั่ง</th>
                <th style={styles.th}>วันที่จอง</th>
                <th style={styles.th}>เวลาเริ่ม</th>
                <th style={styles.th}>เวลาจบ</th>
                <th style={styles.th}>รูปภาพยืนยัน</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log, index) => (
                <tr key={index}>
                  <td style={styles.td}>{log.student_id}</td>
                  <td style={styles.td}>โต๊ะ {log.seat_id}</td>
                  <td style={styles.td}>{log.reserve_date}</td>
                  <td style={styles.td}>{log.start_time}</td>
                  <td style={styles.td}>{log.end_time}</td>
                  <td style={styles.td}>
                    {/* แก้ไขลิงก์รูปภาพให้ถูกต้องตามที่เราทำกันในหน้า Monitor */}
                    {log.image_filename ? (
                      <img 
                        src={`/data/face_scanner/${log.reserve_date}/${log.image_filename}`} 
                        alt="Face Scan" 
                        style={{ width: '80px', height: '80px', objectFit: 'contain', backgroundColor: '#f0f2f5', borderRadius: '8px', border: '1px solid #ddd' }}
                        onError={(e) => { e.target.src = 'https://via.placeholder.com/80?text=No+Image' }} 
                      />
                    ) : (
                      <span style={{color: '#999', fontSize: '0.9rem'}}>ไม่มีรูปภาพ</span>
                    )}
                  </td>
                </tr>
              ))}
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan="6" style={{...styles.td, textAlign: 'center', color: '#888'}}>ไม่พบข้อมูลการจอง</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}

const styles = {
  container: { background: 'white', padding: '30px', borderRadius: '15px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', maxWidth: '1200px', margin: '0 auto' },
  title: { fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '25px', color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '15px' },
  filterBar: { display: 'flex', gap: '15px', flexWrap: 'wrap', marginBottom: '25px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '10px' },
  input: { padding: '10px 12px', border: '1px solid #ddd', borderRadius: '8px', outline: 'none', fontSize: '0.95rem', flex: '1 1 auto', minWidth: '150px' },
  button: { padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'all 0.2s' },
  resetBtn: { background: '#e0e0e0', color: '#333' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#f8f9fa', textAlign: 'left', padding: '15px', borderBottom: '2px solid #eee', color: '#2c3e50', fontSize: '1rem', whiteSpace: 'nowrap' },
  td: { padding: '15px', borderBottom: '1px solid #f0f0f0', verticalAlign: 'middle', color: '#555' }
};