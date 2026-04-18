import React from 'react';
import DatePicker, { registerLocale } from 'react-datepicker';
import th from 'date-fns/locale/th';
import 'react-datepicker/dist/react-datepicker.css';
import { THAI_MONTHS_FULL } from '../../utils/dateUtils'; // นำเข้า THAI_MONTHS_FULL

registerLocale('th', th);

const inputStyle = {
  padding: '10px',
  border: '1px solid #ddd',
  borderRadius: '8px',
  width: '100%',
  boxSizing: 'border-box',
  cursor: 'pointer',
  background: 'white'
};

const ThaiDatePicker = ({ value, onChange, minDate }) => {
  const selectedDate = value ? new Date(value) : null;
  const minDateObj = minDate ? new Date(minDate) : null;

  const handleChange = (date) => {
      if (!date) {
          onChange('');
          return;
      }
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      onChange(`${yyyy}-${mm}-${dd}`); 
  };

  const CustomInput = React.forwardRef(({ value, onClick }, ref) => {
      let displayValue = value;
      if (value) {
          const [d, m, y] = value.split('/');
          displayValue = `${d}/${m}/${parseInt(y) + 543}`;
      }
      return (
          <input 
              style={inputStyle} 
              value={displayValue} 
              onClick={onClick} 
              ref={ref} 
              readOnly 
              placeholder="วว/ดด/ปปปป" 
          />
      );
  });

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 20 }, (_, i) => currentYear - 5 + i);

  return (
      <DatePicker
          selected={selectedDate}
          onChange={handleChange}
          locale="th"
          dateFormat="dd/MM/yyyy"
          minDate={minDateObj}
          customInput={<CustomInput />}
          renderCustomHeader={({
              date, changeYear, changeMonth, decreaseMonth, increaseMonth,
              prevMonthButtonDisabled, nextMonthButtonDisabled,
          }) => (
              <div style={{ margin: 10, display: "flex", justifyContent: "center", gap: '5px' }}>
                  <button type="button" onClick={decreaseMonth} disabled={prevMonthButtonDisabled} style={{cursor:'pointer', border:'none', background:'#eee', borderRadius:'4px', padding:'2px 8px'}}>{"<"}</button>
                  <select
                      value={date.getMonth()}
                      onChange={({ target: { value } }) => changeMonth(Number(value))}
                      style={{padding: '2px', borderRadius: '4px', border: '1px solid #ccc', outline: 'none'}}
                  >
                      {/* ใช้ THAI_MONTHS_FULL จาก dateUtils แทน */}
                      {THAI_MONTHS_FULL.map((option, index) => (
                          <option key={option} value={index}>{option}</option>
                      ))}
                  </select>
                  <select
                      value={date.getFullYear()}
                      onChange={({ target: { value } }) => changeYear(Number(value))}
                      style={{padding: '2px', borderRadius: '4px', border: '1px solid #ccc', outline: 'none'}}
                  >
                      {years.map((option) => (
                          <option key={option} value={option}>{option + 543}</option>
                      ))}
                  </select>
                  <button type="button" onClick={increaseMonth} disabled={nextMonthButtonDisabled} style={{cursor:'pointer', border:'none', background:'#eee', borderRadius:'4px', padding:'2px 8px'}}>{">"}</button>
              </div>
          )}
      />
  );
};

export default ThaiDatePicker;