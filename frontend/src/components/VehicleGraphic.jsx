import React from 'react';
import { motion } from 'framer-motion';

const VehicleGraphic = ({ severity }) => {
  // Determine color based on severity
  let glowColor = 'rgba(255, 255, 255, 0.2)';
  let strokeColor = '#ffffff';
  
  if (severity === 'Critical') {
    glowColor = 'rgba(239, 68, 68, 0.4)';
    strokeColor = '#ef4444';
  } else if (severity === 'Moderate') {
    glowColor = 'rgba(249, 115, 22, 0.3)';
    strokeColor = '#f97316';
  } else if (severity === 'Healthy') {
    glowColor = 'rgba(74, 222, 128, 0.3)';
    strokeColor = '#4ade80';
  }

  return (
    <div className="vehicle-container">
      {/* Background Glow */}
      <motion.div 
        animate={{ 
          boxShadow: [`0 0 20px ${glowColor}`, `0 0 40px ${glowColor}`, `0 0 20px ${glowColor}`] 
        }}
        transition={{ repeat: Infinity, duration: 2 }}
        style={{
          position: 'absolute',
          width: '160px',
          height: '40px',
          borderRadius: '100%',
          filter: 'blur(24px)',
          opacity: 0.5
        }}
      />
      
      {/* Formula E SVG Silhouette */}
      <svg viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', height: '100%', filter: 'drop-shadow(0 25px 25px rgba(0,0,0,0.5))', zIndex: 10 }}>
        {/* Chassis */}
        <motion.path 
          d="M 50 100 L 90 70 L 150 65 L 200 65 L 250 50 L 280 50 L 320 65 L 360 80 L 370 100 Z" 
          stroke={strokeColor} 
          strokeWidth="2" 
          fill="rgba(0,0,0,0.8)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.5, ease: "easeInOut" }}
        />
        {/* Cockpit / Halo */}
        <path d="M 170 65 C 180 40, 220 40, 230 65" stroke="rgba(255,255,255,0.4)" strokeWidth="2" />
        {/* Wheels */}
        <circle cx="100" cy="100" r="20" stroke="rgba(255,255,255,0.6)" strokeWidth="3" fill="#111" />
        <circle cx="310" cy="100" r="20" stroke="rgba(255,255,255,0.6)" strokeWidth="3" fill="#111" />
        {/* Battery Pack Area (Animated based on severity) */}
        <motion.rect 
          x="140" y="80" width="100" height="15" rx="5" 
          fill={glowColor}
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
        <text x="190" y="91" fill="white" fontSize="8" textAnchor="middle" className="mono" style={{ letterSpacing: '0.1em', fontWeight: 'bold' }}>BATTERY DOCK</text>
      </svg>
    </div>
  );
};

export default VehicleGraphic;
