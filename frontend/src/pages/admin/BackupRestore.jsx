import { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import { 
    RiDownloadCloud2Line, 
    RiUploadCloud2Line, 
    RiHistoryLine, 
    RiFileZipLine, 
    RiAlertLine,
    RiDatabase2Line
} from 'react-icons/ri';
import AdminLayout from '../../components/admin/AdminLayout';
import { authFetch } from '../../utils/authFetch';
import { pageStyles, btnStyles } from '../../utils/uiConstants';

export default function BackupRestore() {
    const [logs, setLogs] = useState([]);
    const [backupType, setBackupType] = useState('all'); // 'all' หรือ 'custom'
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

    // ดึงข้อมูล Admin จาก LocalStorage
    const adminData = JSON.parse(localStorage.getItem('admin') || '{}');
    const adminId = adminData.staff_id || 'unknown';

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= 768);
        window.addEventListener('resize', handleResize);
        fetchLogs();
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const fetchLogs = async () => {
        try {
            const res = await authFetch('/api/system/logs');
            if (res.ok) {
                const data = await res.json();
                setLogs(data);
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
        }
    };

    // ฟังก์ชันสำหรับดาวน์โหลดไฟล์ Backup
    const handleBackup = async () => {
        if (backupType === 'custom' && (!startDate || !endDate)) {
            Swal.fire('แจ้งเตือน', 'กรุณาเลือกช่วงวันที่ให้ครบถ้วน', 'warning');
            return;
        }
        if (backupType === 'custom' && startDate > endDate) {
            Swal.fire('แจ้งเตือน', 'วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด', 'warning');
            return;
        }

        Swal.fire({
            title: 'กำลังเตรียมไฟล์สำรองข้อมูล...',
            text: 'รวมรูปภาพและฐานข้อมูล อาจใช้เวลาสักครู่',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        try {
            const start = backupType === 'all' ? 'all' : startDate;
            const end = backupType === 'all' ? 'all' : endDate;
            
            const res = await authFetch(`/api/system/backup?start_date=${start}&end_date=${end}&admin_id=${adminId}`);
            
            if (!res.ok) throw new Error('เกิดข้อผิดพลาดในการสำรองข้อมูล');

            // รับไฟล์ Zip กลับมาแล้วบังคับดาวน์โหลด
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            // ดึงชื่อไฟล์จาก Header Content-Disposition ถ้ามี
            const contentDisposition = res.headers.get('Content-Disposition');
            let filename = `complab_backup_${new Date().getTime()}.zip`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename=(.+)/);
                if (filenameMatch && filenameMatch.length === 2) {
                    filename = filenameMatch[1];
                }
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            Swal.fire('สำเร็จ', 'ดาวน์โหลดไฟล์สำรองข้อมูลเรียบร้อยแล้ว', 'success');
            fetchLogs(); // โหลดประวัติใหม่
        } catch (error) {
            Swal.fire('ผิดพลาด', error.message, 'error');
        }
    };

    // ฟังก์ชันสำหรับอัปโหลดไฟล์ Restore/Migrate
    const handleRestore = async () => {
        if (!selectedFile) {
            Swal.fire('แจ้งเตือน', 'กรุณาเลือกไฟล์ .zip ที่ต้องการนำเข้า', 'warning');
            return;
        }

        const confirm = await Swal.fire({
            title: 'ยืนยันการนำเข้าข้อมูล?',
            html: '<p style="color: #d32f2f;">ข้อมูลใหม่จะถูกนำไปผสาน (Merge) เข้ากับข้อมูลเดิม หากมีรหัสซ้ำ ระบบจะยึดข้อมูลเดิมเป็นหลัก</p>แน่ใจหรือไม่ที่จะนำเข้าไฟล์นี้?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#1677ff',
            cancelButtonColor: '#d33',
            confirmButtonText: 'ยืนยันการนำเข้า',
            cancelButtonText: 'ยกเลิก'
        });

        if (confirm.isConfirmed) {
            Swal.fire({
                title: 'กำลังนำเข้าและอัปโหลดรูปภาพ...',
                text: 'กระบวนการนี้อาจใช้เวลานาน ห้ามปิดหน้านี้เด็ดขาด',
                allowOutsideClick: false,
                didOpen: () => Swal.showLoading()
            });

            try {
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('admin_id', adminId);

                // เปลี่ยนเป็น fetch ปกติที่ไม่กำหนด Content-Type (ให้เบราว์เซอร์จัดการ Boundary เอง)
                const token = localStorage.getItem('token');
                const res = await fetch('/api/system/migrate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                        // ไม่ต้องใส่ Content-Type: application/json เพราะเป็น multipart/form-data
                    },
                    body: formData
                });

                const data = await res.json();
                
                if (res.ok) {
                    Swal.fire('สำเร็จ', 'นำเข้าข้อมูลและรูปภาพสำเร็จ', 'success');
                    setSelectedFile(null);
                    document.getElementById('file-upload').value = '';
                    fetchLogs();
                } else {
                    throw new Error(data.detail || 'เกิดข้อผิดพลาดในการนำเข้าข้อมูล');
                }
            } catch (error) {
                Swal.fire('ผิดพลาด', error.message, 'error');
            }
        }
    };

    return (
        <AdminLayout>
            <div style={{ padding: isMobile ? '15px' : '30px', maxWidth: '1200px', margin: '0 auto' }}>
                <div style={pageStyles.header}>
                    <h2 style={pageStyles.title}>
                        <RiDatabase2Line color="#1677ff" /> สำรองและนำเข้าข้อมูล
                    </h2>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
                    
                    {/* การสำรองข้อมูล (Backup) */}
                    <div style={{ ...pageStyles.card, borderTop: '4px solid #1677ff' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#1e293b' }}>
                            <RiDownloadCloud2Line size={24} color="#1677ff" /> ส่งออกไฟล์สำรอง (Backup)
                        </h3>
                        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '20px' }}>
                            ระบบจะบีบอัดข้อมูลฐานข้อมูลและรูปภาพทั้งหมดเป็นไฟล์ .zip เพื่อเก็บรักษาอย่างปลอดภัย
                        </p>

                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', color: '#334155' }}>เลือกช่วงข้อมูล:</label>
                            <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                                    <input 
                                        type="radio" 
                                        checked={backupType === 'all'} 
                                        onChange={() => setBackupType('all')} 
                                    /> ข้อมูลทั้งหมด
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                                    <input 
                                        type="radio" 
                                        checked={backupType === 'custom'} 
                                        onChange={() => setBackupType('custom')} 
                                    /> กำหนดเอง
                                </label>
                            </div>

                            {backupType === 'custom' && (
                                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', backgroundColor: '#f8fafc', padding: '15px', borderRadius: '8px' }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontSize: '0.85rem', marginBottom: '5px', color: '#64748b' }}>ตั้งแต่วันที่:</div>
                                        <input 
                                            type="date" 
                                            value={startDate} 
                                            onChange={e => setStartDate(e.target.value)}
                                            style={pageStyles.input} 
                                        />
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontSize: '0.85rem', marginBottom: '5px', color: '#64748b' }}>ถึงวันที่:</div>
                                        <input 
                                            type="date" 
                                            value={endDate} 
                                            onChange={e => setEndDate(e.target.value)}
                                            style={pageStyles.input} 
                                        />
                                    </div>
                                </div>
                            )}
                        </div>

                        <button 
                            onClick={handleBackup} 
                            style={{ ...btnStyles.primary, width: '100%', padding: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontSize: '1rem' }}
                        >
                            <RiDownloadCloud2Line size={20} /> ดาวน์โหลดไฟล์ Backup (.zip)
                        </button>
                    </div>

                    {/* การนำเข้าข้อมูล (Restore/Migrate) */}
                    <div style={{ ...pageStyles.card, borderTop: '4px solid #10b981' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#1e293b' }}>
                            <RiUploadCloud2Line size={24} color="#10b981" /> นำเข้าข้อมูล (Migrate)
                        </h3>
                        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '20px' }}>
                            อัปโหลดไฟล์ .zip ที่ได้จากการ Backup ข้อมูลจะถูกนำไปผสานรวม (Merge) กับระบบปัจจุบัน
                        </p>

                        <div style={{ backgroundColor: '#fffbe6', border: '1px solid #ffe58f', padding: '12px', borderRadius: '8px', marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                            <RiAlertLine color="#faad14" size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                            <div style={{ fontSize: '0.85rem', color: '#d48806', lineHeight: '1.5' }}>
                                <strong>ข้อควรระวัง:</strong> การนำเข้าจะยึดข้อมูลปัจจุบันเป็นหลัก หากรหัสซ้ำ ระบบจะไม่เขียนทับข้อมูลเดิม และรูปภาพจะถูกอัปโหลดขึ้น Cloud อัตโนมัติ
                            </div>
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <label 
                                htmlFor="file-upload" 
                                style={{
                                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                    border: '2px dashed #cbd5e1', borderRadius: '8px', padding: '30px', cursor: 'pointer',
                                    backgroundColor: selectedFile ? '#f0fdf4' : '#f8fafc', transition: 'all 0.3s'
                                }}
                            >
                                <RiFileZipLine size={40} color={selectedFile ? '#10b981' : '#94a3b8'} style={{ marginBottom: '10px' }} />
                                <span style={{ color: selectedFile ? '#166534' : '#475569', fontWeight: 'bold' }}>
                                    {selectedFile ? selectedFile.name : 'คลิกเพื่อเลือกไฟล์ .zip'}
                                </span>
                                {selectedFile && <span style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '5px' }}>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</span>}
                                <input 
                                    id="file-upload" 
                                    type="file" 
                                    accept=".zip" 
                                    onChange={(e) => setSelectedFile(e.target.files[0])} 
                                    style={{ display: 'none' }} 
                                />
                            </label>
                        </div>

                        <button 
                            onClick={handleRestore}
                            disabled={!selectedFile}
                            style={{ 
                                ...btnStyles.save, width: '100%', padding: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontSize: '1rem',
                                backgroundColor: selectedFile ? '#10b981' : '#cbd5e1', cursor: selectedFile ? 'pointer' : 'not-allowed'
                            }}
                        >
                            <RiUploadCloud2Line size={20} /> เริ่มการนำเข้าข้อมูล
                        </button>
                    </div>

                </div>

                {/* ประวัติการทำงาน (Logs) */}
                <div style={pageStyles.card}>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#1e293b', borderBottom: '1px solid #e2e8f0', paddingBottom: '15px' }}>
                        <RiHistoryLine size={22} color="#64748b" /> ประวัติการทำงานล่าสุด (System Logs)
                    </h3>
                    
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#f8fafc', color: '#475569', textAlign: 'left' }}>
                                    <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0' }}>วัน-เวลา</th>
                                    <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0' }}>ประเภท</th>
                                    <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0' }}>ผู้ดำเนินการ</th>
                                    <th style={{ padding: '12px', borderBottom: '2px solid #e2e8f0' }}>ชื่อไฟล์</th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.length > 0 ? logs.map((log, index) => (
                                    <tr key={index} style={{ borderBottom: '1px solid #e2e8f0', ':hover': { backgroundColor: '#f1f5f9' } }}>
                                        <td style={{ padding: '12px', color: '#334155' }}>{log.date}</td>
                                        <td style={{ padding: '12px' }}>
                                            <span style={{ 
                                                padding: '4px 10px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 'bold',
                                                backgroundColor: log.type === 'backup' ? '#e0f2fe' : '#dcfce3',
                                                color: log.type === 'backup' ? '#0369a1' : '#166534'
                                            }}>
                                                {log.type === 'backup' ? 'Export (Backup)' : 'Import (Migrate)'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px', color: '#334155' }}>{log.admin_name}</td>
                                        <td style={{ padding: '12px', color: '#64748b', fontSize: '0.85rem', wordBreak: 'break-all' }}>{log.file_name}</td>
                                    </tr>
                                )) : (
                                    <tr>
                                        <td colSpan="4" style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>
                                            ยังไม่มีประวัติการทำงาน
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