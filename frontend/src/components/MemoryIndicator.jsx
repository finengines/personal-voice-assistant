import React, { useState, useEffect } from 'react';
import './MemoryIndicator.css';

const MemoryIndicator = ({ isVisible, type, message, duration = 3000 }) => {
  const [show, setShow] = useState(false);
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setShow(true);
      setAnimate(true);
      
      const timer = setTimeout(() => {
        setAnimate(false);
        setTimeout(() => setShow(false), 300); // Allow fade out animation
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [isVisible, duration]);

  if (!show) return null;

  const getIcon = () => {
    switch (type) {
      case 'memory-created':
        return '🧠';
      case 'memory-retrieved':
        return '💭';
      case 'memory-searching':
        return '🔍';
      default:
        return '💡';
    }
  };

  const getTypeClass = () => {
    switch (type) {
      case 'memory-created':
        return 'memory-created';
      case 'memory-retrieved':
        return 'memory-retrieved';
      case 'memory-searching':
        return 'memory-searching';
      default:
        return 'memory-default';
    }
  };

  return (
    <div className={`memory-indicator ${getTypeClass()} ${animate ? 'animate' : 'fade-out'}`}>
      <div className="memory-content">
        <span className="memory-icon">{getIcon()}</span>
        <span className="memory-message">{message}</span>
      </div>
      <div className="memory-pulse"></div>
    </div>
  );
};

export default MemoryIndicator; 