import React from 'react';

const SeatGrid = ({ selectedArray, onToggle, forceAll, activeColor, disabledArray = [] }) => (
  <div style={{ background: '#fafafa', padding: '15px', borderRadius: '10px', border: '1px solid #eee' }}>
    <div style={{ background: '#cbd5e1', color: '#334155', textAlign: 'center', padding: '8px', borderRadius: '6px', marginBottom: '15px', fontWeight: 'bold', fontSize: '0.9rem', letterSpacing: '2px' }}>
      กระดาน (หน้าห้อง)
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 0.4fr 1fr 1fr 1fr', gap: '8px' }}>
      {Array.from({ length: 30 }, (_, i) => i + 1).map(num => {
        const on       = forceAll || selectedArray.includes(num);
        const disabled = disabledArray.includes(num);
        const col = ((num - 1) % 6) + 1;
        const gridColumn = col > 3 ? col + 1 : col; 
        return (
          <div key={num} onClick={() => !forceAll && !disabled && onToggle(num)}
            title={disabled ? 'เครื่องนี้แจ้งขัดข้องอยู่' : undefined}
            style={{
              gridColumn: gridColumn,
              padding: '10px 0', textAlign: 'center', borderRadius: '6px',
              fontWeight: '700', fontSize: '0.9rem',
              cursor: forceAll || disabled ? 'not-allowed' : 'pointer',
              userSelect: 'none',
              background: disabled ? '#d9d9d9' : on ? activeColor : 'white',
              color: disabled ? '#999' : on ? 'white' : '#64748b',
              border: disabled ? '1px solid #bfbfbf' : on ? `1px solid ${activeColor}` : '1px solid #cbd5e1',
              opacity: forceAll ? 0.6 : 1,
              transition: 'all 0.15s',
              boxShadow: on ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
            }}>
            {num}
          </div>
        );
      })}
    </div>
  </div>
);

export default SeatGrid;