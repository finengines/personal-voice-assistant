import React, { useEffect, useRef } from 'react';

// Radial bar spectrum visualizer using analyser frequency data
const RadialSpectrum = ({
  enabled = true,
  analyser = null,
  size = 360,
  barCount = 96,
  innerRadiusRatio = 0.45,
  barColor = '#a6ff7a',
  glow = true,
}) => {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);

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

    const freqArray = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;

    const render = () => {
      ctx.clearRect(0, 0, pxSize, pxSize);
      const cx = pxSize / 2;
      const cy = pxSize / 2;

      if (!analyser || !freqArray) {
        rafRef.current = requestAnimationFrame(render);
        return;
      }

      try { analyser.getByteFrequencyData(freqArray); } catch (_) {}

      const step = Math.floor(freqArray.length / barCount);
      const beatPulse = analyser ? (Math.sin(performance.now() / 100) > 0.98 ? 1.04 : 1.0) : 1.0;
      const inner = pxSize * innerRadiusRatio * (0.92 + 0.12 * beatPulse);
      const maxBar = pxSize * 0.24;

      for (let i = 0; i < barCount; i += 1) {
        const angle = (i / barCount) * Math.PI * 2 - Math.PI / 2;
        // average small window to reduce flicker
        let sum = 0;
        const start = i * step;
        const end = Math.min(freqArray.length, start + step);
        for (let j = start; j < end; j += 1) sum += freqArray[j];
        const avg = sum / Math.max(1, end - start);
        const magnitude = (avg / 255);
        const barLen = inner + Math.pow(magnitude, 1.1) * maxBar;

        const x1 = cx + Math.cos(angle) * inner;
        const y1 = cy + Math.sin(angle) * inner;
        const x2 = cx + Math.cos(angle) * barLen;
        const y2 = cy + Math.sin(angle) * barLen;

        ctx.strokeStyle = barColor;
        ctx.lineWidth = Math.max(2, pxSize * 0.003);
        if (glow) {
          ctx.shadowColor = barColor;
          ctx.shadowBlur = 12;
        } else {
          ctx.shadowBlur = 0;
        }
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
  }, [enabled, analyser, size, barCount, innerRadiusRatio, barColor, glow]);

  if (!enabled) return null;
  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', pointerEvents: 'none' }}
      aria-hidden
    />
  );
};

export default RadialSpectrum;


