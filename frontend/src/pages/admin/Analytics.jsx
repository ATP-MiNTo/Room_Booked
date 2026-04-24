import React, { useState, useEffect, useCallback, useMemo } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import {
  RiBarChartBoxLine, RiUserFollowLine, RiUserUnfollowLine,
  RiUserForbidLine, RiToolsFill, RiArrowUpLine, RiArrowDownLine, RiCalendar2Line,
  RiAlertFill, RiComputerLine, RiDownloadLine, RiRefreshLine,
  RiPieChartLine, RiTimerLine, RiGroupLine,
  RiArrowLeftLine, RiArrowRightLine
} from 'react-icons/ri';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import {
  pad, fmtDate, getISOWeek, getWeekMonday, getWeekRangeLabel,
  THAI_MONTHS_SHORT, THAI_MONTHS_FULL, THAI_DAYS_SHORT,
  escapeCSV, downloadCSV, formatThaiDate
} from '../../utils/dateUtils';
import { COLORS_MAJOR, COLORS_YEAR, STATUS_COLORS, MAJOR_OPTIONS, YEAR_OPTIONS, btnStyles, pageStyles } from '../../utils/uiConstants';

function NavBtn({ onClick, disabled, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? '#f1f5f9' : 'white',
        border: '1px solid #e2e8f0', borderRadius: '8px',
        padding: '6px 10px', cursor: disabled ? 'default' : 'pointer',
        color: disabled ? '#cbd5e1' : '#1677ff',
        display: 'flex', alignItems: 'center', transition: 'all 0.15s', lineHeight: 1,
      }}
    >
      {children}
    </button>
  );
}

const selStyles = {
  wrap: { display: 'flex', alignItems: 'center', gap: '8px' },
  label: { position: 'relative', display: 'flex', alignItems: 'center' },
  nativeInput: { opacity: 0, position: 'absolute', inset: 0, width: '100%', height: '100%', cursor: 'pointer', border: 'none', background: 'transparent', zIndex: 2 },
  labelText: { display: 'block', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '7px 14px', fontWeight: '600', color: '#1e293b', fontSize: '0.9rem', minWidth: '180px', textAlign: 'center', cursor: 'pointer', pointerEvents: 'none' },
};

