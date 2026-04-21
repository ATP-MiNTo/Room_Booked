import { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import { authFetch } from '../../utils/authFetch';
import Swal from 'sweetalert2';
import { 
  RiSearchLine, 
  RiUserStarLine,
  RiUserAddLine,
  RiDeleteBinLine,
  RiSave3Line,
  RiCloseLine,
  RiInformationFill
} from 'react-icons/ri';

export default function AdminManage() {
  const [admins, setAdmins] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  
  const [newAdmin, setNewAdmin] = useState({
    staff_id: '', first_name: '', last_name: '', department: '', position: '', username: '', password: '', priority: 3
  });

  useEffect(() => {
    fetchAdmins();
  }, []);

  const fetchAdmins = async () => {
    try {
      const response = await authFetch('/api/admins');
      const res = response.ok ? response : await fetch('/admins');
      if (res.ok) {
        const data = await res.json();
        setAdmins(data);
      }
    } catch (error) {
      console.error("Error fetching admins:", error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;

    setNewAdmin({
      ...newAdmin,
      [name]: name === "priority" ? Number(value) : value
    });
  };

  const handleAddAdmin = async (e) => {
    e.preventDefault();
    
    if (!newAdmin.staff_id || !newAdmin.first_name || !newAdmin.username || !newAdmin.password) {
        Swal.fire('ข้อมูลไม่ครบ', 'กรุณากรอก รหัสพนักงาน, ชื่อ, Username และ Password', 'warning');
        return;
    }

    try {
      const res = await authFetch('/api/admins', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          ...newAdmin,
          last_name: newAdmin.last_name || null,
          department: newAdmin.department || null,
          position: newAdmin.position || null,
          priority: Number(newAdmin.priority || 3)
        })
      });

      
      const data = await res.json();
      
      if (res.ok) {
        Swal.fire({ icon: 'success', title: 'เพิ่มแอดมินสำเร็จ', showConfirmButton: false, timer: 1500 });
        setIsAddModalOpen(false);
        setNewAdmin({ staff_id: '', first_name: '', last_name: '', department: '', position: '', username: '', password: '', priority: 3 });
        fetchAdmins();
      } else {
        let errorMsg = 'ไม่สามารถเพิ่มแอดมินได้';
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail
            .map(e => (typeof e === 'string' ? e : (e.msg || e.message || JSON.stringify(e))))
            .join(', ');
        } else if (data.detail && typeof data.detail === 'object') {
          errorMsg = data.detail.msg || data.detail.message || JSON.stringify(data.detail);
        }
        Swal.fire('ข้อผิดพลาด', String(errorMsg), 'error');
      }
    } catch (e) {
      Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
    }
  };

  const handleDelete = async (staffId, adminName) => {
    if (admins.length <= 1) {
        Swal.fire('ไม่อนุญาต', 'ระบบต้องมีผู้ดูแลระบบอย่างน้อย 1 คน', 'error');
        return;
    }

    const confirm = await Swal.fire({
      title: 'ยืนยันการลบบัญชี?',
      html: `คุณต้องการเพิกถอนสิทธิ์และลบบัญชีของ <b>${adminName}</b> ใช่หรือไม่?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonText: 'ยกเลิก',
      confirmButtonText: 'ใช่, ลบบัญชีเลย!'
    });

    if (confirm.isConfirmed) {
      try {
        const res = await authFetch(`/api/admins/${staffId}`, { method: 'DELETE' });
        if (res.ok) {
          Swal.fire({ icon: 'success', title: 'ลบข้อมูลสำเร็จ', showConfirmButton: false, timer: 1500 });
          fetchAdmins();
        } else {
          Swal.fire('ข้อผิดพลาด', 'ไม่สามารถลบข้อมูลได้', 'error');
        }
      } catch (e) {
        Swal.fire('ข้อผิดพลาด', 'ติดต่อเซิร์ฟเวอร์ไม่ได้', 'error');
      }
    }
  };

  const filteredAdmins = admins.filter(admin => 
    admin.staff_id.includes(searchTerm) || 
    admin.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    admin.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    admin.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AdminLayout>
      <div style={f.container}>
        
        <div style={f.headerArea}>
            <h2 style={f.title}>
              <RiUserStarLine color="#722ed1" /> จัดการผู้ดูแลระบบ (Admin)
            </h2>
            <button onClick={() => setIsAddModalOpen(true)} style={f.addBtn}>
                <RiUserAddLine size={18} /> เพิ่มผู้ดูแลระบบ
            </button>
        </div>

        <div style={f.filterContainer}>
            <div style={f.inputGroup}>
                <RiSearchLine color="#888" style={{marginLeft: '15px', position: 'absolute'}} size={18}/>
                <input 
                    type="text" 
                    placeholder="ค้นหารหัส, ชื่อ, หรือ Username..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={f.searchInput}
                />
            </div>
        </div>

        <div style={f.tableWrap}>
          <table style={f.table}>
            <thead>
              <tr>
                <th style={{...f.th, width: '15%'}}>รหัสพนักงาน</th>
                <th style={{...f.th, width: '25%'}}>ชื่อ - นามสกุล</th>
                <th style={{...f.th, width: '25%'}}>แผนก / ตำแหน่ง</th>
                <th style={{...f.th, width: '20%'}}>Username</th>
                <th style={{...f.th, textAlign: 'center', width: '15%'}}>จัดการ</th>
              </tr>
            </thead>
            <tbody>
              {filteredAdmins.map((admin) => (
                <tr key={admin.staff_id} style={f.tr}>
                  <td style={{...f.td, fontWeight: '700', color: '#722ed1'}}>{admin.staff_id}</td>
                  <td style={{...f.td, color: '#2c3e50', fontWeight: '700'}}>
                    {admin.first_name} {admin.last_name}
                  </td>
                  <td style={f.td}>
                    <div>{admin.department}</div>
                    <div style={{fontSize: '0.8rem', color: '#888'}}>{admin.position}</div>
                  </td>
                  <td style={f.td}>
                    <span style={{ backgroundColor: '#f0f2f5', padding: '4px 8px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', color: '#555', border: '1px solid #ddd' }}>
                        {admin.username}
                    </span>
                  </td>
                  <td style={{...f.td, textAlign: 'center'}}>
                    <button onClick={() => handleDelete(admin.staff_id, `${admin.first_name} ${admin.last_name}`)} style={f.iconBtnDanger} title="ลบผู้ดูแลระบบ">
                        <RiDeleteBinLine size={16}/> ลบบัญชี
                    </button>
                  </td>
                </tr>
              ))}
              {filteredAdmins.length === 0 && (
                <tr>
                  <td colSpan="5" style={{...f.td, textAlign: 'center', color: '#ccc', padding: '40px'}}>ไม่พบข้อมูลผู้ดูแลระบบ</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>

      {isAddModalOpen && (
        <div style={f.modalBackdrop} onClick={() => setIsAddModalOpen(false)}>
            <div style={f.modalContent} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '15px', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0, color: '#722ed1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <RiUserAddLine /> เพิ่มบัญชีผู้ดูแลระบบ
                    </h3>
                    <button style={f.closeModalBtn} onClick={() => setIsAddModalOpen(false)}><RiCloseLine size={24} /></button>
                </div>

                <form onSubmit={handleAddAdmin}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
                        <div>
                            <label style={f.label}>รหัสพนักงาน <span style={{color: 'red'}}>*</span></label>
                            <input type="text" name="staff_id" value={newAdmin.staff_id} onChange={handleInputChange} required style={f.formInput} placeholder="" />
                        </div>
                        <div>
                            <label style={f.label}>แผนก</label>
                            <input type="text" name="department" value={newAdmin.department} onChange={handleInputChange} style={f.formInput} placeholder="" />
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
                        <div>
                            <label style={f.label}>ชื่อ <span style={{color: 'red'}}>*</span></label>
                            <input type="text" name="first_name" value={newAdmin.first_name} onChange={handleInputChange} required style={f.formInput} />
                        </div>
                        <div>
                            <label style={f.label}>นามสกุล</label>
                            <input type="text" name="last_name" value={newAdmin.last_name} onChange={handleInputChange} style={f.formInput} />
                        </div>
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={f.label}>ตำแหน่ง</label>
                        <input type="text" name="position" value={newAdmin.position} onChange={handleInputChange} style={f.formInput} placeholder="เช่น เจ้าหน้าที่ดูแลห้องแล็บ" />
                    </div>

                    <div style={{ padding: '20px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px dashed #cbd5e1', marginBottom: '25px' }}>
                        <h4 style={{ margin: '0 0 15px 0', fontSize: '0.9rem', color: '#475569' }}>ข้อมูลสำหรับเข้าสู่ระบบ (Login Info)</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                            <div>
                                <label style={f.label}>Username <span style={{color: 'red'}}>*</span></label>
                                <input type="text" name="username" value={newAdmin.username} onChange={handleInputChange} required style={f.formInput} />
                            </div>
                            <div>
                                <label style={f.label}>Password <span style={{color: 'red'}}>*</span></label>
                                <input type="password" name="password" value={newAdmin.password} onChange={handleInputChange} required style={f.formInput} />
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                        <button type="button" onClick={() => setIsAddModalOpen(false)} style={f.cancelBtn}>ยกเลิก</button>
                        <button type="submit" style={f.submitBtn}><RiSave3Line size={18} /> บันทึกและสร้างบัญชี</button>
                    </div>
                </form>
            </div>
        </div>
      )}

    </AdminLayout>
  );
}

const f = {
  container: { background: 'white', padding: '30px', borderRadius: '15px', boxShadow: '0 4px 20px rgba(0,0,0,0.08)', maxWidth: '1100px', margin: '0 auto', paddingBottom: '60px' },
  headerArea: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #eee', paddingBottom: '15px', marginBottom: '25px' },
  title: { fontSize: '1.6rem', fontWeight: 'bold', color: '#2c3e50', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' },
  addBtn: { display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', backgroundColor: '#722ed1', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'background 0.2s', boxShadow: '0 4px 10px rgba(114,46,209,0.3)' },
  filterContainer: { marginBottom: '25px', backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '12px', border: '1px solid #eee' },
  inputGroup: { position: 'relative', display: 'flex', alignItems: 'center', width: '100%', maxWidth: '500px' },
  searchInput: { padding: '12px 15px 12px 45px', border: '1px solid #ddd', borderRadius: '8px', fontSize: '0.95rem', outline: 'none', width: '100%', transition: 'border 0.2s', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)' },
  tableWrap: { overflowX: 'auto', background: 'white', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  table: { width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' },
  th: { background: '#f9f0ff', textAlign: 'left', padding: '15px', borderBottom: '2px solid #e2e8f0', color: '#531dab', fontSize: '0.95rem', whiteSpace: 'nowrap' },
  tr: { borderBottom: '1px solid #f0f0f0', transition: 'background 0.2s' },
  td: { padding: '15px', verticalAlign: 'middle', color: '#555', fontSize: '0.95rem' },
  iconBtnDanger: { background: '#fff1f0', color: '#cf1322', border: '1px solid #ffa39e', borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '5px', fontWeight: 'bold', fontSize: '0.85rem', transition: 'background 0.2s' },
  modalBackdrop: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999, backdropFilter: 'blur(3px)' },
  modalContent: { position: 'relative', width: '100%', maxWidth: '650px', background: 'white', borderRadius: '16px', padding: '30px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' },
  closeModalBtn: { background: '#f8fafc', border: 'none', borderRadius: '50%', color: '#64748b', cursor: 'pointer', padding: '6px', display: 'flex', transition: 'background 0.2s' },
  label: { display: 'block', fontSize: '0.85rem', color: '#475569', marginBottom: '8px', fontWeight: 'bold' },
  formInput: { width: '100%', padding: '12px 15px', border: '1px solid #cbd5e1', borderRadius: '8px', outline: 'none', fontSize: '0.95rem', boxSizing: 'border-box', transition: 'border 0.2s', backgroundColor: '#f8fafc' },
  cancelBtn: { padding: '12px 25px', background: '#f1f5f9', border: '1px solid #cbd5e1', color: '#475569', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.95rem' },
  submitBtn: { padding: '12px 25px', background: '#722ed1', border: 'none', color: 'white', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '5px', boxShadow: '0 4px 12px rgba(114,46,209,0.3)', fontSize: '0.95rem' }
};