import { useState } from 'react';
import { MAJOR_OPTIONS } from '../utils/uiConstants';

const ReservationForm = ({ selectedSeat, startTime, displayEndTime, onConfirm }) => {
  
  const [formData, setFormData] = useState({
    studentId: '', firstName: '', lastName: '', major: '', purpose: ''
  });

  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!/^1\d{9}$/.test(formData.studentId)) {
      e.studentId = 'รหัสนักศึกษาต้องเป็นตัวเลข 10 หลัก และขึ้นต้นด้วย 1';
    }
    if (!formData.firstName.trim()) e.firstName = 'กรุณากรอกชื่อ';
    if (!formData.lastName.trim()) e.lastName = 'กรุณากรอกนามสกุล';
    if (!formData.major) e.major = 'กรุณาเลือกสาขา';
    if (!formData.purpose.trim()) e.purpose = 'กรุณาระบุวัตถุประสงค์';
    return e;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: undefined }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length > 0) {
      setErrors(e2);
      return;
    }
    onConfirm({ ...formData, lastname: formData.lastName });
  };

  return (
    <div style={{ flex: 1, animation: 'fadeIn 0.4s' }}>
      <div style={{ backgroundColor: '#e8f5e9', padding: '15px', borderRadius: '10px', marginBottom: '20px', textAlign: 'center', border: '1px solid #c8e6c9' }}>
        <div style={{ fontSize: '0.9rem', color: '#666' }}>จองที่นั่ง</div>
        <span style={{ fontSize: '3rem', fontWeight: 'bold', display: 'block', color: '#2e7d32', lineHeight: '1' }}>{selectedSeat}</span>
        <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#2e7d32', marginTop: '5px' }}>{startTime} - {displayEndTime}</div>
      </div>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label style={labelStyle}>รหัสนักศึกษา</label>
          <input 
            type="text" 
            name="studentId" 
            value={formData.studentId} 
            onChange={handleChange} 
            placeholder="เช่น 165XXXXXXX" 
            maxLength={10}
            style={{ ...inputStyle, borderColor: errors.studentId ? '#f5222d' : '#ccc' }} 
          />
          {errors.studentId && <div style={errorStyle}>{errors.studentId}</div>}
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>ชื่อ</label>
            <input 
              type="text" name="firstName" value={formData.firstName} onChange={handleChange} 
              placeholder="ชื่อ" style={{ ...inputStyle, borderColor: errors.firstName ? '#f5222d' : '#ccc' }} 
            />
            {errors.firstName && <div style={errorStyle}>{errors.firstName}</div>}
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>นามสกุล</label>
            <input 
              type="text" name="lastName" value={formData.lastName} onChange={handleChange} 
              placeholder="นามสกุล" style={{ ...inputStyle, borderColor: errors.lastName ? '#f5222d' : '#ccc' }} 
            />
            {errors.lastName && <div style={errorStyle}>{errors.lastName}</div>}
          </div>
        </div>

        <div>
          <label style={labelStyle}>สาขา</label>
          <select 
            name="major" value={formData.major} onChange={handleChange} 
            style={{ ...inputStyle, backgroundColor: 'white', borderColor: errors.major ? '#f5222d' : '#ccc' }}
          >
            {MAJOR_OPTIONS.map((m, i) => (
              <option key={i} value={m.value}>{m.label}</option>
            ))}
          </select>
          {errors.major && <div style={errorStyle}>{errors.major}</div>}
        </div>

        <div>
          <label style={labelStyle}>วัตถุประสงค์</label>
          <input 
            type="text" name="purpose" value={formData.purpose} onChange={handleChange} 
            placeholder="เช่น ทำการบ้านวิชา XX111, ทำโปรเจค" 
            style={{ ...inputStyle, borderColor: errors.purpose ? '#f5222d' : '#ccc' }} 
          />
          {errors.purpose && <div style={errorStyle}>{errors.purpose}</div>}
        </div>

        <button type="submit" style={buttonStyle}>ยืนยัน</button>
      </form>
    </div>
  );
};

const labelStyle = { fontWeight: 'bold', color: '#555', fontSize: '0.9rem' };
const inputStyle = { width: '100%', padding: '10px', marginTop: '5px', borderRadius: '6px', border: '1px solid #ccc', boxSizing: 'border-box' };
const errorStyle = { color: '#f5222d', fontSize: '0.8rem', marginTop: '4px' };
const buttonStyle = { marginTop: '10px', padding: '15px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', fontSize: '16px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' };

export default ReservationForm;