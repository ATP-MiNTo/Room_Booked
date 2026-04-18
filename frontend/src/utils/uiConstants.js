export const COLORS_MAJOR = ['#1677ff','#52c41a','#faad14','#f5222d','#722ed1','#13c2c2'];
export const COLORS_YEAR  = ['#3b82f6','#8b5cf6','#ec4899','#f43f5e','#eab308','#64748b','#ef4444'];

export const STATUS_COLORS = {
  normal: '#52c41a',
  noshow: '#faad14',
  walkin: '#ff4d4f',
  broken: '#8c8c8c',
};

export const MAJOR_OPTIONS = [
  { value: '', label: '-- ทุกสาขาวิชา --' },
  { value: 'วิศวกรรมไฟฟ้า', label: 'วิศวกรรมไฟฟ้า' },
  { value: 'วิศวกรรมปัญญาประดิษฐ์และวิทยาการข้อมูล', label: 'วิศวกรรมปัญญาประดิษฐ์และวิทยาการข้อมูล' },
  { value: 'วิศวกรรมคอมพิวเตอร์และหุ่นยนต์', label: 'วิศวกรรมคอมพิวเตอร์และหุ่นยนต์' },
  { value: 'วิศวกรรมมัลติมีเดียและเอ็นเตอร์เทนเมนต์', label: 'วิศวกรรมมัลติมีเดียและเอ็นเตอร์เทนเมนต์' },
];

export const YEAR_OPTIONS = [
  { value: '', label: '-- ทุกชั้นปี --' },
  { value: 'ปี 1', label: 'ชั้นปี 1' },
  { value: 'ปี 2', label: 'ชั้นปี 2' },
  { value: 'ปี 3', label: 'ชั้นปี 3' },
  { value: 'ปี 4', label: 'ชั้นปี 4' },
  { value: 'ปี 5++', label: 'ชั้นปี 5++' },
  { value: 'รีไทร์ (เกิน 10 ปี)', label: 'รีไทร์ (เกิน 10 ปี)' },
  { value: 'Error (เลขแปลกๆ)', label: 'Error (รหัสไม่ถูกต้อง)' },
];

export const btnStyles = {
  action: (bg, color, border) => ({
    display: 'flex', alignItems: 'center', gap: '6px',
    padding: '8px 16px',
    backgroundColor: bg, color,
    border: `1px solid ${border}`,
    borderRadius: '30px',
    cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem',
  }),
  export: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 16px',
    backgroundColor: '#f6ffed', color: '#52c41a',
    border: '1px solid #b7eb8f',
    borderRadius: '30px',
    cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem',
  },
  refresh: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 16px',
    backgroundColor: '#f0f9ff', color: '#1677ff',
    border: '1px solid #91caff',
    borderRadius: '30px',
    cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem',
  },
  mock: (active) => ({
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 16px',
    backgroundColor: active ? '#fdf2f8' : '#f1f5f9',
    color: active ? '#db2777' : '#64748b',
    border: `1px solid ${active ? '#fbcfe8' : '#cbd5e1'}`,
    borderRadius: '30px',
    cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem',
  }),
};

export const tableStyles = {
  wrap: { overflowX: 'auto', background: 'white', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#f8f9fa', textAlign: 'left', padding: '13px 15px', borderBottom: '2px solid #eee', color: '#2c3e50', fontSize: '0.9rem', whiteSpace: 'nowrap', userSelect: 'none' },
  thContent: { display: 'flex', alignItems: 'center' },
  td: { padding: '13px 15px', borderBottom: '1px solid #f0f0f0', color: '#555', verticalAlign: 'middle', fontSize: '0.9rem' },
};

export const pageStyles = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '15px' },
  title: { fontSize: '1.6rem', fontWeight: '700', color: '#2c3e50', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' },
  card: { background: 'white', padding: '25px', borderRadius: '15px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', border: '1px solid #f1f5f9' },
  pagination: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', padding: '10px 15px', background: 'white', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  pageBtn: { display: 'flex', alignItems: 'center', gap: '5px', padding: '8px 12px', backgroundColor: '#f0f2f5', border: 'none', borderRadius: '6px', cursor: 'pointer', color: '#2c3e50', fontWeight: '700', fontSize: '0.9rem' },
  badge: { padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' },
  imageThumbnail: { width: '45px', height: '45px', borderRadius: '6px', overflow: 'hidden', cursor: 'pointer', position: 'relative', border: '1px solid #eee', backgroundColor: '#fafafa', margin: '0 auto' },
  imageOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', opacity: 0, transition: 'opacity 0.2s' },
  modalBackdrop: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.65)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999, backdropFilter: 'blur(3px)' },
  modalContent: { position: 'relative', maxWidth: '95vw', maxHeight: '90vh', background: 'white', borderRadius: '12px', boxShadow: '0 10px 30px rgba(0,0,0,0.2)' },
  closeModalBtn: { position: 'absolute', top: '15px', right: '15px', background: '#f5f5f5', border: 'none', borderRadius: '50%', color: '#555', cursor: 'pointer', padding: '5px', display: 'flex', zIndex: 10 },
  enlargedImage: { maxWidth: '100%', maxHeight: 'calc(90vh - 10px)', objectFit: 'contain', borderRadius: '8px', display: 'block', backgroundColor: 'white', padding: '10px' },
};