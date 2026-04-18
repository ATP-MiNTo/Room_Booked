import React from 'react';
import { RiArrowDownSFill } from 'react-icons/ri';

export const AccordionTrigger = ({ id, openPanel, setOpenPanel, icon, title, subtitle, accentColor }) => {
  const isOpen = openPanel === id;
  return (
    <div
      onClick={() => setOpenPanel(isOpen ? null : id)}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '15px 20px',
        background: isOpen ? '#fafafa' : 'white',
        borderRadius: isOpen ? '12px 12px 0 0' : '12px',
        borderLeft: `4px solid ${accentColor}`,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        cursor: 'pointer', userSelect: 'none',
        transition: 'border-radius 0.2s, background 0.2s',
      }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
        <span style={{ fontSize: '1.2rem', color: accentColor, display: 'flex' }}>{icon}</span>
        <div>
          <div style={{ fontWeight: '700', color: '#2c3e50', fontSize: '0.97rem' }}>{title}</div>
          <div style={{ fontSize: '0.78rem', color: '#aaa', marginTop: '1px' }}>{subtitle}</div>
        </div>
      </div>
      <span style={{ color: '#bbb', fontSize: '1.2rem', display: 'inline-block', transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.25s' }}>
        <RiArrowDownSFill />
      </span>
    </div>
  );
};

export const AccordionBody = ({ id, openPanel, children }) => {
  const isOpen = openPanel === id;
  return (
    <div style={{ maxHeight: isOpen ? '3000px' : '0', overflow: 'hidden', transition: 'max-height 0.35s ease', background: 'white', borderRadius: '0 0 12px 12px', boxShadow: isOpen ? '0 4px 12px rgba(0,0,0,0.06)' : 'none' }}>
      <div style={{ padding: '20px 20px 24px' }}>{children}</div>
    </div>
  );
};