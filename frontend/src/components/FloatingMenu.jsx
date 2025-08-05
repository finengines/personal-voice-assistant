import React from 'react';
import { FiServer, FiSliders } from 'react-icons/fi';
import './FloatingMenu.css';

const FloatingMenu = ({ onOpenMcp, onOpenPresets }) => (
  <div className="floating-menu">
    <button className="float-btn" onClick={onOpenMcp} title="MCP Servers"><FiServer size={22}/></button>
    <button className="float-btn" onClick={onOpenPresets} title="Agent Presets"><FiSliders size={22}/></button>
  </div>
);
export default FloatingMenu; 