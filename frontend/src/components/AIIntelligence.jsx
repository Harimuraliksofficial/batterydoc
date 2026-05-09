import React from 'react';
import { CheckCircle, AlertTriangle, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';
import AnimatedGauge from './AnimatedGauge';

/**
 * AIIntelligence Component
 * Renders live battery health analytics from the AI backend.
 * Synchronized with predictionData state.
 */
const AIIntelligence = ({ predictionData }) => {
  // Console log for real-time debugging as requested
  console.log("AI CARD LIVE DATA", predictionData);

  // If no data yet, don't render or show a subtle loader (handled by parent usually)
  if (!predictionData) return null;

  const { 
    soh_prediction, 
    degradation_percentage, 
    estimated_rul, 
    battery_condition 
  } = predictionData;

  // Helper to determine status-based colors
  const getStatusColor = (status) => {
    if (status === 'Healthy') return '#4ade80'; // Green
    if (status === 'Moderate') return '#fb923c'; // Orange
    if (status === 'Critical') return '#ef4444'; // Red
    return '#ffffff';
  };

  // Helper to get corresponding Lucide icon
  const getStatusIcon = (status) => {
    const color = getStatusColor(status);
    if (status === 'Healthy') return <CheckCircle size={24} style={{ color }} />;
    if (status === 'Critical') return <AlertTriangle size={24} style={{ color }} />;
    return <ShieldAlert size={24} style={{ color }} />;
  };

  const statusColor = getStatusColor(battery_condition);

  return (
    <div className="ai-grid">
      {/* 1. SOH GAUGE CARD */}
      <motion.div 
        whileHover={{ scale: 1.02 }} 
        className="glass-panel" 
        style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}
      >
        <AnimatedGauge 
          value={soh_prediction} 
          label="State of Health" 
          unit="%" 
          color={statusColor} 
        />
      </motion.div>

      {/* 2. DEGRADATION GAUGE CARD */}
      <motion.div 
        whileHover={{ scale: 1.02 }} 
        className="glass-panel" 
        style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}
      >
        <AnimatedGauge 
          value={degradation_percentage} 
          label="Degradation %" 
          unit="%" 
          color={degradation_percentage > 30 ? "#ef4444" : "#ffffff"} 
        />
      </motion.div>

      {/* 3. ESTIMATED RUL CARD */}
      <motion.div 
        whileHover={{ scale: 1.02 }} 
        className="glass-panel" 
        style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
      >
        <span className="ai-card-label mono">Remaining Useful Life</span>
        <div className="ai-card-value">
          <motion.span
            key={estimated_rul}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {estimated_rul}
          </motion.span>
          <span className="ai-card-unit">cycles</span>
        </div>
      </motion.div>

      {/* 4. AI CONDITION STATUS CARD */}
      <motion.div 
        whileHover={{ scale: 1.02 }} 
        className="glass-panel" 
        style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start' }}
      >
        <span className="ai-card-label mono">AI Status System</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
          {getStatusIcon(battery_condition)}
          <motion.span 
            key={battery_condition}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ 
              fontSize: '1.2rem', 
              fontWeight: 700, 
              color: statusColor,
              textTransform: 'uppercase', 
              letterSpacing: '0.05em' 
            }}
          >
            {battery_condition}
          </motion.span>
        </div>
      </motion.div>
    </div>
  );
};

export default AIIntelligence;
