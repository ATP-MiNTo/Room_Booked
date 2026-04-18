import { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import {
  RiSearchLine, RiRefreshLine, RiImageAddLine, RiCloseLine,
  RiArrowLeftSLine, RiArrowRightSLine, RiFileExcel2Line,
  RiArrowUpSFill, RiArrowDownSFill, RiFilter3Fill, RiArrowDownSLine,
  RiHistoryFill
} from 'react-icons/ri';
import { formatThaiDate, generateTimeOptions, escapeCSV, downloadCSV, fmtDate } from '../../utils/dateUtils';
import { MAJOR_OPTIONS, YEAR_OPTIONS, pageStyles, tableStyles, btnStyles } from '../../utils/uiConstants';

// 🟢 1. กำหนด URL ของ Backend (FastAPI)
const BACKEND_URL = '';

export default function BookingHistory() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({ studentId: '', bookingDate: '', startTime: '', endTime: '', branch: '', yearLevel: '' });
  const [selectedImage, setSelectedImage] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: null });
  const [isFilterOpen, setIsFilterOpen] = useState(true);

  const itemsPerPage = 10;
  const timeOptions = generateTimeOptions();

  useEffect(() => { fetchLogs(); }, []);

  const fetchLogs = async () => {
    try {
      const res = await fetch('/reservations');
      if (res.ok) setLogs(await res.json());
    } catch (e) {
      console.error('fetchLogs error:', e);
    }
  };

  // 🟢 2. ฟังก์ชันสร้าง URL รูปภาพที่ถูกต้อง (ชี้ไปที่ Backend)
  const getImageUrl = (date, filename) => {
    if (!filename) return null;
    // ป้องกันกรณี filename มี / นำหน้า
    const cleanFilename = filename.startsWith('/') ? filename.substring(1) : filename;
    // คืนค่าเป็นพาทเต็ม เช่น http://localhost:8000/data/face_scanner/2026-04-18/filename.jpg
    return `${BACKEND_URL}/data/face_scanner/${date}/${cleanFilename}`;
  };

  const handleFilterChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
    setCurrentPage(1);
  };

  const resetFilter = () => {
    setFilters({ studentId: '', bookingDate: '', startTime: '', endTime: '', branch: '', yearLevel: '' });
    setCurrentPage(1);
  };

  const handleSort = (key) => {
    if (sortConfig.key === key) {
      if (sortConfig.direction === 'asc') setSortConfig({ key, direction: 'desc' });
      else if (sortConfig.direction === 'desc') setSortConfig({ key: null, direction: null });
    } else {
      setSortConfig({ key, direction: 'asc' });
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchStudent  = !filters.studentId  || log.student_id?.toLowerCase().includes(filters.studentId.toLowerCase()) || log.first_name?.toLowerCase().includes(filters.studentId.toLowerCase()) || log.last_name?.toLowerCase().includes(filters.studentId.toLowerCase());
    const matchDate     = !filters.bookingDate || log.reserve_date === filters.bookingDate;
    const matchStart    = !filters.startTime   || log.start_time >= filters.startTime;
    const matchEnd      = !filters.endTime     || log.end_time <= filters.endTime;
    const matchBranch   = !filters.branch      || log.major === filters.branch;
    const matchYear     = !filters.yearLevel   || log.year_level === filters.yearLevel;
    return matchStudent && matchDate && matchStart && matchEnd && matchBranch && matchYear;
  });

  const sortedLogs = [...filteredLogs].sort((a, b) => {
    if (!sortConfig.key || !sortConfig.direction) return 0;
    let aVal = a[sortConfig.key];
    let bVal = b[sortConfig.key];
    if (sortConfig.key === 'seat_id') {
      aVal = parseInt(aVal, 10); bVal = parseInt(bVal, 10);
    } else if (sortConfig.key === 'reserve_date') {
      aVal = new Date(`${a.reserve_date}T${a.start_time}`).getTime();
      bVal = new Date(`${b.reserve_date}T${b.start_time}`).getTime();
    } else if (sortConfig.key === 'status') {
      const now = Date.now();
      aVal = new Date(`${a.reserve_date}T${a.end_time}`).getTime() < now ? 0 : 1;
      bVal = new Date(`${b.reserve_date}T${b.end_time}`).getTime() < now ? 0 : 1;
    } else {
      aVal = aVal ? aVal.toString().toLowerCase() : '';
      bVal = bVal ? bVal.toString().toLowerCase() : '';
    }
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.ceil(sortedLogs.length / itemsPerPage);
  const currentItems = sortedLogs.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const getStatusBadge = (logDate, logEndTime) => {
    if (!logDate || !logEndTime) return <span style={pageStyles.badge}>ไม่ทราบสถานะ</span>;
    const expired = new Date(`${logDate}T${logEndTime}`) < new Date();
    return expired
      ? <span style={{ ...pageStyles.badge, background: '#f5f5f5', color: '#888' }}>หมดเวลา</span>
      : <span style={{ ...pageStyles.badge, background: '#e6f4ff', color: '#1677ff' }}>รอ/กำลังใช้งาน</span>;
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey || !sortConfig.direction)
      return <span style={{ opacity: 0.2, marginLeft: '4px', fontSize: '0.8rem' }}>↕</span>;
    return sortConfig.direction === 'asc'
      ? <RiArrowUpSFill style={{ marginLeft: '4px', color: '#1677ff' }} />
      : <RiArrowDownSFill style={{ marginLeft: '4px', color: '#1677ff' }} />;
  };

  const exportToCSV = () => {
    const headers = ['สถานะ', 'รหัสนักศึกษา', 'ชื่อ-นามสกุล', 'สาขา', 'ชั้นปี', 'ที่นั่ง', 'วันที่จอง', 'เวลาเริ่ม', 'เวลาจบ', 'วัตถุประสงค์'];
    const rows = [
      headers.map(escapeCSV).join(','),
      ...sortedLogs.map(log => {
        const status = new Date(`${log.reserve_date}T${log.end_time}`) < new Date() ? 'หมดเวลา' : 'กำลังใช้งาน';
        return [status, log.student_id, `${log.first_name} ${log.last_name}`, log.major, log.year_level, log.seat_id, log.reserve_date, log.start_time, log.end_time, log.purpose].map(escapeCSV).join(',');
      }),
    ];
    downloadCSV(rows, `booking_logs_${fmtDate(new Date())}.csv`);
  };

  return (
    <AdminLayout>
      <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>

        {/* Header */}
        <div style={pageStyles.header}>
          <h2 style={pageStyles.title}>
            <RiHistoryFill color="#1677ff" /> Booking History
          </h2>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button onClick={exportToCSV} style={btnStyles.export}>
              <RiFileExcel2Line /> Export CSV
            </button>
            <button onClick={fetchLogs} style={btnStyles.refresh}>
              <RiRefreshLine /> Refresh
            </button>
          </div>
        </div>

        {/* Filter accordion */}
        <div style={{ marginBottom: '25px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', borderRadius: '12px' }}>
          <div
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '15px 20px',
              background: isFilterOpen ? '#fafafa' : 'white',
              borderRadius: isFilterOpen ? '12px 12px 0 0' : '12px',
              borderLeft: '4px solid #1677ff',
              cursor: 'pointer', userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <RiFilter3Fill size={20} color="#1677ff" />
              <div>
                <div style={{ fontWeight: '700', color: '#2c3e50', fontSize: '1rem' }}>ค้นหาและตัวกรอง</div>
                <div style={{ fontSize: '0.82rem', color: '#aaa', marginTop: '2px' }}>ค้นหาตามรหัส, วันที่, เวลา, สาขา หรือชั้นปี</div>
              </div>
            </div>
            <span style={{ color: '#bbb', display: 'inline-block', transform: isFilterOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.25s' }}>
              <RiArrowDownSLine size={22} />
            </span>
          </div>

          <div style={{ maxHeight: isFilterOpen ? '400px' : '0', overflow: 'hidden', transition: 'max-height 0.35s ease', background: 'white', borderRadius: '0 0 12px 12px' }}>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 250px', position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <RiSearchLine color="#888" style={{ position: 'absolute', left: '12px' }} size={18} />
                  <input
                    type="text" name="studentId"
                    placeholder="ค้นหารหัส หรือ ชื่อนักศึกษา..."
                    value={filters.studentId} onChange={handleFilterChange}
                    style={s.searchInput}
                  />
                </div>
                <select name="branch" value={filters.branch} onChange={handleFilterChange} style={{ ...s.input, flex: '1 1 200px', cursor: 'pointer' }}>
                  {MAJOR_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <select name="yearLevel" value={filters.yearLevel} onChange={handleFilterChange} style={{ ...s.input, minWidth: '130px', cursor: 'pointer' }}>
                  {YEAR_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={s.label}>วันที่:</span>
                  <input type="date" name="bookingDate" value={filters.bookingDate} onChange={handleFilterChange} style={s.input} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={s.label}>ตั้งแต่:</span>
                  <select name="startTime" value={filters.startTime} onChange={handleFilterChange} style={{ ...s.input, cursor: 'pointer' }}>
                    <option value="">ทั้งหมด</option>
                    {timeOptions.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={s.label}>ถึง:</span>
                  <select name="endTime" value={filters.endTime} onChange={handleFilterChange} style={{ ...s.input, cursor: 'pointer' }}>
                    <option value="">ทั้งหมด</option>
                    {timeOptions.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div style={{ flex: 1 }} />
                <button onClick={resetFilter} style={s.resetBtn}><RiRefreshLine /> ล้างตัวกรอง</button>
              </div>
            </div>
          </div>
        </div>

        {/* Table */}
        <div style={tableStyles.wrap}>
          <table style={tableStyles.table}>
            <thead>
              <tr>
                {[
                  { label: 'สถานะ',        key: 'status' },
                  { label: 'ผู้จอง',       key: 'student_id' },
                  { label: 'ชั้นปี',       key: 'year_level', center: true },
                  { label: 'ที่นั่ง',      key: 'seat_id',    center: true },
                  { label: 'วันที่และเวลา', key: 'reserve_date' },
                  { label: 'วัตถุประสงค์', key: 'purpose' },
                ].map(col => (
                  <th key={col.key} style={{ ...tableStyles.th, cursor: 'pointer', textAlign: col.center ? 'center' : 'left' }} onClick={() => handleSort(col.key)}>
                    <div style={{ ...tableStyles.thContent, justifyContent: col.center ? 'center' : 'flex-start' }}>
                      {col.label} <SortIcon columnKey={col.key} />
                    </div>
                  </th>
                ))}
                <th style={{ ...tableStyles.th, textAlign: 'center' }}>รูปยืนยัน</th>
              </tr>
            </thead>
            <tbody>
              {currentItems.map((log, i) => (
                <tr key={i}>
                  <td style={tableStyles.td}>{getStatusBadge(log.reserve_date, log.end_time)}</td>
                  <td style={tableStyles.td}>
                    <div style={{ fontWeight: '700', color: '#2c3e50' }}>{log.student_id}</div>
                    <div style={{ fontSize: '0.85rem', color: '#555' }}>{log.first_name} {log.last_name}</div>
                    <div style={{ fontSize: '0.75rem', color: '#aaa' }}>{log.major}</div>
                  </td>
                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                    <span style={{ fontWeight: 'bold', color: '#8b5cf6', background: '#f3e8ff', padding: '4px 10px', borderRadius: '20px', fontSize: '0.85rem' }}>{log.year_level}</span>
                  </td>
                  <td style={{ ...tableStyles.td, fontWeight: '700', color: '#1677ff', textAlign: 'center', fontSize: '1.1rem' }}>{log.seat_id}</td>
                  <td style={tableStyles.td}>
                    <div style={{ fontWeight: 'bold', color: '#444' }}>{formatThaiDate(log.reserve_date)}</div>
                    <div style={{ fontSize: '0.85rem', color: '#888' }}>{log.start_time?.substring(0,5)} - {log.end_time?.substring(0,5)} น.</div>
                  </td>
                  <td style={tableStyles.td}>
                    <div style={{ maxWidth: '150px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: '#555' }} title={log.purpose}>{log.purpose}</div>
                  </td>
                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                    {log.image_filename ? (
                      <div
                        style={pageStyles.imageThumbnail}
                        // 🟢 3. เรียกใช้ getImageUrl เพื่อดึงรูปจาก Backend
                        onClick={() => setSelectedImage(getImageUrl(log.reserve_date, log.image_filename))}
                        onMouseEnter={(e) => e.currentTarget.lastChild.style.opacity = 1}
                        onMouseLeave={(e) => e.currentTarget.lastChild.style.opacity = 0}
                      >
                        {/* 🟢 4. แสดงรูปภาพตัวอย่าง */}
                        <img 
                          src={getImageUrl(log.reserve_date, log.image_filename)} 
                          alt="Face Scan" 
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                          onError={(e) => { e.target.style.display = 'none'; }} 
                        />
                        <div style={pageStyles.imageOverlay}><RiImageAddLine size={18} color="white" /></div>
                      </div>
                    ) : (
                      <span style={{ color: '#ccc', fontSize: '0.85rem' }}>ไม่มีรูป</span>
                    )}
                  </td>
                </tr>
              ))}
              {sortedLogs.length === 0 && (
                <tr><td colSpan="7" style={{ ...tableStyles.td, textAlign: 'center', color: '#ccc', padding: '40px' }}>ไม่พบข้อมูลการจองในระบบ</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={pageStyles.pagination}>
            <button style={{ ...pageStyles.pageBtn, opacity: currentPage === 1 ? 0.5 : 1 }} onClick={() => setCurrentPage(p => Math.max(p - 1, 1))} disabled={currentPage === 1}>
              <RiArrowLeftSLine size={18} /> ก่อนหน้า
            </button>
            <span style={{ fontSize: '0.9rem', color: '#555', fontWeight: 'bold' }}>
              หน้า {currentPage} จาก {totalPages} <span style={{ color: '#aaa', fontWeight: 'normal' }}>({sortedLogs.length} รายการ)</span>
            </span>
            <button style={{ ...pageStyles.pageBtn, opacity: currentPage === totalPages ? 0.5 : 1 }} onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))} disabled={currentPage === totalPages}>
              ถัดไป <RiArrowRightSLine size={18} />
            </button>
          </div>
        )}
      </div>

      {/* Image modal */}
      {selectedImage && (
        <div style={pageStyles.modalBackdrop} onClick={() => setSelectedImage(null)}>
          <div style={{ ...pageStyles.modalContent, padding: '5px', background: 'transparent', boxShadow: 'none' }} onClick={e => e.stopPropagation()}>
            <button style={{ ...pageStyles.closeModalBtn, top: '-15px', right: '-15px', background: 'white', borderRadius: '50%', padding: '5px' }} onClick={() => setSelectedImage(null)}>
              <RiCloseLine size={24} />
            </button>
            <img src={selectedImage} alt="Face Scan" style={pageStyles.enlargedImage} />
          </div>
        </div>
      )}
    </AdminLayout>
  );
}

const s = {
  searchInput: { padding: '10px 12px 10px 40px', border: '1px solid #ddd', borderRadius: '8px', fontSize: '0.95rem', outline: 'none', width: '100%', boxSizing: 'border-box' },
  input: { padding: '9px 11px', border: '1px solid #ddd', borderRadius: '8px', fontSize: '0.93rem', outline: 'none', boxSizing: 'border-box' },
  label: { fontSize: '0.9rem', fontWeight: '700', color: '#4a5568', whiteSpace: 'nowrap' },
  resetBtn: { display: 'flex', alignItems: 'center', gap: '5px', padding: '9px 15px', background: '#f5f5f5', border: '1px solid #ddd', color: '#555', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', fontSize: '0.9rem', whiteSpace: 'nowrap' },
};