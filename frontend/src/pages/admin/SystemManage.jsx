import React, { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import Swal from 'sweetalert2';
import { 
  RiLockFill, RiToolsFill, RiDeleteBinFill, RiCheckFill, RiCalendarEventFill, 
  RiShieldUserFill, RiUserAddLine, RiEdit2Fill, RiCloseLine, RiSave3Line, RiSettings4Line, RiRefreshLine
} from 'react-icons/ri';

import ThaiDatePicker from '../../components/admin/ThaiDatePicker';
import SeatGrid from '../../components/admin/SeatGrid';
import { AccordionTrigger, AccordionBody } from '../../components/admin/Accordion';

import { formatThaiDate, generateTimeOptions, DAY_NAMES_EN, THAI_DAYS_FULL } from '../../utils/dateUtils';
import { pageStyles, tableStyles, btnStyles } from '../../utils/uiConstants';
import { authFetch } from '../../utils/authFetch';

export default function SystemManage() {
  const currentAdminId = sessionStorage.getItem('adminId');
  const currentYear = new Date().getFullYear();
  const thaiYear = currentYear + 543;

  const dayOfWeekOptions = DAY_NAMES_EN.map((day, idx) => ({
    value: day,
    label: THAI_DAYS_FULL[idx]
  }));

  const timeOptions = generateTimeOptions();

  const purposeOptions = [
    { value: 'ตารางเรียน', lockAll: true },
    { value: 'สอบ',        lockAll: true },
    { value: 'อื่นๆ',      lockAll: false },
  ];

  const issueOptions = [
    'หน้าจอเสีย',
    'ตัวเครื่อง (PC) มีปัญหา',
    'เมาส์ / คีย์บอร์ดเสีย',
    'ระบบเครือข่าย / อินเทอร์เน็ต',
  ];

  const [openPanel, setOpenPanel] = useState(null);

  const [semestersList, setSemestersList] = useState([]);
  const [semData, setSemData] = useState({ academic_year: thaiYear, semester: '1', start_date: '', end_date: '' });
  
  const [blockData, setBlockData] = useState({
    purpose: 'ตารางเรียน', selected_semester_id: '', single_date: '', day_of_week: 'Monday',
    start_time: '', end_time: '', seat_nos: [], subject_name: '', section: '', teacher_name: '', note: ''
  });

  const [brokenData, setBrokenData] = useState({ seat_no: null });
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [otherIssue, setOtherIssue] = useState('');
  
  const [schedules, setSchedules] = useState([]);
  const [brokenList, setBrokenList] = useState([]);

  const [adminsList, setAdminsList] = useState([]);
  const [newAdmin, setNewAdmin] = useState({
    staff_id: '', first_name: '', last_name: '', department: '', position: '', username: '', password: '', priority: 3
  });

  const [editingAdmin, setEditingAdmin] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const [currentPriority, setCurrentPriority] = useState(3);

  const fetchData = async () => {
    try {
      const [r0, r1, r2, r3] = await Promise.all([
        authFetch('/api/system/semesters'),
        authFetch('/api/system/schedules'),
        authFetch('/api/system/broken-seats'),
        authFetch('/api/admins')
      ]);
      
      if (r0.ok) setSemestersList(await r0.json());
      if (r1.ok) setSchedules(await r1.json());
      if (r2.ok) setBrokenList(await r2.json());
      if (r3.ok) {
          const admins = await r3.json();
          setAdminsList(admins);
          const me = admins.find(a => a.staff_id === currentAdminId);
          if (me) setCurrentPriority(me.priority);
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchData(); }, []);

  const canManageSystem = currentPriority <= 2;
  const canManageAdmin = currentPriority === 1;

  const getDayLabel = (v) => dayOfWeekOptions.find(d => d.value === v)?.label ?? v;

  const handleSemesterSubmit = async (e) => {
    e.preventDefault();
    if (!canManageSystem) return;

    if (!semData.start_date || !semData.end_date) {
        return Swal.fire('แจ้งเตือน', 'กรุณาระบุวันที่ให้ครบถ้วน', 'warning');
    }
    const res = await authFetch('/api/system/semesters', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(semData) 
    });

    if (res.ok) {
        Swal.fire('สำเร็จ', 'บันทึกปีการศึกษาเรียบร้อย', 'success');
        setSemData({ academic_year: thaiYear, semester: '1', start_date: '', end_date: '' });
        fetchData();
    }
  };

  const handleSeatToggle = (num) => {
    if (!canManageSystem) return;
    if (blockData.purpose === 'ตารางเรียน' || blockData.purpose === 'สอบ') return;
    setBlockData(prev => ({
      ...prev,
      seat_nos: prev.seat_nos.includes(num) ? prev.seat_nos.filter(s => s !== num) : [...prev.seat_nos, num],
    }));
  };

  const handleBlockSubmit = async (e) => {
    e.preventDefault();
    if (!canManageSystem) return;
    if (!currentAdminId) return Swal.fire('ข้อผิดพลาด', 'กรุณาเข้าสู่ระบบ', 'error');

    const isAcademicPurpose = blockData.purpose === 'ตารางเรียน';
    let finalStartDate = '';
    let finalEndDate = '';
    let finalYear = null;
    let finalSem = null;
    let finalDayOfWeek = blockData.day_of_week;

    if (isAcademicPurpose) {
        const selectedSem = semestersList.find(s => s.id.toString() === blockData.selected_semester_id);
        if (!selectedSem) return Swal.fire('แจ้งเตือน', 'กรุณาเลือกปีการศึกษา/ภาคเรียน', 'warning');
        finalStartDate = selectedSem.start_date;
        finalEndDate = selectedSem.end_date;
        finalYear = selectedSem.academic_year;
        finalSem = selectedSem.semester;
    } else {
        if (!blockData.single_date) return Swal.fire('แจ้งเตือน', 'กรุณาระบุวันที่ต้องการจองให้ครบถ้วน', 'warning');
        finalStartDate = blockData.single_date;
        finalEndDate = blockData.single_date; 
        const d = new Date(blockData.single_date);
        
        finalDayOfWeek = DAY_NAMES_EN[d.getDay()];
    }

    const isLockAll = (blockData.purpose === 'ตารางเรียน' || blockData.purpose === 'สอบ');
    if (!isLockAll && blockData.seat_nos.length === 0) return Swal.fire('แจ้งเตือน', 'กรุณาเลือกที่นั่งอย่างน้อย 1 ที่', 'warning');

    const res = await authFetch('/api/system/lock-seats', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({
        ...blockData,
          academic_year: finalYear, semester: finalSem,
          start_date: finalStartDate, end_date: finalEndDate,
          day_of_week: finalDayOfWeek,
          start_time: `${blockData.start_time}:00`, end_time: `${blockData.end_time}:00`,
          is_all_seats: isLockAll, admin_id: currentAdminId
      }) 
    });

    if (res.ok) {
        Swal.fire('สำเร็จ', 'บันทึกข้อมูลเรียบร้อย', 'success');
        setBlockData({ ...blockData, single_date: '', start_time: '', end_time: '', seat_nos: [], subject_name: '', section: '', teacher_name: '', note: '' });
        setOpenPanel(null);
        fetchData();
    }
  };

  const handleDeleteSchedule = async (id) => {
    if (!canManageSystem) return;
    if ((await Swal.fire({ title: 'ยืนยันลบ?', icon: 'warning', showCancelButton: true, confirmButtonColor: '#d33' })).isConfirmed) {
        await authFetch(`/api/system/schedules/${id}`, { method: 'DELETE' });
        fetchData();
    }
  };

  const handleBrokenSubmit = async (e) => {
    e.preventDefault();
    if (!canManageSystem) return;
    if (!brokenData.seat_no) return Swal.fire('แจ้งเตือน', 'กรุณาเลือกที่นั่ง', 'warning');
    const note = [...selectedIssues, otherIssue].filter(i => i.trim()).join(', ');
    if (!note) return Swal.fire('แจ้งเตือน', 'กรุณาระบุอาการเสีย', 'warning');
    
    const res = await authFetch('/api/system/report-broken', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ seat_no: brokenData.seat_no, note, admin_id: currentAdminId}) 
    });

    if (res.ok) {
        Swal.fire('สำเร็จ', 'บันทึกแจ้งเครื่องเสียเรียบร้อย', 'success');
        setBrokenData({ seat_no: null }); setSelectedIssues([]); setOtherIssue('');
        setOpenPanel(null);
        fetchData();
    }
  };

  const handleResolveBroken = async (brokenId) => {
    if (!canManageSystem) return;
    const today = new Date().toISOString().split('T')[0];
    const { value: selectedDate } = await Swal.fire({
        title: 'ยืนยันการซ่อมเสร็จ',
        html: `<div style="text-align: left; padding: 5px;"><label style="font-weight: bold; color: #555;">ระบุวันที่ซ่อมเสร็จ (ค.ศ.):</label><input type="date" id="fixed-date" value="${today}" max="${today}" style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box;"></div>`,
        showCancelButton: true, confirmButtonColor: '#52c41a',
        preConfirm: () => document.getElementById('fixed-date').value || Swal.showValidationMessage('กรุณาเลือกวันที่')
    });
    if (selectedDate) {

        await authFetch('/api/system/resolve-broken', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ broken_id: brokenId, admin_id: currentAdminId, fixed_date: selectedDate }) 
        });

        fetchData();
    }
  };

  const handleAdminChange = (e) => setNewAdmin({ ...newAdmin, [e.target.name]: e.target.value });

  const handleAddAdmin = async (e) => {
    e.preventDefault();
    if (!canManageAdmin) return;
    if (!newAdmin.staff_id || !newAdmin.first_name || !newAdmin.username || !newAdmin.password) {
        return Swal.fire('ข้อมูลไม่ครบ', 'กรุณากรอกรหัสพนักงาน ชื่อ Username และรหัสผ่าน', 'warning');
    }
    try {

      const res = await authFetch('/api/admins', { 
        method: 'POST',
        body: JSON.stringify({...newAdmin, priority: parseInt(newAdmin.priority) })
      });

      const data = await res.json();
      if (res.ok) {
        Swal.fire({ icon: 'success', title: 'เพิ่มแอดมินสำเร็จ', showConfirmButton: false, timer: 1500 });
        setNewAdmin({ staff_id: '', first_name: '', last_name: '', department: '', position: '', username: '', password: '', priority: 3 });
        fetchData();
      } else {
        Swal.fire('ข้อผิดพลาด', data.detail || 'ไม่สามารถเพิ่มแอดมินได้', 'error');
      }
    } catch (e) {
      Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
    }
  };

  const handleDeleteAdmin = async (staffId, adminName) => {
    if (!canManageAdmin) return;
    if (adminsList.length <= 1) return Swal.fire('ไม่อนุญาต', 'ระบบต้องมีผู้ดูแลระบบอย่างน้อย 1 คน', 'error');
    const confirm = await Swal.fire({
      title: 'ยืนยันการลบบัญชี?',
      html: `ต้องการเพิกถอนสิทธิ์และลบบัญชีของ <b>${adminName}</b> ใช่หรือไม่?`,
      icon: 'warning', showCancelButton: true, confirmButtonColor: '#dc3545',
      confirmButtonText: 'ใช่, ลบบัญชีเลย!'
    });
    if (confirm.isConfirmed) {
      const res = await authFetch(`/api/admins/${staffId}`, { method: 'DELETE' });
      if (res.ok) {
        Swal.fire({ icon: 'success', title: 'ลบข้อมูลสำเร็จ', showConfirmButton: false, timer: 1500 });
        fetchData();
      }
    }
  };

  const openEditAdminModal = (admin) => {
    if (!canManageAdmin) return;
    setEditingAdmin({
        staff_id: admin.staff_id,
        first_name: admin.first_name,
        last_name: admin.last_name,
        department: admin.department === '-' ? '' : admin.department,
        position: admin.position === '-' ? '' : admin.position,
        username: admin.username,
        password: '',
        priority: admin.priority
    });
    setIsEditModalOpen(true);
  };

  const handleEditAdminChange = (e) => setEditingAdmin({ ...editingAdmin, [e.target.name]: e.target.value });

  const handleEditAdminSubmit = async (e) => {
      e.preventDefault();
      if (!canManageAdmin) return;
      if (!editingAdmin.first_name || !editingAdmin.username) {
          return Swal.fire('ข้อมูลไม่ครบ', 'กรุณากรอกชื่อ และ Username', 'warning');
      }
      try {

          const res = await authFetch(`/api/admins/${editingAdmin.staff_id}`, { 
            method: 'PUT', 
            body: JSON.stringify({...editingAdmin, priority: parseInt(editingAdmin.priority)})
          });
          const data = await res.json();
          if (res.ok) {
              Swal.fire({ icon: 'success', title: 'แก้ไขข้อมูลสำเร็จ', showConfirmButton: false, timer: 1500 });
              setIsEditModalOpen(false);
              fetchData();
          } else {
              Swal.fire('ข้อผิดพลาด', data.detail || 'ไม่สามารถแก้ไขข้อมูลได้', 'error');
          }
      } catch (e) {
          Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
      }
  };

  const getPriorityTag = (p) => {
    if (p === 1) return <span style={{...pageStyles.badge, background: '#fff1f0', color: '#cf1322', border: '1px solid #ffa39e'}}>Level 1</span>;
    if (p === 2) return <span style={{...pageStyles.badge, background: '#e6f7ff', color: '#096dd9', border: '1px solid #91d5ff'}}>Level 2</span>;
    return <span style={{...pageStyles.badge, background: '#f5f5f5', color: '#595959', border: '1px solid #d9d9d9'}}>Level 3</span>;
  };

  return (
    <AdminLayout>
      {/* 🟢 ขยายความกว้างให้ตรงกับหน้าอื่น */}
      <div style={{ padding: '10px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>
        
        {/* 🟢 Header มาตรฐาน */}
        <div style={pageStyles.header}>
          <h2 style={pageStyles.title}>
            <RiSettings4Line color="#1677ff" /> System Settings
          </h2>
          <button onClick={fetchData} style={btnStyles.refresh}>
            <RiRefreshLine /> Refresh
          </button>
        </div>

        <div style={{ marginBottom: '10px' }}>
          <AccordionTrigger id="semester" openPanel={openPanel} setOpenPanel={setOpenPanel} icon={<RiCalendarEventFill />} title="กำหนดปีการศึกษา / ภาคเรียน" subtitle="ตั้งค่าช่วงเวลาเริ่มต้นและสิ้นสุดของแต่ละเทอม" accentColor="#8b5cf6" />
          <AccordionBody id="semester" openPanel={openPanel}>
            <form onSubmit={handleSemesterSubmit} style={f.form}>
                <div style={f.row}>
                    <div style={f.fg}><label style={f.label}>ปีการศึกษา (พ.ศ.)</label><input type="number" required style={f.input} value={semData.academic_year} onChange={e => setSemData({...semData, academic_year: e.target.value})} disabled={!canManageSystem} /></div>
                    <div style={f.fg}><label style={f.label}>ภาคเรียน</label>
                        <select style={f.input} value={semData.semester} onChange={e => setSemData({...semData, semester: e.target.value})} disabled={!canManageSystem}>
                            <option value="1">เทอม 1</option><option value="2">เทอม 2</option><option value="Summer">เทอม Summer</option>
                        </select>
                    </div>
                </div>
                <div style={f.row}>
                    <div style={f.fg}>
                        <label style={f.label}>เริ่มต้น</label>
                        <ThaiDatePicker value={semData.start_date} onChange={val => setSemData({...semData, start_date: val})} disabled={!canManageSystem} />
                    </div>
                    <div style={f.fg}>
                        <label style={f.label}>สิ้นสุด</label>
                        <ThaiDatePicker value={semData.end_date} onChange={val => setSemData({...semData, end_date: val})} disabled={!canManageSystem} />
                    </div>
                </div>
                {canManageSystem ? (
                    <button type="submit" style={{...f.primaryBtn, background: '#8b5cf6'}}>บันทึกปีการศึกษา</button>
                ) : (
                    <div style={f.readOnlyNote}>หมายเหตุ: สิทธิ์ระดับ 3 ไม่สามารถบันทึกข้อมูลได้</div>
                )}
            </form>
            {semestersList.map(s => (
                <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: '#f8f9fa', marginTop: '5px', borderRadius: '6px' }}>
                    <span>ปี <b>{s.academic_year}</b> / <b>{s.semester}</b> ({formatThaiDate(s.start_date)} ถึง {formatThaiDate(s.end_date)})</span>
                    {canManageSystem && <button onClick={() => authFetch(`/api/system/semesters/${s.id}`, {method:'DELETE'}).then(fetchData)} style={{border:'none', background:'#fff1f0', color:'#cf1322', padding:'8px', margin:'0 3px', borderRadius:'6px', cursor:'pointer', display:'inline-flex'}}><RiDeleteBinFill size={16}/></button>}
                </div>
            ))}
          </AccordionBody>
        </div>

        <div style={{ marginBottom: '10px' }}>
          <AccordionTrigger id="block" openPanel={openPanel} setOpenPanel={setOpenPanel} icon={<RiLockFill />} title="ล็อกที่นั่ง / ตารางเรียน" subtitle="ล็อกที่นั่งตามตารางสอน" accentColor="#1677ff" />
          <AccordionBody id="block" openPanel={openPanel}>
            <form onSubmit={handleBlockSubmit} style={f.form}>
              <div style={f.row}>
                <div style={{...f.fg, flex: '0 0 auto', minWidth: '120px', maxWidth: '145px'}}><label style={f.label}>วัตถุประสงค์</label>
                  <select style={f.input} value={blockData.purpose} onChange={e => setBlockData({ ...blockData, purpose: e.target.value, seat_nos: [] })} disabled={!canManageSystem}>
                    {purposeOptions.map(p => <option key={p.value} value={p.value}>{p.value}</option>)}
                  </select>
                </div>
                
                {blockData.purpose === 'ตารางเรียน' ? (
                  <div style={f.fg}><label style={f.label}>ปีการศึกษา / ภาคเรียน</label>
                    <select required style={f.input} value={blockData.selected_semester_id} onChange={e => setBlockData({ ...blockData, selected_semester_id: e.target.value })} disabled={!canManageSystem}>
                      <option value="" disabled>-- เลือก --</option>
                      {semestersList.map(s => <option key={s.id} value={s.id}>ปี {s.academic_year} / {s.semester}</option>)}
                    </select>
                  </div>
                ) : (
                  <div style={f.fg}><label style={f.label}>วันที่ต้องการจอง</label>
                    <ThaiDatePicker value={blockData.single_date} onChange={val => setBlockData({...blockData, single_date: val})} minDate={`${currentYear}-01-01`} disabled={!canManageSystem} />
                  </div>
                )}
              </div>

              {blockData.purpose === 'ตารางเรียน' && (
                  <div style={f.row}>
                    <div style={{...f.fg, flex: 2}}><label style={f.label}>ชื่อวิชา</label><input type="text" placeholder="วิชา..." style={f.input} value={blockData.subject_name} onChange={e => setBlockData({ ...blockData, subject_name: e.target.value })} disabled={!canManageSystem} /></div>
                    <div style={{...f.fg, flex: 1}}><label style={f.label}>Section</label><input type="text" placeholder="336A" maxLength="5" style={f.input} value={blockData.section} onChange={e => setBlockData({ ...blockData, section: e.target.value })} disabled={!canManageSystem} /></div>
                    <div style={{...f.fg, flex: 2}}><label style={f.label}>อาจารย์</label><input type="text" placeholder="ชื่อผู้สอน..." style={f.input} value={blockData.teacher_name} onChange={e => setBlockData({ ...blockData, teacher_name: e.target.value })} disabled={!canManageSystem} /></div>
                  </div>
              )}

              {blockData.purpose === 'สอบ' && (
                  <div style={f.row}>
                    <div style={{...f.fg, flex: 2}}><label style={f.label}>ชื่อวิชา / รายวิชาสอบ</label><input type="text" placeholder="วิชา..." style={f.input} value={blockData.subject_name} onChange={e => setBlockData({ ...blockData, subject_name: e.target.value })} disabled={!canManageSystem} /></div>
                    <div style={{...f.fg, flex: 1}}><label style={f.label}>Section</label><input type="text" placeholder="336A" maxLength="5" style={f.input} value={blockData.section} onChange={e => setBlockData({ ...blockData, section: e.target.value })} disabled={!canManageSystem} /></div>
                    <div style={{...f.fg, flex: 2}}><label style={f.label}>ผู้คุมสอบ</label><input type="text" placeholder="ชื่อผู้คุมสอบ..." style={f.input} value={blockData.teacher_name} onChange={e => setBlockData({ ...blockData, teacher_name: e.target.value })} disabled={!canManageSystem} /></div>
                  </div>
              )}

              <div style={f.row}>
                {blockData.purpose === 'ตารางเรียน' && (
                  <div style={f.fg}><label style={f.label}>วันในสัปดาห์</label>
                      <select style={f.input} value={blockData.day_of_week} onChange={e => setBlockData({ ...blockData, day_of_week: e.target.value })} disabled={!canManageSystem}>{dayOfWeekOptions.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}</select>
                  </div>
                )}
                <div style={f.fg}><label style={f.label}>เริ่ม</label>
                    <select required style={f.input} value={blockData.start_time} onChange={e => setBlockData({ ...blockData, start_time: e.target.value })} disabled={!canManageSystem}><option value="" disabled>--:--</option>{timeOptions.map(t => <option key={t} value={t}>{t}</option>)}</select>
                </div>
                <div style={f.fg}><label style={f.label}>จบ</label>
                    <select required style={f.input} value={blockData.end_time} onChange={e => setBlockData({ ...blockData, end_time: e.target.value })} disabled={!canManageSystem}><option value="" disabled>--:--</option>{timeOptions.filter(t => t > blockData.start_time).map(t => <option key={t} value={t}>{t}</option>)}</select>
                </div>
              </div>

              <div style={f.fg}><label style={f.label}>ที่นั่ง <span style={{ fontWeight: '400', fontSize: '0.83rem', color: (blockData.purpose === 'ตารางเรียน' || blockData.purpose === 'สอบ') ? '#e53e3e' : '#888' }}>{(blockData.purpose === 'ตารางเรียน' || blockData.purpose === 'สอบ') ? '— ล็อคทั้งห้อง' : '— เลือกได้หลายที่'}</span></label>
                <SeatGrid selectedArray={blockData.seat_nos} onToggle={handleSeatToggle} forceAll={blockData.purpose === 'ตารางเรียน' || blockData.purpose === 'สอบ'} activeColor="#1677ff" />
              </div>

              <div style={f.fg}><label style={f.label}>หมายเหตุเพิ่มเติม</label><input type="text" style={f.input} value={blockData.note} onChange={e => setBlockData({ ...blockData, note: e.target.value })} disabled={!canManageSystem} /></div>
              
              {canManageSystem ? (
                <button type="submit" style={f.primaryBtn}>บันทึกตาราง</button>
              ) : (
                <div style={f.readOnlyNote}>หมายเหตุ: สิทธิ์ระดับ 3 ไม่สามารถบันทึกข้อมูลได้</div>
              )}
            </form>
          </AccordionBody>
        </div>

        <div style={{ marginBottom: '10px' }}>
          <AccordionTrigger id="broken" openPanel={openPanel} setOpenPanel={setOpenPanel} icon={<RiToolsFill />} title="แจ้งอุปกรณ์ขัดข้อง" subtitle="รายงานเครื่องที่ใช้งานไม่ได้" accentColor="#dc3545" />
          <AccordionBody id="broken" openPanel={openPanel}>
            <form onSubmit={handleBrokenSubmit} style={f.form}>
              <div style={f.fg}><label style={f.label}>เลือกที่นั่ง</label>
                <SeatGrid 
                  selectedArray={brokenData.seat_no ? [brokenData.seat_no] : []} 
                  onToggle={(num) => { 
                    if (!canManageSystem) return;
                    const isBroken = brokenList.some(b => b.status === 'broken' && b.seat_no === num);
                    if (isBroken) return;
                    setBrokenData({ seat_no: num });
                  }} 
                  forceAll={false} 
                  activeColor="#dc3545"
                  disabledArray={brokenList.filter(b => b.status === 'broken').map(b => b.seat_no)}
                />
              </div>
              <div style={f.fg}><label style={f.label}>อาการเสีย</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {issueOptions.map(issue => (
                    <label key={issue} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: canManageSystem ? 'pointer' : 'default' }}>
                      <input type="checkbox" checked={selectedIssues.includes(issue)} onChange={() => setSelectedIssues(p => p.includes(issue) ? p.filter(i => i !== issue) : [...p, issue])} disabled={!canManageSystem} /> {issue}
                    </label>
                  ))}
                  <input type="text" placeholder="อื่นๆ..." value={otherIssue} onChange={e => setOtherIssue(e.target.value)} style={f.input} disabled={!canManageSystem} />
                </div>
              </div>
              {canManageSystem ? (
                <button type="submit" style={f.dangerBtn}>ยืนยันแจ้งเสีย</button>
              ) : (
                <div style={f.readOnlyNote}>หมายเหตุ: สิทธิ์ระดับ 3 ไม่สามารถแจ้งข้อมูลได้</div>
              )}
            </form>
          </AccordionBody>
        </div>

        <div style={{ marginBottom: '36px' }}>
          <AccordionTrigger id="admins" openPanel={openPanel} setOpenPanel={setOpenPanel} icon={<RiShieldUserFill />} title="จัดการผู้ดูแลระบบ (Admin)" subtitle="เพิ่ม/ลบบัญชีและจัดการสิทธิ์แอดมิน" accentColor="#722ed1" />
          <AccordionBody id="admins" openPanel={openPanel}>
            
            <div style={{ backgroundColor: '#f0f5ff', padding: '15px', borderRadius: '8px', border: '1px solid #adc6ff', marginBottom: '20px', color: '#0958d9', fontSize: '0.9rem' }}>
              <strong style={{ display: 'block', marginBottom: '5px' }}>ความหมายของระดับความสำคัญ:</strong>
              <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><b>ระดับ 1:</b> จัดการได้ทุกอย่าง รวมถึงการแก้ไขหรือเพิ่ม/ลบข้อมูลแอดมินคนอื่นๆ</li>
                <li><b>ระดับ 2:</b> ไม่สามารถแก้ไขข้อมูลหรือเพิ่ม/ลบบัญชีแอดมินได้ (แต่จัดการตารางเรียนและแจ้งซ่อมได้)</li>
                <li><b>ระดับ 3:</b> ดูข้อมูลได้อย่างเดียว ไม่สามารถเพิ่ม แก้ไข หรือลบข้อมูลใดๆ ในระบบได้</li>
              </ul>
            </div>

            {canManageAdmin ? (
                <div style={{ backgroundColor: '#f9f0ff', padding: '20px', borderRadius: '10px', border: '1px dashed #d3adf7', marginBottom: '20px' }}>
                <h4 style={{ margin: '0 0 15px 0', color: '#531dab', display: 'flex', alignItems: 'center', gap: '8px' }}><RiUserAddLine size={18}/> เพิ่มบัญชีแอดมินใหม่</h4>
                <form onSubmit={handleAddAdmin} style={f.form}>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>รหัสพนักงาน *</label><input type="text" name="staff_id" value={newAdmin.staff_id} onChange={handleAdminChange} required style={f.input} /></div>
                        <div style={{...f.fg, flex: '0 0 auto', minWidth: '100px', maxWidth: '130px'}}>
                            <label style={f.label}>ระดับสิทธิ์</label>
                            <select name="priority" value={newAdmin.priority} onChange={handleAdminChange} style={f.input}>
                                <option value={1}>1</option>
                                <option value={2}>2</option>
                                <option value={3}>3</option>
                            </select>
                        </div>
                    </div>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>ชื่อ *</label><input type="text" name="first_name" value={newAdmin.first_name} onChange={handleAdminChange} required style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>นามสกุล</label><input type="text" name="last_name" value={newAdmin.last_name} onChange={handleAdminChange} style={f.input} /></div>
                    </div>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>แผนก</label><input type="text" name="department" value={newAdmin.department} onChange={handleAdminChange} placeholder="" style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>ตำแหน่ง</label><input type="text" name="position" value={newAdmin.position} onChange={handleAdminChange} placeholder="" style={f.input} /></div>
                    </div>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>Username *</label><input type="text" name="username" value={newAdmin.username} onChange={handleAdminChange} required style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>Password *</label><input type="password" name="password" value={newAdmin.password} onChange={handleAdminChange} required style={f.input} /></div>
                    </div>
                    <button type="submit" style={{...f.primaryBtn, background: '#722ed1', marginTop: '5px'}}>บันทึกแอดมินใหม่</button>
                </form>
                </div>
            ) : (
                <div style={{ backgroundColor: '#fff1f0', color: '#cf1322', padding: '15px', borderRadius: '8px', border: '1px solid #ffa39e', marginBottom: '20px', fontSize: '0.9rem', textAlign: 'center', fontWeight: 'bold' }}>
                    สิทธิ์ระดับ {currentPriority} ไม่สามารถเพิ่ม แก้ไข หรือลบข้อมูลผู้ดูแลระบบได้
                </div>
            )}

            {/* 🟢 ตารางรายชื่อ Admin ปรับใส่ Card */}
            <div style={f.tableWrap}>
              <table style={tableStyles.table}>
                <thead>
                  <tr>
                    <th style={tableStyles.th}>สิทธิ์</th>
                    <th style={tableStyles.th}>รหัสพนักงาน</th>
                    <th style={tableStyles.th}>ชื่อ-นามสกุล</th>
                    <th style={tableStyles.th}>แผนก</th>
                    <th style={tableStyles.th}>ตำแหน่ง</th>
                    <th style={tableStyles.th}>Username</th>
                    {canManageAdmin && <th style={{...tableStyles.th, textAlign: 'center'}}>จัดการ</th>}
                  </tr>
                </thead>
                <tbody>
                  {adminsList.map(admin => (
                    <tr key={admin.staff_id}>
                      <td style={tableStyles.td}>{getPriorityTag(admin.priority)}</td>
                      <td style={{...tableStyles.td, fontWeight: 'bold'}}>{admin.staff_id}</td>
                      <td style={tableStyles.td}>{admin.first_name} {admin.last_name}</td>
                      <td style={tableStyles.td}>{admin.department}</td>
                      <td style={tableStyles.td}>{admin.position}</td>
                      <td style={tableStyles.td}>{admin.username}</td>
                      {canManageAdmin && (
                        <td style={{...tableStyles.td, textAlign: 'center'}}>
                          <button onClick={() => openEditAdminModal(admin)} style={{border:'none', background:'#e6f4ff', color:'#1677ff', padding:'8px', margin:'0 3px', borderRadius:'6px', cursor:'pointer', display:'inline-flex'}}><RiEdit2Fill size={16}/></button>
                          <button onClick={() => handleDeleteAdmin(admin.staff_id, `${admin.first_name} ${admin.last_name}`)} style={{border:'none', background:'#fff1f0', color:'#cf1322', padding:'8px', margin:'0 3px', borderRadius:'6px', cursor:'pointer', display:'inline-flex'}}><RiDeleteBinFill size={16}/></button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </AccordionBody>
        </div>

        {/* 🟢 ตารางล็อกที่นั่ง ปรับใส่ Card */}
        <div style={pageStyles.card}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '9px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RiCalendarEventFill color="#1677ff"/> รายการล็อกที่นั่ง / ตารางเรียน
            </h3>
            <div style={tableStyles.wrap}>
            <table style={tableStyles.table}>
                <thead>
                <tr>
                    <th style={tableStyles.th}>ปีการศึกษา / เทอม</th>
                    <th style={tableStyles.th}>วัน</th>
                    <th style={tableStyles.th}>เวลา</th>
                    <th style={tableStyles.th}>รายละเอียด (วิชา/ผู้สอน)</th>
                    <th style={tableStyles.th}>ที่นั่ง</th>
                    {canManageSystem && <th style={tableStyles.th}>ลบ</th>}
                </tr>
                </thead>
                <tbody>
                {schedules.map(row => (
                    <tr key={row.id}>
                    <td style={tableStyles.td}>
                        {row.academic_year 
                        ? <span style={{ color: '#8b5cf6', fontWeight: 'bold' }}>ปี {row.academic_year} / {row.semester}</span>
                        : <span style={{ color: '#555' }}>{formatThaiDate(row.start_date)}</span>
                        }
                    </td>
                    <td style={tableStyles.td}>{getDayLabel(row.day_of_week)}</td>
                    <td style={tableStyles.td}>{row.start_time.slice(0,5)} - {row.end_time.slice(0,5)}</td>
                    <td style={tableStyles.td}>
                        {row.subject_name !== '-' 
                          ? <><b>{row.subject_name}</b>{row.purpose === 'สอบ' && <span style={{ marginLeft: '6px', background: '#fff1f0', color: '#cf1322', padding: '1px 7px', borderRadius: '10px', fontSize: '0.78rem', fontWeight: 'bold' }}>สอบ</span>}</>
                          : <b>{row.purpose}</b>
                        }
                        {row.section !== '-' && ` Sec.${row.section}`}<br/>
                        <small style={{color:'#888'}}>{row.teacher_name !== '-' ? `(${row.teacher_name})` : ''}</small>
                    </td>
                    <td style={tableStyles.td}>{row.seat_no || 'ทั้งห้อง'}</td>
                    {canManageSystem && <td style={tableStyles.td}><button onClick={() => handleDeleteSchedule(row.id)} style={{border:'none', background:'#fff1f0', color:'#cf1322', padding:'8px', margin:'0 3px', borderRadius:'6px', cursor:'pointer', display:'inline-flex'}}><RiDeleteBinFill size={16}/></button></td>}
                    </tr>
                ))}
                {schedules.length === 0 && <tr><td colSpan={canManageSystem ? "6" : "5"} style={{ ...tableStyles.td, textAlign: 'center', color: '#ccc' }}>ไม่มีข้อมูล</td></tr>}
                </tbody>
            </table>
            </div>
        </div>

        {/* 🟢 ตารางแจ้งซ่อม ปรับใส่ Card */}
        <div style={{...pageStyles.card, marginTop: '30px'}}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '9px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RiToolsFill color="#dc3545"/> ประวัติแจ้งอุปกรณ์ขัดข้อง
            </h3>
            <div style={tableStyles.wrap}>
            <table style={tableStyles.table}>
                <thead>
                <tr>
                    <th style={tableStyles.th}>วันแจ้ง</th>
                    <th style={tableStyles.th}>ที่นั่ง</th>
                    <th style={tableStyles.th}>อาการ</th>
                    <th style={tableStyles.th}>สถานะ</th>
                    <th style={tableStyles.th}>ซ่อมเสร็จ</th>
                    {canManageSystem && <th style={tableStyles.th}>จัดการ</th>}
                </tr>
                </thead>
                <tbody>
                {brokenList.map(b => (
                    <tr key={b.id}>
                    <td style={tableStyles.td}>{formatThaiDate(b.broken_date)}</td>
                    <td style={tableStyles.td}><b>PC{String(b.seat_no).padStart(2, '0')}</b></td>
                    <td style={tableStyles.td}>{b.note}</td>
                    <td style={tableStyles.td}>{b.status === 'broken' ? <span style={{...pageStyles.badge, background: '#fff1f0', color: '#cf1322'}}>เสีย</span> : <span style={{...pageStyles.badge, background: '#f6ffed', color: '#389e0d'}}>ปกติ</span>}</td>
                    <td style={tableStyles.td}>{b.fixed_date ? formatThaiDate(b.fixed_date) : '-'}</td>
                    {canManageSystem && <td style={tableStyles.td}>{b.status === 'broken' && <button onClick={() => handleResolveBroken(b.id)} style={{border:'none', background:'#f6ffed', color:'#389e0d', padding:'8px', margin:'0 3px', borderRadius:'6px', cursor:'pointer', display:'inline-flex'}}><RiCheckFill size={16}/></button>}</td>}
                    </tr>
                ))}
                {brokenList.length === 0 && <tr><td colSpan={canManageSystem ? "6" : "5"} style={{ ...tableStyles.td, textAlign: 'center', color: '#ccc' }}>ไม่มีข้อมูล</td></tr>}
                </tbody>
            </table>
            </div>
        </div>

      </div>

      {isEditModalOpen && editingAdmin && (
        <div style={f.modalBackdrop} onClick={() => setIsEditModalOpen(false)}>
            <div style={f.modalContent} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '15px', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0, color: '#722ed1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <RiEdit2Fill /> แก้ไขข้อมูลแอดมิน: {editingAdmin.staff_id}
                    </h3>
                    <button style={f.closeModalBtn} onClick={() => setIsEditModalOpen(false)}><RiCloseLine size={24} /></button>
                </div>

                <form onSubmit={handleEditAdminSubmit} style={f.form}>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>แผนก</label><input type="text" name="department" value={editingAdmin.department} onChange={handleEditAdminChange} style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>ตำแหน่ง</label><input type="text" name="position" value={editingAdmin.position} onChange={handleEditAdminChange} style={f.input} /></div>
                    </div>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>ชื่อ *</label><input type="text" name="first_name" value={editingAdmin.first_name} onChange={handleEditAdminChange} required style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>นามสกุล</label><input type="text" name="last_name" value={editingAdmin.last_name} onChange={handleEditAdminChange} style={f.input} /></div>
                    </div>
                    <div style={f.row}>
                        <div style={f.fg}><label style={f.label}>Username *</label><input type="text" name="username" value={editingAdmin.username} onChange={handleEditAdminChange} required style={f.input} /></div>
                        <div style={f.fg}><label style={f.label}>Passwordใหม่ (เว้นว่างถ้าไม่เปลี่ยน)</label><input type="password" name="password" value={editingAdmin.password} onChange={handleEditAdminChange} style={f.input} placeholder="********" /></div>
                        <div style={f.fg}>
                            <label style={f.label}>ระดับสิทธิ์</label>
                            <select name="priority" value={editingAdmin.priority} onChange={handleEditAdminChange} style={f.input}>
                                <option value={1}>1</option>
                                <option value={2}>2</option>
                                <option value={3}>3</option>
                            </select>
                        </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                        <button type="button" onClick={() => setIsEditModalOpen(false)} style={{...f.primaryBtn, background: '#f1f5f9', color: '#475569'}}>ยกเลิก</button>
                        <button type="submit" style={{...f.primaryBtn, background: '#722ed1', display: 'flex', alignItems: 'center', gap: '5px'}}><RiSave3Line size={18}/> บันทึกการแก้ไข</button>
                    </div>
                </form>
            </div>
        </div>
      )}

    </AdminLayout>
  );
}

const f = {
  form: { display: 'flex', flexDirection: 'column', gap: '14px' },
  row: { display: 'flex', gap: '12px', alignItems: 'flex-start' },
  fg: { display: 'flex', flexDirection: 'column', gap: '5px', flex: 1 },
  label: { fontSize: '0.9rem', fontWeight: '700', color: '#4a5568' },
  input: { padding: '10px', border: '1px solid #ddd', borderRadius: '8px', width: '100%', boxSizing: 'border-box', outline: 'none' },
  primaryBtn: { padding: '12px', background: '#1677ff', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', transition: 'opacity 0.2s' },
  dangerBtn: { padding: '12px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', transition: 'opacity 0.2s' },
  tableWrap: { overflowX: 'auto', background: 'white', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#f8f9fa', textAlign: 'left', padding: '12px', borderBottom: '2px solid #eee', fontSize: '0.85rem' },
  td: { padding: '12px', borderBottom: '1px solid #f0f0f0', fontSize: '0.9rem' },
  modalBackdrop: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999, backdropFilter: 'blur(3px)' },
  modalContent: { position: 'relative', width: '100%', maxWidth: '650px', background: 'white', borderRadius: '16px', padding: '30px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)', maxHeight: '90vh', overflowY: 'auto' },
  closeModalBtn: { background: '#f8fafc', border: 'none', borderRadius: '50%', color: '#64748b', cursor: 'pointer', padding: '6px', display: 'flex', transition: 'background 0.2s' }
};