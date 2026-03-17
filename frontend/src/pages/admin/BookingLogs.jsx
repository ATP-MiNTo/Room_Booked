import { useState, useEffect } from 'react';
import AdminLayout from './AdminLayout'; 

export default function BookingLogs() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({
    date: '', studentId: '', bookingDate: '', time: '', branch: ''
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
    setFilters({ date: '', studentId: '', bookingDate: '', time: '', branch: '' });
  };

  const filteredLogs = logs.filter(log => {
    return log.student_id?.includes(filters.studentId) || true; 
  });

  return (
    // สวม AdminLayout ครอบเนื้อหาทั้งหมดไว้
    <AdminLayout>
      <div style={styles.container}>
        <div style={styles.title}>Booking Logs (ประวัติการจอง)</div>

        <div style={styles.filterBar}>
          <input type="date" name="date" value={filters.date} onChange={handleFilterChange} style={styles.input} />
          <input type="text" name="studentId" placeholder="รหัสนักศึกษา" value={filters.studentId} onChange={handleFilterChange} style={styles.input} />
          <input type="date" name="bookingDate" value={filters.bookingDate} onChange={handleFilterChange} style={styles.input} />
          <input type="time" name="time" value={filters.time} onChange={handleFilterChange} style={styles.input} />
          
          <select name="branch" value={filters.branch} onChange={handleFilterChange} style={styles.input}>
            <option value="">สาขา</option>
            <option>วิศวกรรมไฟฟ้า</option>
            <option>วิศวกรรมปัญญาประดิษฐ์และวิทยาการข้อมูล</option>
            <option>วิศวกรรมคอมพิวเตอร์และหุ่นยนต์</option>
            <option>วิศวกรรมมัลติมีเดียและเอ็นเตอร์เทนเมนต์</option>
          </select>

          <button onClick={resetFilter} style={{...styles.button, ...styles.resetBtn}}>Reset</button>
          <button onClick={() => console.log("กำลังค้นหา:", filters)} style={{...styles.button, ...styles.queryBtn}}>Query</button>
        </div>

        <table style={styles.table}>
          <thead>
            <tr>
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
                <td style={styles.td}>โต๊ะ {log.seat_id}</td>
                <td style={styles.td}>{log.reserve_date}</td>
                <td style={styles.td}>{log.start_time}</td>
                <td style={styles.td}>{log.end_time}</td>
                <td style={styles.td}>
                  {log.image_path ? (
                    <img 
                      src={log.image_path} 
                      alt="Face Scan" 
                      style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '8px' }}
                      onError={(e) => { e.target.src = 'https://via.placeholder.com/80?text=No+Image' }} 
                    />
                  ) : (
                    <span style={{color: '#999'}}>ไม่มีรูปภาพ</span>
                  )}
                </td>
              </tr>
            ))}
            {filteredLogs.length === 0 && (
              <tr>
                <td colSpan="5" style={{...styles.td, textAlign: 'center', color: '#888'}}>ไม่พบข้อมูลการจอง</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </AdminLayout>
  );
}

const styles = {
  container: { background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  title: { fontSize: '24px', fontWeight: 'bold', marginBottom: '20px', color: '#2c3e50' },
  filterBar: { display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' },
  input: { padding: '8px 10px', border: '1px solid #ddd', borderRadius: '6px', outline: 'none' },
  button: { padding: '8px 16px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' },
  queryBtn: { background: '#1677ff', color: 'white' },
  resetBtn: { background: '#eee', color: '#333' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#fafafa', textAlign: 'left', padding: '12px 10px', borderBottom: '2px solid #eee', color: '#555' },
  td: { padding: '10px', borderBottom: '1px solid #eee', verticalAlign: 'middle' }
};