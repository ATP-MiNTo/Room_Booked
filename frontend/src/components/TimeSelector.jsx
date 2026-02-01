const TimeSelector = ({ startTime, endTime, allTimeSlots, onChangeStart, onChangeEnd }) => {

  // Helper แปลงเวลาโชว์ (10:00 -> 09:59)
  const getDisplayEndTime = (time) => {
    if (!time) return "";
    const [hourStr, minStr] = time.split(":");
    let hour = parseInt(hourStr);
    let min = parseInt(minStr);
    if (min === 0) { hour -= 1; min = 59; } 
    else if (min === 30) { min = 29; }
    return `${hour.toString().padStart(2, '0')}:${min}`;
  };

  const endTimeOptions = allTimeSlots.slice(allTimeSlots.indexOf(startTime) + 1);

  return (
    <div style={{ margin: '20px 0', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '12px', border: '1px solid #eee' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', color: '#333' }}>
          เลือกช่วงเวลาใช้งาน
        </label>
        
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>ตั้งแต่</span>
            <select value={startTime} onChange={(e) => onChangeStart(e.target.value)} style={selectStyle}>
              {allTimeSlots.slice(0, -1).map(time => (
                <option key={time} value={time}>{time}</option>
              ))}
            </select>
          </div>
          <div style={{ color: '#aaa', paddingTop: '15px' }}>➜</div>
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>ถึงเวลา</span>
            <select value={endTime} onChange={(e) => onChangeEnd(e.target.value)} style={selectStyle}>
              {endTimeOptions.map(time => (
                <option key={time} value={time}>
                   {getDisplayEndTime(time)}
                </option>
              ))}
            </select>
          </div>
        </div>
    </div>
  );
};

const selectStyle = { width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '16px' };

export default TimeSelector;