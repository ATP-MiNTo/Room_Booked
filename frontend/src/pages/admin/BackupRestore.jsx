import { useState, useEffect, useRef } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import Swal from 'sweetalert2';
import { 
  RiDatabase2Fill, 
  RiHistoryFill, 
  RiDownloadCloud2Fill, 
  RiUploadCloud2Fill, 
  RiArrowDownSFill,
  RiInformationFill,
  RiFileZipLine,
  RiRefreshLine
} from 'react-icons/ri';

import { THAI_MONTHS_SHORT } from '../../utils/dateUtils';
import { pageStyles, tableStyles, btnStyles } from '../../utils/uiConstants';
import { authFetch } from '../../utils/authFetch';

export default function BackupRestore() {
  const currentAdminId = sessionStorage.getItem('adminId');
  const today = new Date().toISOString().split("T")[0];
  const currentYear = new Date().getFullYear();

  const [openPanel, setOpenPanel] = useState(null); 
  const [restoreFile, setRestoreFile] = useState(null);
  const fileInputRef = useRef(null); 
  
  const [backupMode, setBackupMode] = useState('all');
  const [startDate, setStartDate] = useState(`${currentYear}-01-01`);
  const [endDate, setEndDate] = useState(today);

  const [backupHistory, setBackupHistory] = useState([]); 

  const formatLogDate = (dateStr) => {
    if (!dateStr) return { date: '-', time: '-' };
    try {
      const [datePart, timePart] = dateStr.split(' ');
      if (datePart && timePart) {
        const [d, m, y] = datePart.split('/');
        const thaiYear = parseInt(y) < 2400 ? parseInt(y) + 543 : parseInt(y);
        
        return {
            date: `${parseInt(d)} ${THAI_MONTHS_SHORT[parseInt(m) - 1]} ${thaiYear}`,
            time: `${timePart} น.`
        };
      }
      return { date: dateStr, time: '-' };
    } catch (e) {
      return { date: dateStr, time: '-' };
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await authFetch('/api/system/logs');
      if (res.ok) {
        const data = await res.json();
        setBackupHistory(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleBackup = async () => {
    let queryStart = startDate;
    let queryEnd = endDate;

    if (backupMode === 'all') {
        queryStart = 'all';
        queryEnd = 'all';
    } else if (!startDate || !endDate) {
        return Swal.fire('แจ้งเตือน', 'กรุณาเลือกช่วงวันที่ให้ครบถ้วน', 'warning');
    }

    try {
      Swal.fire({
        title: 'กำลังบีบอัดข้อมูล...',
        text: 'กำลังรวบรวมฐานข้อมูลและรูปภาพใบหน้าเป็นไฟล์ .zip โปรดรอสักครู่',
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading()
      });

      const adminParam = currentAdminId ? `&admin_id=${currentAdminId}` : '';
      const res = await authFetch(`/api/system/backup?start_date=${queryStart}&end_date=${queryEnd}${adminParam}`);
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const now = new Date();
        const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`;
        const fileNameSuffix = backupMode === 'all' ? 'all_time' : `${startDate}_to_${endDate}`;
        a.download = `complab_backup_${fileNameSuffix}_${timestamp}.zip`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        Swal.fire('สำเร็จ!', 'ดาวน์โหลดไฟล์สำรองข้อมูล (.zip) เรียบร้อยแล้ว', 'success');
        fetchLogs(); 
      } else {
        const errData = await res.json().catch(() => ({ detail: "ไม่ทราบสาเหตุแน่ชัด" }));
        Swal.fire('ข้อผิดพลาด', `Backend Error: ${typeof errData.detail === 'string' ? errData.detail : 'ไม่ทราบสาเหตุ'}`, 'error');
      }
    } catch (error) {
      console.error(error);
      Swal.fire('ข้อผิดพลาด', 'ไม่สามารถติดต่อเซิร์ฟเวอร์ได้', 'error');
    }
  };

  const handleMigrateSubmit = async (e) => {
    e.preventDefault();
    if (!restoreFile) {
      return Swal.fire('แจ้งเตือน', 'กรุณาเลือกไฟล์ .zip ก่อนนำเข้า', 'warning');
    }

    const confirm = await Swal.fire({
      title: 'คำเตือนการนำเข้าข้อมูล',
      html: 'ระบบจะนำเข้าข้อมูลตารางและรูปภาพที่อยู่ในไฟล์ ZIP <b>เข้าระบบ (Migration)</b><br/>(หากมีข้อมูลที่ซ้ำกันอยู่แล้ว ระบบจะข้ามไป ไม่ลบข้อมูลปัจจุบันทิ้ง)',
      icon: 'info',
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonText: 'ยกเลิก',
      confirmButtonText: 'ยืนยันการนำเข้า'
    });

    if (confirm.isConfirmed) {
      try {
        Swal.fire({
          title: 'กำลังแตกไฟล์นำเข้า...',
          text: 'กำลังอัปโหลดรูปภาพขึ้น Cloud อาจใช้เวลาสักครู่ ห้ามปิดหน้าต่างนี้เด็ดขาด',
          allowOutsideClick: false,
          didOpen: () => Swal.showLoading()
        });

        const formData = new FormData();
        formData.append('file', restoreFile);
        formData.append('admin_id', currentAdminId || 'unknown');

        // กลับมาใช้ authFetch ตามเดิมของคุณ เพื่อแก้ปัญหา 401 Unauthorized
        const res = await authFetch('/api/system/migrate', { 
          method: 'POST', 
          body: formData 
        });

        if (res.ok) {
          Swal.fire('สำเร็จ!', 'นำเข้าฐานข้อมูลและรูปภาพขึ้น Cloud เรียบร้อยแล้ว', 'success').then(() => {
            setRestoreFile(null);
            if (fileInputRef.current) fileInputRef.current.value = ""; 
            fetchLogs(); 
          });
        } else {
          const errData = await res.json().catch(() => ({ detail: "ไฟล์เสียหาย" }));
          Swal.fire('ข้อผิดพลาด', `การนำเข้าล้มเหลว: ${typeof errData.detail === 'string' ? errData.detail : 'ไม่ทราบสาเหตุ'}`, 'error');
        }
      } catch (error) {
        Swal.fire('ข้อผิดพลาด', 'ไม่สามารถติดต่อเซิร์ฟเวอร์ได้', 'error');
      }
    }
  };

  const handleBoxClick = () => {
    if (fileInputRef.current) {
        fileInputRef.current.click();
    }
  };

  return (
    <AdminLayout>
      {/* ขยายความกว้างให้ตรงกับหน้าอื่น */}
      <div style={{ padding: '10px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>

        {/* Header มาตรฐาน */}
        <div style={pageStyles.header}>
          <h2 style={pageStyles.title}>
            <RiDatabase2Fill color="#1677ff" /> Backup & Migration
          </h2>
          <button onClick={fetchLogs} style={btnStyles.refresh}>
            <RiRefreshLine /> Refresh
          </button>
        </div>

        {/* แบ่งครึ่ง 2 ฝั่ง ซ้าย Backup ขวา Migrate */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '30px' }}>
          
          {/* สำรองข้อมูล */}
          <div style={pageStyles.card}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '10px' }}>
              <div style={{ backgroundColor: '#e6f4ff', padding: '15px', borderRadius: '50%', marginBottom: '15px' }}>
                <RiDownloadCloud2Fill size={40} color="#1677ff" />
              </div>
              <h3 style={{ color: '#2c3e50', margin: '0 0 15px 0' }}>เลือกขอบเขตการสำรองข้อมูล</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px', width: '100%', maxWidth: '400px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 'bold', color: '#555' }}>
                  <input 
                    type="radio" 
                    name="backupMode" 
                    checked={backupMode === 'all'} 
                    onChange={() => setBackupMode('all')} 
                    style={{ transform: 'scale(1.2)' }}
                  />
                  สำรองทั้งหมด
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 'bold', color: '#555' }}>
                  <input 
                    type="radio" 
                    name="backupMode" 
                    checked={backupMode === 'range'} 
                    onChange={() => setBackupMode('range')} 
                    style={{ transform: 'scale(1.2)' }}
                  />
                  กำหนดช่วงเวลา
                </label>
              </div>

              {backupMode === 'range' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px', width: '100%', maxWidth: '400px' }}>
                  <div style={{ textAlign: 'left' }}>
                    <label style={f.label}>ตั้งแต่วันที่</label>
                    <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{...f.input, marginTop: '5px'}} required />
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <label style={f.label}>ถึงวันที่</label>
                    <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{...f.input, marginTop: '5px'}} required />
                  </div>
                </div>
              )}

              <button onClick={handleBackup} style={{ ...f.primaryBtn, width: '100%', maxWidth: '400px', padding: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
                <RiDatabase2Fill size={18} /> โหลดไฟล์ Backup (.zip)
              </button>
            </div>
          </div>

          {/* นำเข้าข้อมูล */}
          <div style={pageStyles.card}>
            <form onSubmit={handleMigrateSubmit} style={f.form}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '10px' }}>
                <div style={{ backgroundColor: '#fff1f0', padding: '15px', borderRadius: '50%', marginBottom: '15px' }}>
                  <RiUploadCloud2Fill size={40} color="#dc3545" />
                </div>
                <h3 style={{ color: '#2c3e50', margin: '0 0 15px 0' }}>นำเข้าข้อมูล (Data Migration)</h3>

                <div style={{ backgroundColor: '#fff1f0', border: '1px solid #ffa39e', padding: '15px', borderRadius: '8px', display: 'flex', gap: '10px', alignItems: 'flex-start', marginBottom: '20px', width: '100%' }}>
                  <RiInformationFill size={24} color="#cf1322" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ fontSize: '0.9rem', color: '#cf1322', lineHeight: '1.5', textAlign: 'left' }}>
                    ระบบจะทำการแตกไฟล์และนำเข้า <b>ข้อมูลฐานข้อมูล และรูปภาพขึ้น Cloud</b> รวมเข้ากับระบบปัจจุบัน (หากมีข้อมูลเดิมอยู่แล้ว ระบบจะข้ามไปโดยอัตโนมัติ)
                  </div>
                </div>

                <div style={{...f.fg, width: '100%'}}>
                  <div 
                      onClick={handleBoxClick}
                      style={{ 
                          border: '2px dashed #ddd', 
                          padding: '30px', 
                          textAlign: 'center', 
                          borderRadius: '10px', 
                          cursor: 'pointer',
                          backgroundColor: restoreFile ? '#e6f4ff' : '#fafafa',
                          borderColor: restoreFile ? '#1677ff' : '#ddd',
                          transition: 'all 0.2s'
                      }}
                  >
                      <RiFileZipLine size={40} color={restoreFile ? '#1677ff' : '#aaa'} style={{ marginBottom: '10px' }} />
                      <div style={{ color: restoreFile ? '#1677ff' : '#666', fontWeight: 'bold', fontSize: '1rem' }}>
                          {restoreFile ? `เลือกไฟล์แล้ว: ${restoreFile.name}` : 'คลิกเพื่อเลือกไฟล์ .zip'}
                      </div>
                  </div>

                  <input 
                    type="file" 
                    accept=".zip" 
                    ref={fileInputRef}
                    onChange={(e) => {
                        if(e.target.files && e.target.files.length > 0) {
                            setRestoreFile(e.target.files[0]);
                        }
                    }} 
                    style={{ display: 'none' }} 
                  />
                </div>

                <button type="submit" disabled={!restoreFile} style={{ ...f.dangerBtn, width: '100%', padding: '12px', marginTop: '20px', opacity: restoreFile ? 1 : 0.5, cursor: restoreFile ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <RiUploadCloud2Fill size={18} /> ยืนยันการนำเข้าข้อมูล
                </button>
              </div>
            </form>
          </div>

        </div>

        {/* ========== ตารางประวัติ ========== */}
        <div style={pageStyles.card}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#2c3e50', borderBottom: '2px solid #eee', paddingBottom: '9px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RiHistoryFill color="#64748b" /> ประวัติการสำรองและการนำเข้าข้อมูล (Logs)
          </h3>
          <div style={tableStyles.wrap}>
            <table style={tableStyles.table}>
              <thead>
                <tr>
                  <th style={{...tableStyles.th, width: '25%'}}>วันที่ / เวลา</th>
                  <th style={tableStyles.th}>ประเภทรายการ</th>
                  <th style={tableStyles.th}>ผู้ดำเนินการ</th>
                  <th style={tableStyles.th}>ชื่อไฟล์</th>
                </tr>
              </thead>
              <tbody>
                {backupHistory.length > 0 ? (
                  backupHistory.map((item, idx) => {
                    const formatted = formatLogDate(item.date);
                    return (
                      <tr key={idx}>
                        <td style={{...tableStyles.td, fontWeight: 'bold', color: '#444'}}>{formatted.date}<br/><small style={{color:'#64748b', fontWeight:'normal'}}>{formatted.time}</small></td>
                        <td style={tableStyles.td}>
                          {item.type === 'backup' 
                            ? <span style={{ ...pageStyles.badge, background: '#e6f4ff', color: '#1677ff' }}>สำรองข้อมูล</span> 
                            : <span style={{ ...pageStyles.badge, background: '#fff1f0', color: '#dc3545' }}>นำเข้าข้อมูล</span>
                          }
                        </td>
                        <td style={tableStyles.td}>{item.admin_name}</td>
                        <td style={tableStyles.td}><small style={{ color: '#888', wordBreak: 'break-all' }}>{item.file_name}</small></td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="4" style={{ ...tableStyles.td, textAlign: 'center', color: '#ccc', padding: '30px' }}>
                      ยังไม่มีประวัติการทำรายการล่าสุด
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </AdminLayout>
  );
}

const f = {
  form:         { display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' },
  fg:           { display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 },
  label:        { fontSize: '0.9rem', fontWeight: '700', color: '#4a5568' },
  input:        { padding: '9px 11px', border: '1px solid #ddd', borderRadius: '8px', fontSize: '0.93rem', outline: 'none', width: '100%', boxSizing: 'border-box' },
  primaryBtn:   { padding: '10px', background: '#1677ff', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', fontSize: '0.95rem', marginTop: '4px' },
  dangerBtn:    { padding: '10px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', fontSize: '0.95rem', marginTop: '4px' },
};