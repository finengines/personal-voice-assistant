// Lightweight audio features helper and React hook for Web Audio analyser
// Computes smoothed energy bands, spectral centroid, and a simple beat gate
// with minimal allocations per frame.

import { useEffect, useRef, useState } from 'react';

export function computeBandsFromFFT(fftArray) {
  // Split into rough bands: bass (20-250Hz), mid (250-2k), treble (2k-8k)
  const len = fftArray.length;
  if (len === 0) return { bass: 0, mid: 0, treble: 0, rms: 0 };

  let sum = 0;
  let bassSum = 0;
  let midSum = 0;
  let trebleSum = 0;

  const bassEnd = Math.floor(len * 0.1); // ~0-10%
  const midEnd = Math.floor(len * 0.5); // ~10-50%

  for (let i = 0; i < len; i += 1) {
    const v = fftArray[i] / 255; // 0..1
    sum += v * v;
    if (i < bassEnd) bassSum += v;
    else if (i < midEnd) midSum += v;
    else trebleSum += v;
  }

  const rms = Math.sqrt(sum / len);
  return {
    bass: bassSum / (bassEnd || 1),
    mid: midSum / (midEnd - bassEnd || 1),
    treble: trebleSum / (len - midEnd || 1),
    rms,
  };
}

export function computeSpectralCentroid(fftArray, sampleRate = 48000) {
  const len = fftArray.length;
  if (len === 0) return 0;
  let num = 0;
  let den = 0;
  const nyquist = sampleRate / 2;
  for (let i = 0; i < len; i += 1) {
    const mag = fftArray[i];
    const freq = (i / len) * nyquist;
    num += freq * mag;
    den += mag;
  }
  if (den === 0) return 0;
  return num / den; // Hz
}

export function useAudioFeatures(analyser, options = {}) {
  const {
    smoothing = 0.85,
    fftSize = 1024,
    sensitivity = 1.0,
  } = options;

  const [features, setFeatures] = useState({
    bass: 0,
    mid: 0,
    treble: 0,
    rms: 0,
    centroidHz: 0,
    beat: false,
  });

  const rafRef = useRef(0);
  const fftRef = useRef(null);
  const emaRef = useRef({ bass: 0, mid: 0, treble: 0, rms: 0, centroidHz: 0 });
  const beatRef = useRef({ ema: 0, lastTime: 0, cooldownMs: 140, armed: true });

  useEffect(() => {
    if (!analyser) return undefined;
    try {
      analyser.fftSize = fftSize;
      analyser.smoothingTimeConstant = smoothing;
    } catch (_) {}

    const freqArray = new Uint8Array(analyser.frequencyBinCount);
    fftRef.current = freqArray;

    const loop = () => {
      try {
        analyser.getByteFrequencyData(freqArray);
      } catch (_) {
        // Analyser may be disconnected
        rafRef.current = requestAnimationFrame(loop);
        return;
      }

      const bands = computeBandsFromFFT(freqArray);
      const centroidHz = computeSpectralCentroid(freqArray);

      // EMA smoothing
      const alpha = 0.18; // responsiveness
      emaRef.current.bass = emaRef.current.bass * (1 - alpha) + bands.bass * alpha;
      emaRef.current.mid = emaRef.current.mid * (1 - alpha) + bands.mid * alpha;
      emaRef.current.treble = emaRef.current.treble * (1 - alpha) + bands.treble * alpha;
      emaRef.current.rms = emaRef.current.rms * (1 - alpha) + bands.rms * alpha;
      emaRef.current.centroidHz = emaRef.current.centroidHz * (1 - alpha) + centroidHz * alpha;

      // Simple beat gate on bass with cooldown
      const now = performance.now();
      const gain = Math.max(0.5, Math.min(2.5, sensitivity));
      const bassVal = emaRef.current.bass * gain;
      beatRef.current.ema = beatRef.current.ema * 0.9 + bassVal * 0.1;
      const threshold = beatRef.current.ema * 1.35 + 0.02; // adaptive
      let beat = false;
      if (bassVal > threshold && beatRef.current.armed) {
        beat = true;
        beatRef.current.armed = false;
        beatRef.current.lastTime = now;
      }
      if (now - beatRef.current.lastTime > beatRef.current.cooldownMs) {
        beatRef.current.armed = true;
      }

      setFeatures({
        bass: emaRef.current.bass,
        mid: emaRef.current.mid,
        treble: emaRef.current.treble,
        rms: emaRef.current.rms,
        centroidHz: emaRef.current.centroidHz,
        beat,
      });

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [analyser, fftSize, smoothing, sensitivity]);

  return features;
}

export default useAudioFeatures;


