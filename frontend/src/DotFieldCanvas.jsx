import { useEffect, useRef } from 'react';

const DotFieldCanvas = ({ active }) => {
  const canvasRef = useRef(null);
  const dots = useRef([]);
  const raf = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const resize = () => {
      canvas.width = 260;
      canvas.height = 260;
      initDots();
    };
    const initDots = () => {
      const radius = canvas.width / 2;
      const ctr = canvas.width / 2;
      const step = 12;
      const arr = [];
      for (let a = 0; a < 360; a += step) {
        for (let r = radius * 0.1; r < radius * 0.9; r += step) {
          const rad = (a * Math.PI) / 180;
          const x = ctr + Math.cos(rad) * r;
          const y = ctr + Math.sin(rad) * r;
          arr.push({ x, y, o: Math.random() });
        }
      }
      dots.current = arr;
    };
    resize();

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#eae5ec';
      dots.current.forEach((d) => {
        const offset = active ? Math.sin((Date.now() / 400) + d.o * Math.PI) * 1.5 : 0;
        ctx.beginPath();
        ctx.arc(d.x + offset, d.y + offset, 2, 0, Math.PI * 2);
        ctx.fill();
      });
      raf.current = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(raf.current);
  }, [active]);

  return <canvas ref={canvasRef} style={{ width: 260, height: 260 }} />;
};

export default DotFieldCanvas; 