export const THAI_MONTHS_SHORT = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
export const THAI_MONTHS_FULL  = ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'];
export const THAI_DAYS_SHORT   = ['อา','จ','อ','พ','พฤ','ศ','ส'];
export const THAI_DAYS_FULL    = ['วันอาทิตย์', 'วันจันทร์', 'วันอังคาร', 'วันพุธ', 'วันพฤหัสบดี', 'วันศุกร์', 'วันเสาร์'];
export const DAY_NAMES_EN      = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

export const BOOKING_TIME_SLOTS = [
  "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", 
  "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", 
  "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00"
];

export const pad = (n) => String(n).padStart(2, '0');

export const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;

export const formatThaiDate = (dateString) => {
  if (!dateString || dateString === '-') return '-';
  try {
    const parts = dateString.split(' ')[0].split('-');
    if (parts.length !== 3) return dateString;
    const [y, m, d] = parts;
    const thaiYear = parseInt(y) < 2400 ? parseInt(y) + 543 : parseInt(y);
    return `${parseInt(d)} ${THAI_MONTHS_SHORT[parseInt(m)-1]} ${thaiYear}`;
  } catch {
    return dateString;
  }
};

export const getISOWeek = (d) => {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return { year: date.getUTCFullYear(), week: Math.ceil((((date - yearStart) / 86400000) + 1) / 7) };
};

export const getWeekMonday = (year, week) => {
  const simple = new Date(year, 0, 1 + (week - 1) * 7);
  const dow = simple.getDay();
  const mon = new Date(simple);
  mon.setDate(simple.getDate() - (dow <= 4 ? dow - 1 : dow - 8));
  return mon;
};

export const getWeekRangeLabel = (year, week) => {
  const mon = getWeekMonday(year, week);
  const sun = new Date(mon);
  sun.setDate(mon.getDate() + 6);
  return `${mon.getDate()} ${THAI_MONTHS_SHORT[mon.getMonth()]} – ${sun.getDate()} ${THAI_MONTHS_SHORT[sun.getMonth()]} ${sun.getFullYear()+543}`;
};

export const generateTimeOptions = (startHour = 8, endHour = 21, intervalMinutes = 30) => {
  const opts = [];
  for (let i = startHour; i <= endHour; i++) {
    opts.push(`${pad(i)}:00`);
    if (i !== endHour && intervalMinutes === 30) {
      opts.push(`${pad(i)}:30`);
    }
  }
  return opts;
};

export const escapeCSV = (val) => `"${String(val ?? '').replace(/"/g, '""')}"`;

export const downloadCSV = (rows, filename) => {
  const blob = new Blob(['\ufeff' + rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
};