import { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import Swal from 'sweetalert2';
import {
  RiSearchLine, RiRefreshLine, RiFileExcel2Line,
  RiGroupFill, RiEdit2Line, RiDeleteBinLine, RiSave3Line, RiCloseLine,
  RiArrowUpSFill, RiArrowDownSFill, RiArrowLeftSLine, RiArrowRightSLine,
  RiFilter3Fill, RiArrowDownSLine, RiHistoryFill, RiImageAddLine,
  RiPieChartLine, RiUserStarLine
} from 'react-icons/ri';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { formatThaiDate, escapeCSV, downloadCSV, fmtDate } from '../../utils/dateUtils';
import { MAJOR_OPTIONS, YEAR_OPTIONS, COLORS_YEAR, pageStyles, tableStyles, btnStyles } from '../../utils/uiConstants';

export default function StudentInfo() {
  const [students, setStudents] = useState([]);
  const [currentAcademicYear, setCurrentAcademicYear] = useState(null);
  const [filters, setFilters] = useState({ keyword: '', branch: '', yearLevel: '' });
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState({ key: 'student_id', direction: 'asc' });
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentHistory, setStudentHistory] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);

  const itemsPerPage = 10;

  useEffect(() => { fetchStudentsAndYear(); }, []);

  const fetchStudentsAndYear = async () => {
    try {
      const [resStudents, resYear] = await Promise.all([
        fetch('/api/students').then(r => r.ok ? r : fetch('/students')),
        fetch('/api/current-academic-year'),
      ]);
      if (resStudents.ok) setStudents(await resStudents.json());
      if (resYear.ok) {
        const data = await resYear.json();
        setCurrentAcademicYear(data.current_academic_year);
      }
    } catch (e) {
      console.error('fetchStudentsAndYear error:', e);
    }
  };

  const getYearStatsData = () => {
    const counts = { 'ปี 1': 0, 'ปี 2': 0, 'ปี 3': 0, 'ปี 4': 0, 'ปี 5++': 0 };
    students.forEach(s => { if (counts[s.year_level] !== undefined) counts[s.year_level]++; });
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: k, value: v }))
      .sort((a, b) => a.name.localeCompare(b.name));
  };

  const yearStatsData = getYearStatsData();

  const handleSort = (key) => {
    if (sortConfig.key === key) {
      if (sortConfig.direction === 'asc') setSortConfig({ key, direction: 'desc' });
      else if (sortConfig.direction === 'desc') setSortConfig({ key: null, direction: null });
    } else {
      setSortConfig({ key, direction: 'asc' });
    }
  };

  const handleFilterChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
    setCurrentPage(1);
  };

  const resetFilter = () => {
    setFilters({ keyword: '', branch: '', yearLevel: '' });
    setCurrentPage(1);
  };

  const startEditing = (std) => {
    setEditingId(std.student_id);
    setEditData({ first_name: std.first_name, last_name: std.last_name, major: std.major });
  };

  const cancelEditing = () => { setEditingId(null); setEditData({}); };

  const saveEdit = async (studentId) => {
    try {
      const res = await fetch(`/api/students/${studentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData),
      });
      if (res.ok) {
        Swal.fire({ icon: 'success', title: 'อัปเดตข้อมูลสำเร็จ', showConfirmButton: false, timer: 1500 });
        setEditingId(null);
        fetchStudentsAndYear();
      } else {
        Swal.fire('ข้อผิดพลาด', 'ไม่สามารถอัปเดตข้อมูลได้', 'error');
      }
    } catch {
      Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
    }
  };

  const handleDelete = async (studentId, studentName) => {
    const confirm = await Swal.fire({
      title: 'ยืนยันการลบ?',
      html: `คุณต้องการลบข้อมูลของ <b>${studentName}</b> ใช่หรือไม่?<br/><br/><small style="color:red;">การลบจะทำให้ประวัติการจองหายไปด้วย</small>`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonText: 'ยกเลิก',
      confirmButtonText: 'ใช่, ลบเลย!',
    });
    if (!confirm.isConfirmed) return;
    try {
      const res = await fetch(`/api/students/${studentId}`, { method: 'DELETE' });
      if (res.ok) {
        Swal.fire({ icon: 'success', title: 'ลบข้อมูลสำเร็จ', showConfirmButton: false, timer: 1500 });
        fetchStudentsAndYear();
      } else {
        Swal.fire('ข้อผิดพลาด', 'ไม่สามารถลบข้อมูลได้', 'error');
      }
    } catch {
      Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
    }
  };

  const exportToCSV = () => {
    const headers = ['รหัสนักศึกษา', 'ชื่อ', 'นามสกุล', 'สาขา', 'ชั้นปี'];
    const rows = [
      headers.map(escapeCSV).join(','),
      ...sortedStudents.map(s => [s.student_id, s.first_name, s.last_name, s.major, s.year_level].map(escapeCSV).join(',')),
    ];
    downloadCSV(rows, `student_info_${fmtDate(new Date())}.csv`);
  };

  const openHistoryModal = async (student) => {
    setSelectedStudent(student);
    setHistoryModalOpen(true);
    setIsHistoryLoading(true);
    try {
      const res = await fetch(`/api/students/${student.student_id}/reservations`);
      setStudentHistory(res.ok ? await res.json() : []);
    } catch {
      setStudentHistory([]);
    }
    setIsHistoryLoading(false);
  };

  const getStatusBadge = (logDate, logEndTime) => {
    if (!logDate || !logEndTime) return <span style={pageStyles.badge}>-</span>;
    const expired = new Date(`${logDate}T${logEndTime}`) < new Date();
    return expired
      ? <span style={{ ...pageStyles.badge, background: '#f5f5f5', color: '#888' }}>หมดเวลา</span>
      : <span style={{ ...pageStyles.badge, background: '#e6f4ff', color: '#1677ff' }}>รอ/กำลังใช้งาน</span>;
  };

  const calculateTotalHours = (history) => {
    let totalMins = 0;
    history.forEach(log => {
      if (log.start_time && log.end_time) {
        const [sh, sm] = log.start_time.split(':').map(Number);
        const [eh, em] = log.end_time.split(':').map(Number);
        const diff = (eh * 60 + em) - (sh * 60 + sm);
        if (diff > 0) totalMins += diff;
      }
    });
    const hrs  = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    if (!hrs && !mins) return '0 ชั่วโมง';
    return `${hrs ? hrs + ' ชม. ' : ''}${mins ? mins + ' นาที' : ''}`;
  };

  const filteredStudents = students.filter(s => {
    const kw = filters.keyword.toLowerCase();
    const matchKeyword = !filters.keyword || s.student_id.includes(filters.keyword) || s.first_name.toLowerCase().includes(kw) || s.last_name.toLowerCase().includes(kw);
    const matchBranch  = !filters.branch    || s.major      === filters.branch;
    const matchYear    = !filters.yearLevel || s.year_level === filters.yearLevel;
    return matchKeyword && matchBranch && matchYear;
  });

  const sortedStudents = [...filteredStudents].sort((a, b) => {
    if (!sortConfig.key || !sortConfig.direction) return 0;
    const aVal = a[sortConfig.key]?.toString().toLowerCase() || '';
    const bVal = b[sortConfig.key]?.toString().toLowerCase() || '';
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.ceil(sortedStudents.length / itemsPerPage);
  const currentItems = sortedStudents.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey || !sortConfig.direction)
      return <span style={{ opacity: 0.2, marginLeft: '4px', fontSize: '0.8rem' }}>↕</span>;
    return sortConfig.direction === 'asc'
      ? <RiArrowUpSFill style={{ marginLeft: '4px', color: '#1677ff' }} />
      : <RiArrowDownSFill style={{ marginLeft: '4px', color: '#1677ff' }} />;
  };

  return (
    <AdminLayout>
      <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>

        {/* Header */}
        <div style={pageStyles.header}>
          <h2 style={pageStyles.title}>
            <RiGroupFill color="#1677ff" /> Student Info
          </h2>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button onClick={exportToCSV} style={btnStyles.export}>
              <RiFileExcel2Line /> Export CSV
            </button>
            <button onClick={fetchStudentsAndYear} style={btnStyles.refresh}>
              <RiRefreshLine /> Refresh
            </button>
          </div>
        </div>

        {/* Stats cards */}
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '25px' }}>
          <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', padding: '20px', borderRadius: '12px', flex: '1 1 200px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
            <div>
              <div style={{ fontSize: '0.9rem', color: '#389e0d', fontWeight: 'bold' }}>จำนวนนักศึกษาในระบบ</div>
              <div style={{ fontSize: '2.2rem', fontWeight: '900', color: '#135200', marginTop: '5px' }}>{students.length} <span style={{ fontSize: '1rem', fontWeight: 'normal' }}>คน</span></div>
            </div>
            <div style={{ background: '#d9f7be', padding: '15px', borderRadius: '50%', color: '#52c41a' }}>
              <RiUserStarLine size={32} />
            </div>
          </div>

          <div style={{ background: 'white', border: '1px solid #e2e8f0', padding: '20px', borderRadius: '12px', flex: '2 1 400px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: '0 0 5px 0', color: '#1e293b', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RiPieChartLine color="#8b5cf6" /> สัดส่วนแบ่งตามชั้นปี
              </h3>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '10px' }}>
                ปีการศึกษาปัจจุบัน: <b style={{ color: '#8b5cf6' }}>{currentAcademicYear || 'กำลังโหลด...'}</b>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {yearStatsData.map((d, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#f8fafc', padding: '6px 12px', borderRadius: '20px', border: '1px solid #f1f5f9' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: COLORS_YEAR[i % COLORS_YEAR.length] }} />
                    <span style={{ fontSize: '0.85rem', color: '#475569' }}>{d.name}</span>
                    <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>{d.value}</strong>
                  </div>
                ))}
                {yearStatsData.length === 0 && <span style={{ fontSize: '0.85rem', color: '#aaa' }}>ไม่มีข้อมูลชั้นปี</span>}
              </div>
            </div>
            {yearStatsData.length > 0 && (
              <div style={{ width: '140px', height: '120px', flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={yearStatsData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={2}>
                      {yearStatsData.map((_, i) => <Cell key={i} fill={COLORS_YEAR[i % COLORS_YEAR.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v, n) => [`${v} คน`, n]} contentStyle={{ borderRadius: '8px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
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
                <div style={{ fontSize: '0.82rem', color: '#aaa', marginTop: '2px' }}>ค้นหาด้วยข้อความ หรือคัดกรองตามสาขา/ชั้นปี</div>
              </div>
            </div>
            <span style={{ color: '#bbb', display: 'inline-block', transform: isFilterOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.25s' }}>
              <RiArrowDownSLine size={22} />
            </span>
          </div>
          <div style={{ maxHeight: isFilterOpen ? '200px' : '0', overflow: 'hidden', transition: 'max-height 0.35s ease', background: 'white', borderRadius: '0 0 12px 12px' }}>
            <div style={{ padding: '16px 20px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ flex: '1 1 250px', position: 'relative', display: 'flex', alignItems: 'center' }}>
                <RiSearchLine color="#888" style={{ position: 'absolute', left: '12px' }} size={18} />
                <input
                  type="text" name="keyword"
                  placeholder="ค้นหารหัส หรือ ชื่อนักศึกษา..."
                  value={filters.keyword} onChange={handleFilterChange}
                  style={s.searchInput}
                />
              </div>
              <select name="branch" value={filters.branch} onChange={handleFilterChange} style={{ ...s.input, flex: '1 1 200px', cursor: 'pointer' }}>
                {MAJOR_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <select name="yearLevel" value={filters.yearLevel} onChange={handleFilterChange} style={{ ...s.input, minWidth: '130px', cursor: 'pointer' }}>
                {YEAR_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <button onClick={resetFilter} style={s.resetBtn}><RiRefreshLine /> ล้างตัวกรอง</button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div style={tableStyles.wrap}>
          <table style={tableStyles.table}>
            <thead>
              <tr>
                {[
                  { label: 'รหัสนักศึกษา', key: 'student_id', w: '15%' },
                  { label: 'ชื่อ',          key: 'first_name', w: '20%' },
                  { label: 'นามสกุล',       key: 'last_name',  w: '20%' },
                  { label: 'สาขา',          key: 'major',      w: '25%' },
                  { label: 'ชั้นปี',        key: 'year_level', w: '10%', center: true },
                ].map(col => (
                  <th key={col.key} style={{ ...tableStyles.th, cursor: 'pointer', width: col.w }} onClick={() => handleSort(col.key)}>
                    <div style={{ ...tableStyles.thContent, justifyContent: col.center ? 'center' : 'flex-start' }}>
                      {col.label} <SortIcon columnKey={col.key} />
                    </div>
                  </th>
                ))}
                <th style={{ ...tableStyles.th, textAlign: 'center', width: '10%' }}>จัดการ</th>
              </tr>
            </thead>
            <tbody>
              {currentItems.map(std => (
                <tr key={std.student_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td
                    style={{ ...tableStyles.td, fontWeight: '700', color: '#1677ff', cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={() => openHistoryModal(std)}
                    onMouseEnter={(e) => e.target.style.color = '#0958d9'}
                    onMouseLeave={(e) => e.target.style.color = '#1677ff'}
                    title={`ดูประวัติการจองของ ${std.first_name}`}
                  >
                    {std.student_id}
                  </td>

                  {editingId === std.student_id ? (
                    <>
                      <td style={tableStyles.td}><input type="text" value={editData.first_name} onChange={e => setEditData({ ...editData, first_name: e.target.value })} style={s.editInput} /></td>
                      <td style={tableStyles.td}><input type="text" value={editData.last_name}  onChange={e => setEditData({ ...editData, last_name: e.target.value })}  style={s.editInput} /></td>
                      <td style={tableStyles.td}><input type="text" value={editData.major}      onChange={e => setEditData({ ...editData, major: e.target.value })}      style={s.editInput} /></td>
                      <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                        <span style={{ fontWeight: 'bold', color: '#8b5cf6', background: '#f3e8ff', padding: '4px 10px', borderRadius: '20px', fontSize: '0.85rem' }}>{std.year_level}</span>
                      </td>
                      <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                        <button onClick={() => saveEdit(std.student_id)} style={s.iconBtnSuccess} title="บันทึก"><RiSave3Line size={18} /></button>
                        <button onClick={cancelEditing}                   style={s.iconBtnDanger}  title="ยกเลิก"><RiCloseLine size={18} /></button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={{ ...tableStyles.td, fontWeight: '700', color: '#2c3e50' }}>{std.first_name}</td>
                      <td style={tableStyles.td}>{std.last_name}</td>
                      <td style={tableStyles.td}>{std.major}</td>
                      <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                        <span style={{ fontWeight: 'bold', color: '#8b5cf6', background: '#f3e8ff', padding: '4px 10px', borderRadius: '20px', fontSize: '0.85rem' }}>{std.year_level}</span>
                      </td>
                      <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                        <button onClick={() => startEditing(std)} style={s.iconBtnInfo}    title="แก้ไข"><RiEdit2Line size={18} /></button>
                        <button onClick={() => handleDelete(std.student_id, `${std.first_name} ${std.last_name}`)} style={s.iconBtnDanger} title="ลบ"><RiDeleteBinLine size={18} /></button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {sortedStudents.length === 0 && (
                <tr><td colSpan="6" style={{ ...tableStyles.td, textAlign: 'center', color: '#ccc', padding: '40px' }}>ไม่พบข้อมูลนักศึกษาในระบบ</td></tr>
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
              หน้า {currentPage} จาก {totalPages} <span style={{ color: '#aaa', fontWeight: 'normal' }}>({sortedStudents.length} คน)</span>
            </span>
            <button style={{ ...pageStyles.pageBtn, opacity: currentPage === totalPages ? 0.5 : 1 }} onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))} disabled={currentPage === totalPages}>
              ถัดไป <RiArrowRightSLine size={18} />
            </button>
          </div>
        )}
      </div>

      {/* History modal */}
      {historyModalOpen && selectedStudent && (
        <div style={pageStyles.modalBackdrop} onClick={() => setHistoryModalOpen(false)}>
          <div style={{ ...pageStyles.modalContent, width: '900px', padding: '25px' }} onClick={e => e.stopPropagation()}>
            <button style={pageStyles.closeModalBtn} onClick={() => setHistoryModalOpen(false)}><RiCloseLine size={24} /></button>
            <h3 style={{ margin: '0 0 15px 0', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <RiHistoryFill color="#1677ff" /> Booking History: {selectedStudent.first_name} {selectedStudent.last_name}
            </h3>

            <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
              {[
                { label: 'รหัสนักศึกษา', value: selectedStudent.student_id, border: '#1677ff', bg: '#f5f5f5', color: '#2c3e50' },
                { label: 'สาขา',         value: selectedStudent.major,      border: '#52c41a', bg: '#f5f5f5', color: '#2c3e50' },
                { label: 'จำนวนการใช้งาน', value: `${studentHistory.length} ครั้ง`, border: '#faad14', bg: '#fffbe6', color: '#d48806' },
                { label: 'เวลารวมทั้งหมด', value: calculateTotalHours(studentHistory), border: '#722ed1', bg: '#f9f0ff', color: '#531dab' },
              ].map((info, i) => (
                <div key={i} style={{ flex: 1, background: info.bg, padding: '12px 15px', borderRadius: '8px', borderLeft: `4px solid ${info.border}` }}>
                  <div style={{ fontSize: '0.8rem', color: '#888' }}>{info.label}</div>
                  <div style={{ fontWeight: 'bold', color: info.color, fontSize: '1.1rem' }}>{info.value}</div>
                </div>
              ))}
            </div>

            {isHistoryLoading ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>กำลังโหลดข้อมูล...</div>
            ) : (
              <div style={{ maxHeight: '50vh', overflowY: 'auto', border: '1px solid #eee', borderRadius: '8px' }}>
                <table style={tableStyles.table}>
                  <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
                    <tr>
                      {['สถานะ', 'ที่นั่ง', 'วันที่จอง', 'เวลา', 'วัตถุประสงค์', 'รูปถ่ายยืนยัน'].map(h => (
                        <th key={h} style={{ ...tableStyles.th, textAlign: h === 'ที่นั่ง' || h === 'รูปถ่ายยืนยัน' ? 'center' : 'left' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {studentHistory.length > 0 ? studentHistory.map((history, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={tableStyles.td}>{getStatusBadge(history.reserve_date, history.end_time)}</td>
                        <td style={{ ...tableStyles.td, textAlign: 'center', fontWeight: 'bold', color: '#1677ff' }}>{history.seat_id}</td>
                        <td style={{ ...tableStyles.td, fontWeight: 'bold', color: '#444' }}>{formatThaiDate(history.reserve_date)}</td>
                        <td style={tableStyles.td}>{history.start_time?.substring(0,5)} - {history.end_time?.substring(0,5)} น.</td>
                        <td style={tableStyles.td}>{history.purpose}</td>
                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                          {history.image_filename ? (
                            <div
                              style={pageStyles.imageThumbnail}
                              onClick={() => setSelectedImage(`/data/face_scanner/${history.reserve_date}/${history.image_filename}`)}
                              onMouseEnter={(e) => e.currentTarget.lastChild.style.opacity = 1}
                              onMouseLeave={(e) => e.currentTarget.lastChild.style.opacity = 0}
                            >
                              <img src={`/data/face_scanner/${history.reserve_date}/${history.image_filename}`} alt="Face Scan" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.src = 'https://via.placeholder.com/50?text=No+Img'; }} />
                              <div style={pageStyles.imageOverlay}><RiImageAddLine size={18} color="white" /></div>
                            </div>
                          ) : (
                            <span style={{ color: '#ccc', fontSize: '0.85rem' }}>ไม่มีรูป</span>
                          )}
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan="6" style={{ ...tableStyles.td, textAlign: 'center', padding: '30px', color: '#ccc' }}>ไม่พบประวัติการใช้งาน</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Image zoom modal */}
      {selectedImage && (
        <div style={{ ...pageStyles.modalBackdrop, zIndex: 10000 }} onClick={() => setSelectedImage(null)}>
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
  resetBtn: { display: 'flex', alignItems: 'center', gap: '5px', padding: '9px 15px', background: '#f5f5f5', border: '1px solid #ddd', color: '#555', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', fontSize: '0.9rem', whiteSpace: 'nowrap' },
  editInput: { padding: '6px 10px', border: '1px solid #1677ff', borderRadius: '6px', fontSize: '0.9rem', width: '100%', boxSizing: 'border-box' },
  iconBtnInfo:    { background: '#e6f4ff', color: '#1677ff', border: 'none', borderRadius: '6px', padding: '8px', margin: '0 3px', cursor: 'pointer', display: 'inline-flex' },
  iconBtnDanger:  { background: '#fff1f0', color: '#cf1322', border: 'none', borderRadius: '6px', padding: '8px', margin: '0 3px', cursor: 'pointer', display: 'inline-flex' },
  iconBtnSuccess: { background: '#f6ffed', color: '#389e0d', border: 'none', borderRadius: '6px', padding: '8px', margin: '0 3px', cursor: 'pointer', display: 'inline-flex' },
};
