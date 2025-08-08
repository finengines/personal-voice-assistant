import React, { useEffect, useRef } from 'react';
import useAudioFeatures from './AudioFeatures';

// Constellation effect: points softly orbit with lines connecting nearby points
// Audio-reactive connection radius and pulse on beats
const ConstellationParticles = ({
  enabled = true,
  analyser = null,
  size = 360,
  density = 'medium', // 'low' | 'medium' | 'high'
  color = '#5fd1ff',
  lineColor = 'rgba(95, 209, 255, 0.35)',
  sensitivity = 1.0,
}) => {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const pointsRef = useRef([]);
  const features = useAudioFeatures(analyser, { smoothing: 0.85, fftSize: 1024, sensitivity });

  const getCount = () => {
    if (density === 'low') return 120;
    if (density === 'high') return 360;
    return 220;
  };

  useEffect(() => {
    if (!enabled) return undefined;

    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pxSize = size * dpr;
    canvas.width = pxSize;
    canvas.height = pxSize;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    const init = () => {
      const arr = [];
      for (let i = 0; i < getCount(); i += 1) {
        const a = Math.random() * Math.PI * 2;
        const r = (pxSize * 0.36) + Math.random() * (pxSize * 0.1);
        arr.push({ a, r, s: 0.001 + Math.random() * 0.002, o: Math.random() });
      }
      pointsRef.current = arr;
    };
    init();

    const render = () => {
      ctx.clearRect(0, 0, pxSize, pxSize);
      const cx = pxSize / 2;
      const cy = pxSize / 2;

      // Audio reactive radius and glow
      const connRadius = 36 + features.rms * 110 + features.mid * 60;
      const pulse = features.beat ? 1.5 : 1.0;

      // Draw points
      for (let i = 0; i < pointsRef.current.length; i += 1) {
        const p = pointsRef.current[i];
        p.a += p.s * (0.6 + features.treble * 1.5);
        const x = cx + Math.cos(p.a) * p.r * pulse;
        const y = cy + Math.sin(p.a) * p.r * pulse;
        p.x = x;
        p.y = y;
      }

      // Lines
      ctx.lineWidth = Math.max(0.6, 1.4 - features.rms * 1.1);
      ctx.strokeStyle = lineColor;
      for (let i = 0; i < pointsRef.current.length; i += 1) {
        const a = pointsRef.current[i];
        for (let j = i + 1; j < i + 10 && j < pointsRef.current.length; j += 1) {
          const b = pointsRef.current[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < connRadius) {
            const alpha = Math.max(0, 1 - d / connRadius) * (0.28 + features.rms * 0.7 + (features.beat ? 0.2 : 0));
            ctx.globalAlpha = Math.min(0.9, alpha);
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Points on top
      ctx.globalAlpha = 1;
      ctx.fillStyle = color;
      for (let i = 0; i < pointsRef.current.length; i += 1) {
        const p = pointsRef.current[i];
        const radius = 1.0 + features.rms * 1.5 + features.treble * 0.7 + (features.beat ? 0.6 : 0);
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [enabled, analyser, size, density, color, lineColor, sensitivity]);

  if (!enabled) return null;
  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', pointerEvents: 'none' }}
      aria-hidden
    />
  );
};

export default ConstellationParticles;


