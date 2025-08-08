import React, { useEffect, useRef } from 'react';
import useAudioFeatures from './AudioFeatures';

// Flow-field particle system driven by a procedural vector field
// Audio-reactive speed and slight directional bias using bass/mid bands
const FlowFieldParticles = ({
  enabled = true,
  analyser = null,
  size = 360,
  numParticles = 1200,
  fieldScale = 0.006,
  baseSpeed = 0.5,
  color = 'rgba(90, 90, 255, 0.7)',
  trailAlpha = 0.08,
  sensitivity = 1.0,
}) => {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const particlesRef = useRef([]);

  const features = useAudioFeatures(analyser, { smoothing: 0.85, fftSize: 1024, sensitivity });

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

    // Initialize particles
    const initParticles = () => {
      const arr = [];
      for (let i = 0; i < numParticles; i += 1) {
        arr.push({
          x: Math.random() * pxSize,
          y: Math.random() * pxSize,
          vx: 0,
          vy: 0,
        });
      }
      particlesRef.current = arr;
    };
    initParticles();

    // Clear with slight alpha to create trails
    const fade = () => {
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = `rgba(0,0,0,${trailAlpha})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };

    const drawPoint = (x, y, alpha, sizePx) => {
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, sizePx, 0, Math.PI * 2);
      ctx.fill();
    };

    const field = (x, y, t) => {
      // Lightweight pseudo-noise vector field using trig; fast and loopable
      const nx = x * fieldScale;
      const ny = y * fieldScale;
      const a = Math.sin(nx + t * 0.6) + Math.cos(ny - t * 0.7);
      const b = Math.cos(ny + t * 0.35) - Math.sin(nx * 0.5 - t * 0.4);
      return { x: a, y: b };
    };

    let lastTime = performance.now();
    const render = () => {
      const now = performance.now();
      const dt = Math.min(32, now - lastTime) / 16.0; // normalize to ~60fps
      lastTime = now;

      fade();
      const t = now * (0.0015 + features.mid * 0.0008);

      // Audio reactivity
      const speedGain = baseSpeed * (0.45 + features.bass * 2.2 + features.mid * 0.8);
      const jitter = (features.treble ** 2) * 1.2;

      ctx.globalCompositeOperation = 'lighter';

      for (let i = 0; i < particlesRef.current.length; i += 1) {
        const p = particlesRef.current[i];
        const v = field(p.x, p.y, t);
        // Normalize and scale
        let vx = v.x;
        let vy = v.y;
        const mag = Math.hypot(vx, vy) || 1;
        vx /= mag;
        vy /= mag;

        // Bass bias rotates the flow subtly clockwise/counter-clockwise
        const bias = (features.bass - 0.5) * 0.9;
        const bx = vx - vy * bias;
        const by = vy + vx * bias;

        p.vx = (p.vx + bx * speedGain * dt) * 0.96;
        p.vy = (p.vy + by * speedGain * dt) * 0.96;
        p.x += p.vx + (Math.random() - 0.5) * jitter;
        p.y += p.vy + (Math.random() - 0.5) * jitter;

        // Wrap around edges for continuity
        if (p.x < 0) p.x += pxSize;
        if (p.x > pxSize) p.x -= pxSize;
        if (p.y < 0) p.y += pxSize;
        if (p.y > pxSize) p.y -= pxSize;

        const alpha = Math.min(0.95, 0.18 + features.rms * 1.2);
        const sizePx = 0.8 + features.rms * 1.4 + (features.beat ? 0.6 : 0);
        drawPoint(p.x, p.y, alpha, sizePx);
      }

      rafRef.current = requestAnimationFrame(render);
    };

    // Prime background
    ctx.fillStyle = 'rgba(0,0,0,1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [enabled, analyser, size, numParticles, fieldScale, baseSpeed, color, trailAlpha, sensitivity]);

  if (!enabled) return null;
  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', pointerEvents: 'none', borderRadius: '50%' }}
      aria-hidden
    />
  );
};

export default FlowFieldParticles;


