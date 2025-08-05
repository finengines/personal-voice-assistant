import React, { useState, useEffect, useMemo } from 'react';
import './ParticleIndicator.css';

/**
 * ParticleIndicator renders a short-lived radial particle burst with an
 * optional label. It is intended to sit absolutely inside a relatively
 * positioned parent (e.g. the connection-container). The animation is
 * CSS-driven so we avoid heavy JS timelines.
 */
const ParticleIndicator = ({ isVisible = false, label = '', duration = 2000 }) => {
  const [show, setShow] = useState(false);
  const [key, setKey] = useState(0); // rerender particles when re-shown

  // Pre-generate random transforms for particles so they look more organic
  const particles = useMemo(() => {
    // 12 small particles in a circle at random angles / distances
    return Array.from({ length: 12 }, (_, idx) => {
      const angle = (Math.PI * 2 * idx) / 12 + Math.random() * 0.2;
      const distance = 40 + Math.random() * 20; // px
      const dx = Math.cos(angle) * distance;
      const dy = Math.sin(angle) * distance;
      return { dx, dy, id: idx };
    });
  }, [key]);

  useEffect(() => {
    if (isVisible) {
      setShow(true);
      setKey((k) => k + 1); // regenerate particles for each burst
      const timer = setTimeout(() => setShow(false), duration);
      return () => clearTimeout(timer);
    }
  }, [isVisible, duration]);

  if (!show) return null;

  return (
    <div className="particle-indicator">
      {particles.map((p) => (
        <span
          key={p.id}
          className="particle"
          style={{
            '--dx': `${p.dx}px`,
            '--dy': `${p.dy}px`,
          }}
        />
      ))}
      {label && <div className="particle-label">{label}</div>}
    </div>
  );
};

export default ParticleIndicator; 