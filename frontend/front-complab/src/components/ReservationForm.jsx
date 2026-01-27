import { useState } from 'react';

const ReservationForm = ({ selectedSeat, startTime, displayEndTime, onConfirm }) => {
  
  // ข้อมูลคณะและสาขา
  const FACULTY_DATA = {
    "คณะวิศวกรรมศาสตร์": [
      "วิศวกรรมไฟฟ้า",
      "วิศวกรรมปัญญาประดิษฐ์และวิทยาการข้อมูล",
      "วิศวกรรมคอมพิวเตอร์และหุ่นยนต์",
      "วิศวกรรมมัลติมีเดียและเอ็นเตอร์เทนเมนต์"
    ],
    "คณะเทคโนโลยีสารสนเทศและนวัตกรรม": [
      "วิทยาการคอมพิวเตอร์",
      "เทคโนโลยีสารสนเทศ",
      "เกมและสื่อเชิงโต้ตอบ",
      "วิทยาการคอมพิวเตอร์ มุ่งเน้นวิทยาการข้อมูลและความมั่นคงปลอดภัยไซเบอร์"
    ]
  };

  const [formData, setFormData] = useState({
    studentId: '', name: '', faculty: '', major: '', year: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      // ถ้าเปลี่ยนคณะ ให้ล้างค่าสาขาทิ้ง
      if (name === 'faculty') {
        return { ...prev, [name]: value, major: '' };
      }
      return { ...prev, [name]: value };
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm(formData);
  };

  return (
    <div style={{ flex: 1, animation: 'fadeIn 0.4s' }}>
      <div style={{ backgroundColor: '#e8f5e9', padding: '15px', borderRadius: '10px', marginBottom: '20px', textAlign: 'center', border: '1px solid #c8e6c9' }}>
        <div style={{ fontSize: '0.9rem', color: '#666' }}>กำลังจองที่นั่ง</div>
        <span style={{ fontSize: '3rem', fontWeight: 'bold', display: 'block', color: '#2e7d32', lineHeight: '1' }}>{selectedSeat}</span>
        <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#2e7d32', marginTop: '5px' }}>{startTime} - {displayEndTime} น.</div>
      </div>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label style={labelStyle}>รหัสนักศึกษา</label>
          <input type="text" name="studentId" required value={formData.studentId} onChange={handleChange} placeholder="16XXXXXXXX" style={inputStyle} />
        </div>
        <div>
          <label style={labelStyle}>ชื่อ-นามสกุล</label>
          <input type="text" name="name" required value={formData.name} onChange={handleChange} placeholder="ชื่อจริง นามสกุล" style={inputStyle} />
        </div>

        {/* Dropdown คณะ */}
        <div>
            <label style={labelStyle}>คณะ</label>
            <select name="faculty" value={formData.faculty} onChange={handleChange} required style={{ ...inputStyle, backgroundColor: 'white' }}>
              <option value="">เลือกคณะ</option>
              {Object.keys(FACULTY_DATA).map(facultyName => (
                <option key={facultyName} value={facultyName}>{facultyName}</option>
              ))}
            </select>
        </div>

        {/* Dropdown สาขา (Dependent) */}
        <div>
            <label style={labelStyle}>สาขา</label>
            <select 
              name="major" 
              value={formData.major} 
              onChange={handleChange} 
              required
              disabled={!formData.faculty} 
              style={{ ...inputStyle, backgroundColor: formData.faculty ? 'white' : '#f5f5f5', cursor: formData.faculty ? 'pointer' : 'not-allowed' }}
            >
              <option value="">{formData.faculty ? "เลือกสาขา" : "กรุณาเลือกคณะก่อน"}</option>
              {formData.faculty && FACULTY_DATA[formData.faculty].map(majorName => (
                <option key={majorName} value={majorName}>{majorName}</option>
              ))}
            </select>
        </div>

        <div>
          <label style={labelStyle}>ชั้นปี</label>
          <select name="year" value={formData.year} onChange={handleChange} required style={{ ...inputStyle, backgroundColor: 'white' }}>
              <option value="">เลือกชั้นปี</option>
              <option value="1">ปี 1</option>
              <option value="2">ปี 2</option>
              <option value="3">ปี 3</option>
              <option value="4+">ปี 4 ขึ้นไป</option>
          </select>
        </div>

        <button type="submit" style={buttonStyle}>ยืนยันการจอง</button>
      </form>
    </div>
  );
};

const labelStyle = { fontWeight: 'bold', color: '#555', fontSize: '0.9rem' };
const inputStyle = { width: '100%', padding: '10px', marginTop: '5px', borderRadius: '6px', border: '1px solid #ccc' };
const buttonStyle = { marginTop: '10px', padding: '15px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '8px', fontSize: '16px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' };

export default ReservationForm;