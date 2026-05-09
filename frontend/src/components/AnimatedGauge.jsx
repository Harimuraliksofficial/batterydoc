import React, { useEffect, useRef } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

/**
 * AnimatedGauge — Pure SVG + Framer Motion gauge.
 * 
 * WHY NOT RECHARTS PIE?
 * Recharts PieChart caches its initial data and only animates on mount.
 * When predictionData updates with a new SOH value, the Pie never
 * re-animates — it appears "frozen". This is the #1 root cause of
 * the "static gauge" bug.
 *
 * This component uses a Framer Motion spring to smoothly animate
 * the arc every single time the `value` prop changes.
 */
const AnimatedGauge = ({ value, label, unit, color }) => {
  // Clamp value to 0–100 range for safety
  const clamped = Math.max(0, Math.min(100, value));

  // Spring-animated value: smoothly transitions whenever `clamped` changes
  const springValue = useSpring(clamped, { stiffness: 80, damping: 20 });

  // Update the spring target whenever the value prop changes
  useEffect(() => {
    springValue.set(clamped);
  }, [clamped, springValue]);

  // SVG arc math
  const radius = 60;
  const strokeWidth = 10;
  const cx = 75;
  const cy = 80;
  const circumference = Math.PI * radius; // half-circle

  // Transform spring value → dashoffset for the arc stroke
  const dashOffset = useTransform(springValue, [0, 100], [circumference, 0]);

  // We also need a display number that animates
  const displayRef = useRef(null);
  useEffect(() => {
    const unsubscribe = springValue.on('change', (latest) => {
      if (displayRef.current) {
        displayRef.current.textContent = latest.toFixed(1);
      }
    });
    return unsubscribe;
  }, [springValue]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '140px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <svg width="150" height="100" viewBox="0 0 150 100" style={{ overflow: 'visible' }}>
        {/* Background track */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Animated foreground arc */}
        <motion.path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: dashOffset }}
          filter={`drop-shadow(0 0 6px ${color})`}
        />
      </svg>

      {/* Numeric readout */}
      <div style={{ position: 'absolute', top: '55%', textAlign: 'center', width: '100%' }}>
        <div
          className="ai-card-value"
          style={{ justifyContent: 'center', color: color, marginBottom: '4px' }}
        >
          <span ref={displayRef}>{clamped.toFixed(1)}</span>
          <span className="ai-card-unit" style={{ color, opacity: 0.8 }}>{unit}</span>
        </div>
        <span className="ai-card-label mono" style={{ margin: 0 }}>{label}</span>
      </div>
    </div>
  );
};

export default AnimatedGauge;
