import { useState } from 'react';

const ReservationForm = ({ selectedSeat, startTime, displayEndTime, onConfirm }) => {
  
  // ข้อมูลสาขา
  const MAJOR_DATA = [
    "วิศวกรรมไฟฟ้า",
    "วิศวกรรมปัญญาประดิษฐ์และวิทยาการข้อมูล",
    "วิศวกรรมคอมพิวเตอร์และหุ่นยนต์",
    "วิศวกรรมมัลติมีเดียและเอ็นเตอร์เทนเมนต์"
  ];

  const [formData, setFormData] = useState({
    studentId: '', firstName: '', lastname : '', major: '', purpose: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // ส่งข้อมูลกลับไปที่หน้าหลัก
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
          <input 
            type="text" 
            name="studentId" 
            required 
            value={formData.studentId} 
            onChange={handleChange} 
            placeholder="16XXXXXXXX" 
            style={inputStyle} 
          />
        </div>
        <div>
          <label style={labelStyle}>ชื่อ</label>
          <input 
            type="text" 
            name="firstName" 
            required 
            value={formData.firstName} 
            onChange={handleChange} 
            placeholder="ชื่อ" 
            style={inputStyle} 
          />
        </div>
        <div>
          <label style={labelStyle}>นามสกุล</label>
          <input 
            type="text" 
            name="lastname" 
            required 
            value={formData.lastname} 
            onChange={handleChange} 
            placeholder="นามสกุล" 
            style={inputStyle} 
          />
        </div>

        {/* Dropdown สาขา */}
        <div>
            <label style={labelStyle}>สาขา</label>
            <select 
              name="major" 
              value={formData.major} 
              onChange={handleChange} 
              required 
              style={{ ...inputStyle, backgroundColor: 'white' }}
            >
              <option value="">เลือกสาขา</option>
              {/* 3. แก้ไขการวนลูปให้ถูกต้อง */}
              {MAJOR_DATA.map((majorName, index) => (
                <option key={index} value={majorName}>{majorName}</option>
              ))}
            </select>
        </div>

        <div>
          <label style={labelStyle}>วัตถุประสงค์การใช้งาน</label>
          <input 
            type="text" 
            name="purpose" 
            required 
            value={formData.purpose} 
            onChange={handleChange} 
            placeholder="เช่น ทำการบ้านวิชา XX111, ทำโปรเจค, ศึกษาเพิ่มเติม" 
            style={inputStyle} 
          />
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