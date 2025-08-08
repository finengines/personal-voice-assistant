import React, { useEffect, useRef } from 'react';

/**
 * AudioParticleSphere
 *
 * Lightweight canvas particle sphere inspired by Perplexity's voice UI.
 * - Uses a Fibonacci sphere distribution projected to 2D
 * - Animates rotation with subtle idle motion
 * - Optionally reacts to an AnalyserNode (Web Audio) for amplitude
 */
const AudioParticleSphere = ({
  enabled = true,
  analyser = null,
  size = 360,
  density = 'medium', // 'low' | 'medium' | 'high'
  color = 'rgba(0,0,0,0.5)',
}) => {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const pointsRef = useRef([]);
  const rotationRef = useRef({ x: 0.2, y: 0.1 });
  const energyRef = useRef(0);

  // Convert density to number of points
  const getPointCount = () => {
    if (density === 'low') return 900;
    if (density === 'high') return 2800;
    return 1600; // medium
  };

  // Precompute points on a unit sphere using Fibonacci lattice
  const initPoints = (num) => {
    const points = [];
    const phi = Math.PI * (3 - Math.sqrt(5)); // golden angle
    for (let i = 0; i < num; i += 1) {
      const y = 1 - (i / (num - 1)) * 2; // y goes from 1 to -1
      const radius = Math.sqrt(1 - y * y);
      const theta = phi * i;
      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;
      points.push({ x, y, z });
    }
    pointsRef.current = points;
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

    initPoints(getPointCount());

    const freqArray = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;

    const render = () => {
      // Read audio energy and smooth
      if (analyser && freqArray) {
        analyser.getByteFrequencyData(freqArray);
        let sum = 0;
        for (let i = 0; i < freqArray.length; i += 1) sum += freqArray[i];
        const avg = sum / freqArray.length; // 0..255
        const normalized = avg / 255; // 0..1
        // Exponential moving average for smoothness
        energyRef.current = energyRef.current * 0.85 + normalized * 0.15;
      } else {
        // Idle low energy pulsing
        const t = performance.now() / 2000;
        energyRef.current = 0.25 + 0.05 * Math.sin(t);
      }

      // Rotation rates influenced by energy
      rotationRef.current.x += 0.002 + energyRef.current * 0.004;
      rotationRef.current.y += 0.003 + energyRef.current * 0.005;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = color;

      const radius = (pxSize / 2) * (0.80 + energyRef.current * 0.12);
      const cx = pxSize / 2;
      const cy = pxSize / 2;

      const rotX = rotationRef.current.x;
      const rotY = rotationRef.current.y;

      const sinX = Math.sin(rotX);
      const cosX = Math.cos(rotX);
      const sinY = Math.sin(rotY);
      const cosY = Math.cos(rotY);

      for (let i = 0; i < pointsRef.current.length; i += 1) {
        const p = pointsRef.current[i];

        // Rotate point around X and Y
        // Rotate around Y
        const x1 = p.x * cosY - p.z * sinY;
        const z1 = p.x * sinY + p.z * cosY;
        // Rotate around X
        const y2 = p.y * cosX - z1 * sinX;
        const z2 = p.y * sinX + z1 * cosX;

        // Perspective projection (closer points brighter/larger)
        const perspective = 1 / (1.4 - z2); // z in [-1,1] => scale ~ [0.7, inf)
        const screenX = cx + x1 * radius * perspective;
        const screenY = cy + y2 * radius * perspective;
        const pointSize = Math.max(1, 1.2 * perspective);
        const alpha = Math.min(0.8, 0.35 + 0.6 * perspective);

        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(screenX, screenY, pointSize, 0, Math.PI * 2);
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, analyser, size, density, color]);

  if (!enabled) return null;
  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', pointerEvents: 'none' }}
      aria-hidden
    />
  );
};

export default AudioParticleSphere;


