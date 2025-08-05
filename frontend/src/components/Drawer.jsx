import React from 'react';
import './Drawer.css';
import { FiX } from 'react-icons/fi';

const Drawer = ({ show, onClose, children }) => {
  if (!show) return null;
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={e=>e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose}><FiX size={24}/></button>
        <div className="drawer-inner">{children}</div>
      </div>
    </div>
  );
};
export default Drawer; 