function DateRangeSelector({ mode, value, onChange }) {
  const now = new Date();

  if (mode === 'today') {
    const handleChange = (delta) => {
      const d = new Date(value);
      d.setDate(d.getDate() + delta);
      onChange(fmtDate(d));
    };
    const label = new Date(value).toLocaleDateString('th-TH', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    return (
      <div style={selStyles.wrap}>
        <NavBtn onClick={() => handleChange(-1)}><RiArrowLeftLine /></NavBtn>
        <div style={selStyles.label}>
          <input type="date" value={value} onChange={e => onChange(e.target.value)} style={selStyles.nativeInput} />
          <span style={selStyles.labelText}>{label}</span>
        </div>
        <NavBtn onClick={() => handleChange(1)} disabled={value === fmtDate(now)}><RiArrowRightLine /></NavBtn>
      </div>
    );
  }

  if (mode === 'week') {
    const { year, week } = value;
    const handleChange = (delta) => {
      const mon = getWeekMonday(year, week);
      mon.setDate(mon.getDate() + delta * 7);
      onChange(getISOWeek(mon));
    };
    const curIW = getISOWeek(now);
    return (
      <div style={selStyles.wrap}>
        <NavBtn onClick={() => handleChange(-1)}><RiArrowLeftLine /></NavBtn>
        <div style={selStyles.label}>
          <input
            type="week" value={`${year}-W${pad(week)}`}
            onChange={e => { const [y, w] = e.target.value.split('-W'); onChange({ year: parseInt(y), week: parseInt(w) }); }}
            style={selStyles.nativeInput}
          />
          <span style={selStyles.labelText}>{getWeekRangeLabel(year, week)}</span>
        </div>
        <NavBtn onClick={() => handleChange(1)} disabled={year === curIW.year && week === curIW.week}><RiArrowRightLine /></NavBtn>
      </div>
    );
  }

  if (mode === 'month') {
    const { year, month } = value;
    const handleChange = (delta) => {
      let m = month + delta, y = year;
      if (m > 12) { m = 1; y++; }
      if (m < 1)  { m = 12; y--; }
      onChange({ year: y, month: m });
    };
    return (
      <div style={selStyles.wrap}>
        <NavBtn onClick={() => handleChange(-1)}><RiArrowLeftLine /></NavBtn>
        <div style={selStyles.label}>
          <input
            type="month" value={`${year}-${pad(month)}`}
            onChange={e => { const [y, m] = e.target.value.split('-'); onChange({ year: parseInt(y), month: parseInt(m) }); }}
            style={selStyles.nativeInput}
          />
          <span style={selStyles.labelText}>{THAI_MONTHS_FULL[month - 1]} {year + 543}</span>
        </div>
        <NavBtn onClick={() => handleChange(1)} disabled={year === now.getFullYear() && month === now.getMonth() + 1}><RiArrowRightLine /></NavBtn>
      </div>
    );
  }

  if (mode === 'year') {
    const handleChange = (delta) => onChange(value + delta);
    return (
      <div style={selStyles.wrap}>
        <NavBtn onClick={() => handleChange(-1)}><RiArrowLeftLine /></NavBtn>
        <div style={selStyles.label}>
          <select value={value} onChange={e => onChange(parseInt(e.target.value))} style={{ ...selStyles.nativeInput, cursor: 'pointer' }}>
            {Array.from({ length: 6 }, (_, i) => now.getFullYear() - i).map(y => (
              <option key={y} value={y}>{y + 543} ({y})</option>
            ))}
          </select>
          <span style={selStyles.labelText}>ปี {value + 543}</span>
        </div>
        <NavBtn onClick={() => handleChange(1)} disabled={value === now.getFullYear()}><RiArrowRightLine /></NavBtn>
      </div>
    );
  }

  return null;
}

export default function Analytics() {
  const now   = new Date();
  const curIW = getISOWeek(now);

  const [timeFilter, setTimeFilter] = useState('week');
  const [selDay,     setSelDay]     = useState(fmtDate(now));
  const [selWeek,    setSelWeek]    = useState({ year: curIW.year, week: curIW.week });
  const [selMonth,   setSelMonth]   = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [selYear,    setSelYear]    = useState(now.getFullYear());

  const [isLoading,      setIsLoading]      = useState(true);
  const [error,          setError]          = useState(null);

  const [kpiData,         setKpiData]         = useState({});
  const [trendData,       setTrendData]       = useState([]);
  const [allSeatsUsage,   setAllSeatsUsage]   = useState([]);
  const [peakHours,       setPeakHours]       = useState([]);
  const [brokenSeatsList, setBrokenSeatsList] = useState([]);
  const [byMajor,         setByMajor]         = useState([]);
  const [byYear,          setByYear]          = useState([]);

  const filterLabel = { today: 'รายวัน', week: 'รายสัปดาห์', month: 'รายเดือน', year: 'รายปี' };

  const buildQuery = (base, params) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v != null && v !== '') q.set(k, v); });
    return `${base}?${q.toString()}`;
  };

  const formatTrendLabel = (dateStr) => {
    const d = new Date(dateStr);
    if (timeFilter === 'today')  return `${String(d.getHours()).padStart(2,'0')}:00`;
    if (timeFilter === 'week')   return `${THAI_DAYS_SHORT[d.getDay()]} ${d.getDate()}`;
    if (timeFilter === 'month')  return `${d.getDate()} ${THAI_MONTHS_SHORT[d.getMonth()]}`;
    return THAI_MONTHS_SHORT[d.getMonth()];
  };

  const getApiParams = useCallback(() => {
    if (timeFilter === 'today') {
      return { start: selDay, end: selDay };
    }
    if (timeFilter === 'week') {
      const { year, week } = selWeek;
      const mon = getWeekMonday(year, week);
      const sun = new Date(mon);
      sun.setDate(mon.getDate() + 6);
      return { start: fmtDate(mon), end: fmtDate(sun) };
    }
    if (timeFilter === 'month') {
      return { month: `${selMonth.year}-${pad(selMonth.month)}` };
    }
    return { year: selYear };
  }, [timeFilter, selDay, selWeek, selMonth, selYear]);

  const getKpiPeriodParams = useCallback(() => {
    if (timeFilter === 'today') {
      return { period: 'today', ref_date: selDay };
    }
    if (timeFilter === 'week') {
      return { period: 'week', ref_week: `${selWeek.year}-W${pad(selWeek.week)}` };
    }
    if (timeFilter === 'month') {
      return { period: 'month', ref_month: `${selMonth.year}-${pad(selMonth.month)}` };
    }
    return { period: 'year', ref_year: selYear };
  }, [timeFilter, selDay, selWeek, selMonth, selYear]);

  const fetchAllData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const rangeParams = getApiParams();
      const kpiParams   = getKpiPeriodParams();

      const [resKpi, resTrend, resSeats, resPeak, resMajor, resYearLv] = await Promise.all([
        fetch(buildQuery('/api/analytics/kpi',         kpiParams)),
        fetch(buildQuery('/api/bookings/range',        rangeParams)),
        fetch(buildQuery('/api/analytics/seat-usage',  rangeParams)),
        fetch(buildQuery('/api/analytics/peak-hours',  rangeParams)),
        fetch(buildQuery('/api/analytics/by-major',    rangeParams)),
        fetch(buildQuery('/api/analytics/by-year',     rangeParams)),
      ]);

      if (resKpi.ok) {
        const kpi = await resKpi.json();
        setKpiData(kpi);
        setBrokenSeatsList(kpi.brokenList || []);
      }

      if (resTrend.ok) {
        const raw = await resTrend.json();
        
        if (timeFilter === 'year') {
          // จัดกลุ่มยอดตามเดือน 1-12
          const monthly = Array(12).fill(0);
          raw.forEach(r => { monthly[new Date(r.date).getMonth()] += r.total; });
          setTrendData(THAI_MONTHS_SHORT.map((m, i) => ({ name: m, 'จองและนั่ง': monthly[i], 'จองแต่ไม่นั่ง': 0, 'ไม่จองแต่นั่ง': 0 })));
          
        } else if (timeFilter === 'month') {
          // สร้างวันที่ 1 ถึง 30/31 สำหรับแกน X ของรายเดือน
          const daysInMonth = new Date(selMonth.year, selMonth.month, 0).getDate();
          const daily = Array(daysInMonth).fill(0);
          
          raw.forEach(r => {
             const dayIndex = parseInt(r.day || new Date(r.date).getDate()) - 1;
             if (dayIndex >= 0 && dayIndex < daysInMonth) {
                 daily[dayIndex] += r.total;
             }
          });
          
          const monthData = Array.from({ length: daysInMonth }, (_, i) => ({
             name: `${i + 1}`,
             'จองและนั่ง': daily[i],
             'จองแต่ไม่นั่ง': 0,
             'ไม่จองแต่นั่ง': 0
          }));
          setTrendData(monthData);

        } else {
          // สำหรับรายวัน หรือ รายสัปดาห์
          setTrendData(raw.map(r => ({ 
             name: r.day ? `${r.day}` : formatTrendLabel(r.date), 
             'จองและนั่ง': r.total, 
             'จองแต่ไม่นั่ง': 0, 
             'ไม่จองแต่นั่ง': 0 
          })));
        }
      } else { setTrendData([]); }

      if (resSeats.ok)  setAllSeatsUsage(await resSeats.json()); else setAllSeatsUsage([]);
      if (resPeak.ok)   setPeakHours(await resPeak.json());      else setPeakHours([]);
      if (resMajor.ok)  setByMajor(await resMajor.json());       else setByMajor([]);
      if (resYearLv.ok) {
        const yd = await resYearLv.json();
        setByYear(yd.filter(i => i.year !== 'Error' && i.year !== 'รีไทร์'));
      } else { setByYear([]); }

    } catch (e) {
      console.error(e);
      setError('ไม่สามารถโหลดข้อมูลได้ กรุณาตรวจสอบการเชื่อมต่อฐานข้อมูล');
    } finally {
      setIsLoading(false);
    }
  }, [timeFilter, getApiParams, getKpiPeriodParams, selMonth.year, selMonth.month]);

  useEffect(() => { fetchAllData(); }, [fetchAllData]);

  const exportCSV = () => {
    const rows = [];

    // Section 1: KPI Summary
    rows.push(['=== ภาพรวม KPI ==='].map(escapeCSV).join(','));
    rows.push(['ประเภท', 'จำนวน (ครั้ง)'].map(escapeCSV).join(','));
    rows.push(['จองและนั่ง',       kpiData.totalNormal  ?? 0].map(escapeCSV).join(','));
    rows.push(['จองแต่ไม่มา',      kpiData.totalNoShow  ?? 0].map(escapeCSV).join(','));
    rows.push(['ไม่จองแต่นั่ง',    kpiData.totalWalkin  ?? 0].map(escapeCSV).join(','));
    rows.push(['เครื่องขัดข้อง',   kpiData.broken       ?? 0].map(escapeCSV).join(','));
    rows.push(['']);

    // Section 2: Seat Usage
    if (allSeatsUsage.length) {
      const total = allSeatsUsage.reduce((s, x) => s + x.usage, 0);
      rows.push(['=== การใช้งานแต่ละเครื่อง ==='].map(escapeCSV).join(','));
      rows.push(['อันดับ', 'หมายเลขเครื่อง', 'จำนวนการใช้งาน (ครั้ง)'].map(escapeCSV).join(','));
      allSeatsUsage.forEach((seat, i) => {
        rows.push([i + 1, seat.name, seat.usage].map(escapeCSV).join(','));
      });
      rows.push(['', 'รวม', total].map(escapeCSV).join(','));
      rows.push(['']);
    }

    // Section 3: By Major
    if (byMajor.length) {
      rows.push(['=== สัดส่วนตามสาขา ==='].map(escapeCSV).join(','));
      rows.push(['สาขา', 'จำนวน (คน/ครั้ง)'].map(escapeCSV).join(','));
      byMajor.forEach(m => rows.push([m.major, m.total].map(escapeCSV).join(',')));
      rows.push(['']);
    }

    // Section 4: Peak Hours
    if (peakHours.length) {
      rows.push(['=== ช่วงเวลายอดนิยม (Peak Hours) ==='].map(escapeCSV).join(','));
      rows.push(['ช่วงเวลา', 'จำนวนผู้ใช้งาน'].map(escapeCSV).join(','));
      peakHours.forEach(h => rows.push([h.time, h.users].map(escapeCSV).join(',')));
      rows.push(['']);
    }

    downloadCSV(rows, `analytics-${timeFilter}-${fmtDate(new Date())}.csv`);
  };

  const renderPieTooltip = (value, name, props) => {
    const percent = props.payload.percent;
    return percent !== undefined ? [`${value} คน (${(percent*100).toFixed(0)}%)`, name] : [`${value} คน`, name];
  };

  const currentDateSelector = useMemo(() => {
    if (timeFilter === 'today') return { mode: 'today', value: selDay,   onChange: setSelDay };
    if (timeFilter === 'week')  return { mode: 'week',  value: selWeek,  onChange: setSelWeek };
    if (timeFilter === 'month') return { mode: 'month', value: selMonth, onChange: setSelMonth };
    return { mode: 'year', value: selYear, onChange: setSelYear };
  }, [timeFilter, selDay, selWeek, selMonth, selYear]);

  const StatCard = ({ title, value, icon, trend, trendCount, color, bgColor }) => {
    const isPos = (trendCount ?? 0) >= 0;
    const isBad = title.includes('ไม่');
    const tColor = isPos ? (isBad ? '#cf1322' : '#389e0d') : (isBad ? '#389e0d' : '#cf1322');
    return (
      <div style={{ background: 'white', padding: '20px', borderRadius: '15px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', flex: '1 1 140px', minWidth: 0, border: `1px solid ${bgColor}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 'bold' }}>{title}</div>
            <div style={{ fontSize: '2rem', fontWeight: '900', color: '#1e293b', marginTop: '5px' }}>{value ?? 0}</div>
          </div>
          <div style={{ background: bgColor, padding: '12px', borderRadius: '12px', color }}>{icon}</div>
        </div>
        {trend !== undefined && trendCount !== undefined && (value > 0 || trendCount !== 0) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '15px', fontSize: '0.85rem', fontWeight: 'bold', color: tColor }}>
            {isPos ? <RiArrowUpLine /> : <RiArrowDownLine />}
            <span>{isPos ? '+' : '-'}{Math.abs(trendCount)} คน ({Math.abs(trend)}%) เทียบช่วงก่อน</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <AdminLayout>
      <div style={{ padding: '10px', maxWidth: '1200px', margin: '0 auto', paddingBottom: '60px' }}>

        <div style={pageStyles.header}>
          <h2 style={pageStyles.title}>
            <RiBarChartBoxLine color="#1677ff" /> Analytics
          </h2>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button onClick={exportCSV}    style={btnStyles.export}><RiDownloadLine /> Export CSV</button>
            <button onClick={fetchAllData} style={btnStyles.refresh}><RiRefreshLine /> Refresh</button>
          </div>
        </div>

        <div style={{ background: 'white', borderRadius: '14px', padding: '12px 16px', marginBottom: '20px', boxShadow: '0 2px 10px rgba(0,0,0,0.06)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '10px', padding: '4px', alignSelf: 'flex-start' }}>
            {Object.entries(filterLabel).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTimeFilter(key)}
                style={timeFilter === key ? s.activeTab : s.inactiveTab}
              >
                {label}
              </button>
            ))}
          </div>
          <DateRangeSelector {...currentDateSelector} />
        </div>

        {error && (
          <div style={{ background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: '10px', padding: '15px 20px', marginBottom: '20px', color: '#cf1322', fontWeight: 'bold' }}>
            {error}
          </div>
        )}

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '100px 0', color: '#888', fontSize: '1.2rem', fontWeight: 'bold' }}>กำลังโหลดข้อมูล...</div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '30px' }}>
              <StatCard title="จองและนั่ง"    value={kpiData.totalNormal}  icon={<RiUserFollowLine size={24}/>}   trend={kpiData.trendNormal}  trendCount={kpiData.trendNormalCount}  color={STATUS_COLORS.normal} bgColor="#f6ffed"/>
              <StatCard title="จองแต่ไม่มานั่ง" value={kpiData.totalNoShow}  icon={<RiUserUnfollowLine size={24}/>} trend={kpiData.trendNoShow}  trendCount={kpiData.trendNoShowCount}  color={STATUS_COLORS.noshow} bgColor="#fffbe6"/>
              <StatCard title="ไม่จองแต่นั่ง" value={kpiData.totalWalkin}  icon={<RiUserForbidLine size={24}/>}  trend={kpiData.trendWalkin}  trendCount={kpiData.trendWalkinCount}  color={STATUS_COLORS.walkin} bgColor="#fff1f0"/>
              <StatCard title="เครื่องขัดข้อง"  value={kpiData.broken}       icon={<RiToolsFill size={24}/>}      color={STATUS_COLORS.broken} bgColor="#f1f5f9"/>
            </div>

            <div style={{ ...pageStyles.card, background: '#fff1f0', border: '1px solid #ffa39e', marginBottom: '30px' }}>
                <h3 style={{ ...s.cardTitle, color: '#cf1322' }}><RiAlertFill /> เครื่องที่แจ้งขัดข้อง ({kpiData.broken || 0})</h3>
                {brokenSeatsList.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
                    {brokenSeatsList.map((item, i) => (
                      <div key={i} style={{ background: 'white', padding: '10px 14px', borderRadius: '8px', borderLeft: '4px solid #cf1322', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 'bold', color: '#1e293b' }}>{item.seat_no}</div>
                          <div style={{ color: '#64748b', fontSize: '0.82rem', marginTop: '2px' }}>{item.note}</div>
                        </div>
                        <div style={{ fontSize: '0.78rem', color: '#94a3b8', flexShrink: 0 }}>{formatThaiDate(item.date)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffa39e', fontWeight: 'bold' }}>ไม่มีเครื่องขัดข้อง</div>
                )}
              </div>

            <div style={{ ...pageStyles.card, marginBottom: '30px' }}>
              <h3 style={styles.cardTitle}><RiCalendar2Line color="#64748b" /> แนวโน้มการใช้งาน
                <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'normal' }}>({filterLabel[timeFilter]})</span>
              </h3>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: '10px', border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }} />
                    <Legend wrapperStyle={{ paddingTop: '15px' }} />
                    <Line type="monotone" dataKey="จองและนั่ง"    stroke={STATUS_COLORS.normal} strokeWidth={3} activeDot={{ r: 7 }} dot={false} />
                    <Line type="monotone" dataKey="จองแต่ไม่นั่ง" stroke={STATUS_COLORS.noshow} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="ไม่จองแต่นั่ง" stroke={STATUS_COLORS.walkin} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <EmptyChart h={300} />}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>

              <div style={{ ...pageStyles.card, display: 'flex', flexDirection: 'column' }}>
                <h3 style={styles.cardTitle}><RiComputerLine color="#1677ff" /> สถิติการใช้งานที่นั่ง</h3>
                <div style={{ fontSize: '0.83rem', color: '#64748b', marginBottom: '12px' }}>เรียงจากมากไปน้อย</div>
                {allSeatsUsage.length > 0 ? (
                  <div style={{ overflowY: 'auto', maxHeight: '280px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ position: 'sticky', top: 0, background: 'white' }}>
                          <th style={styles.th}>อันดับ</th>
                          <th style={{ ...styles.th, textAlign: 'left' }}>เครื่อง</th>
                          <th style={styles.th}>จำนวนครั้ง</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allSeatsUsage.map((seat, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #f1f5f9', backgroundColor: i < 3 ? '#f0f5ff' : 'transparent' }}>
                            <td style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold', color: ['#d4b106','#a3a8b4','#b87241'][i] || '#94a3b8' }}>{i+1}</td>
                            <td style={{ padding: '10px', fontWeight: 'bold', color: '#1e293b' }}>
                              {seat.name}
                              {i < 3 && <span style={{ fontSize: '0.7rem', background: '#1677ff', color: 'white', padding: '2px 6px', borderRadius: '10px', marginLeft: '8px' }}>ฮิต</span>}
                            </td>
                            <td style={{ padding: '10px', textAlign: 'center', color: '#0958d9', fontWeight: 'bold' }}>{seat.usage}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <EmptyChart h={250} />}
              </div>

              <div style={{ ...pageStyles.card, display: 'flex', flexDirection: 'column' }}>
                <h3 style={styles.cardTitle}><RiGroupLine color="#ec4899" /> สัดส่วนแยกตามชั้นปี</h3>
                {byYear.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={byYear} dataKey="total" nameKey="year" cx="50%" cy="50%" outerRadius={75}>
                          {byYear.map((_, i) => <Cell key={i} fill={COLORS_YEAR[i % COLORS_YEAR.length]} />)}
                        </Pie>
                        <Tooltip formatter={renderPieTooltip} contentStyle={{ borderRadius: '8px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginTop: '10px' }}>
                      {byYear.map((m, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '0.85rem' }}>
                          <div style={{ width: '11px', height: '11px', borderRadius: '3px', background: COLORS_YEAR[i % COLORS_YEAR.length], flexShrink: 0 }} />
                          <span style={{ color: '#475569', flex: 1 }}>{m.year}</span>
                          <span style={{ fontWeight: 'bold', color: '#1e293b' }}>{m.total}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : <EmptyChart h={200} />}
              </div>

              <div style={{ ...pageStyles.card, display: 'flex', flexDirection: 'column' }}>
                <h3 style={styles.cardTitle}><RiTimerLine color="#f97316" /> Peak Hours</h3>
                {peakHours.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={peakHours} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px' }} />
                        <Bar dataKey="users" name="ผู้ใช้งาน" radius={[4,4,0,0]} barSize={35}>
                          {peakHours.map((e, i) => (
                            <Cell key={i} fill={e.users === Math.max(...peakHours.map(p=>p.users)) ? '#f97316' : '#8b5cf6'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '0.8rem', color: '#64748b' }}>สีส้ม = ช่วงที่หนาแน่นที่สุด</div>
                  </>
                ) : <EmptyChart h={200} />}
              </div>

              <div style={{ ...pageStyles.card, display: 'flex', flexDirection: 'column' }}>
                <h3 style={styles.cardTitle}><RiPieChartLine color="#722ed1" /> สัดส่วนแยกตามสาขา</h3>
                {byMajor.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={byMajor} dataKey="total" nameKey="major" cx="50%" cy="50%" outerRadius={75}>
                          {byMajor.map((_, i) => <Cell key={i} fill={COLORS_MAJOR[i % COLORS_MAJOR.length]} />)}
                        </Pie>
                        <Tooltip formatter={renderPieTooltip} contentStyle={{ borderRadius: '8px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '10px', maxHeight: '80px', overflowY: 'auto' }}>
                      {byMajor.map((m, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.83rem' }}>
                          <div style={{ width: '11px', height: '11px', borderRadius: '3px', background: COLORS_MAJOR[i % COLORS_MAJOR.length], flexShrink: 0 }} />
                          <span style={{ color: '#475569', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.major}</span>
                          <span style={{ fontWeight: 'bold', color: '#1e293b' }}>{m.total}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : <EmptyChart h={200} />}
              </div>

            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}

function EmptyChart({ h = 200 }) {
  return (
    <div style={{ height: `${h}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#cbd5e1', fontWeight: 'bold', fontSize: '0.95rem' }}>
      ยังไม่มีข้อมูลในช่วงเวลานี้
    </div>
  );
}

const styles = {
  cardTitle: { margin: '0 0 18px 0', color: '#1e293b', fontSize: '1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' },
  th: { padding: '10px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem', borderBottom: '2px solid #e2e8f0' },
};
const s = {
  activeTab:   { padding: '7px 16px', backgroundColor: 'white', color: '#1677ff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.85rem', boxShadow: '0 1px 4px rgba(0,0,0,0.1)' },
  inactiveTab: { padding: '7px 16px', backgroundColor: 'transparent', color: '#64748b', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.85rem' },
  cardTitle:   { margin: '0 0 12px 0', color: '#1e293b', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700' },
  select:      { padding: '9px 11px', border: '1px solid #ddd', borderRadius: '8px', fontSize: '0.9rem', background: 'white', cursor: 'pointer', flex: '1 1 220px', minWidth: '180px' },
  resetBtn:    { display: 'flex', alignItems: 'center', gap: '5px', padding: '9px 15px', background: '#f5f5f5', border: '1px solid #ddd', color: '#555', borderRadius: '8px', cursor: 'pointer', fontWeight: '700', fontSize: '0.9rem', whiteSpace: 'nowrap' },
};