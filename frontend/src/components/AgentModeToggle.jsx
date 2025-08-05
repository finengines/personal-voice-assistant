import React from 'react';
import './AgentModeToggle.css';
import { FiZap, FiCpu } from 'react-icons/fi';

const AgentModeToggle = ({ 
  isEnhancedMode = false, 
  onModeChange, 
  disabled = false,
  className = ''
}) => {
  const handleToggle = () => {
    if (!disabled && onModeChange) {
      onModeChange(!isEnhancedMode);
    }
  };

  return (
    <div className={`agent-mode-toggle ${className} ${disabled ? 'disabled' : ''}`}>
      <div className="mode-toggle-container">
        <button 
          className={`mode-option ${!isEnhancedMode ? 'active' : ''}`}
          onClick={() => !disabled && onModeChange && onModeChange(false)}
          disabled={disabled}
          title="Fast Mode - Minimal latency, basic memory"
        >
          <FiZap size={14} />
          <span>Fast</span>
        </button>
        
        <button 
          className={`mode-option ${isEnhancedMode ? 'active' : ''}`}
          onClick={() => !disabled && onModeChange && onModeChange(true)}
          disabled={disabled}
          title="Enhanced Mode - Advanced memory and contextual understanding"
        >
          <FiCpu size={14} />
          <span>Enhanced</span>
        </button>
        
        <div 
          className="mode-slider"
          style={{
            transform: `translateX(${isEnhancedMode ? '100%' : '0%'})`
          }}
        />
      </div>
      
      <div className="mode-description">
        <span className="mode-label">
          {isEnhancedMode ? 'Enhanced Mode' : 'Fast Mode'}
        </span>
        <span className="mode-detail">
          {isEnhancedMode 
            ? 'Advanced memory & context' 
            : 'Minimal latency response'
          }
        </span>
      </div>
    </div>
  );
};

export default AgentModeToggle; 