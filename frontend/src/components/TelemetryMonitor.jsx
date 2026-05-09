import React from 'react';
import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';

/**
 * TelemetryMonitor — Real-Time Hardware Readout Panel
 * 
 * Displays live incoming values from hardware/backend in a compact
 * Formula E inspired telemetry card grid. Every card updates live
 * whenever the telemetry or predictionData props change.
 * 
 * NO fake data. NO demo values. Every number comes from props.
 */
const TelemetryMonitor = ({ telemetry, predictionData }) => {
  console.log("TELEMETRY MONITOR LIVE", { telemetry, predictionData });

  if (!telemetry || !predictionData) return null;

  // Build the card data from LIVE state only
  const cards = [
    { label: 'VOLTAGE',       value: telemetry.voltage,                   unit: 'V',      color: '#3b82f6' },
    { label: 'CURRENT',       value: telemetry.current,                   unit: 'A',      color: '#8b5cf6' },
    { label: 'TEMPERATURE',   value: telemetry.temperature,               unit: '°C',     color: '#fb923c' },
    { label: 'BATTERY SOC',   value: telemetry.battery_percentage,        unit: '%',      color: '#4ade80' },
    { label: 'HUMIDITY',      value: telemetry.humidity,                   unit: '%',      color: '#06b6d4' },
    { label: 'CYCLE COUNT',   value: telemetry.cycle,                     unit: 'cyc',    color: '#a78bfa' },
    { label: 'CAPACITY',      value: telemetry.capacity,                  unit: 'Ah',     color: '#f472b6' },
    { label: 'SOH',           value: predictionData.soh_prediction,       unit: '%',      color: '#4ade80' },
    { label: 'DEGRADATION',   value: predictionData.degradation_percentage, unit: '%',    color: '#ef4444' },
    { label: 'EST. RUL',      value: predictionData.estimated_rul,        unit: 'cyc',    color: '#fbbf24' },
    { label: 'CONDITION',     value: null, text: predictionData.battery_condition, unit: '', color: predictionData.battery_condition === 'Healthy' ? '#4ade80' : predictionData.battery_condition === 'Critical' ? '#ef4444' : '#fb923c' },
  ];

  return (
    <div style={{ marginTop: '24px' }}>
      {/* Section header */}
      <div className="glass-panel" style={{ marginBottom: '16px', padding: '16px 24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '8px', height: '8px', borderRadius: '50%',
          background: '#4ade80',
          boxShadow: '0 0 8px #4ade80',
          animation: 'pulse 1.5s ease-in-out infinite'
        }} />
        <Activity size={16} color="#4ade80" />
        <span className="mono" style={{ fontSize: '12px', color: '#4ade80', letterSpacing: '0.1em', fontWeight: 600 }}>
          REAL-TIME TELEMETRY MONITOR
        </span>
        <span className="mono" style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {new Date().toLocaleTimeString()}
        </span>
      </div>

      {/* Telemetry card grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
        gap: '12px',
      }}>
        {cards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className="glass-panel"
            style={{
              padding: '14px 16px',
              borderLeft: `3px solid ${card.color}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <span className="mono" style={{ fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              {card.label}
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <motion.span
                key={card.text || card.value}
                initial={{ opacity: 0.3 }}
                animate={{ opacity: 1 }}
                className="mono"
                style={{
                  fontSize: card.text ? '14px' : '20px',
                  fontWeight: 700,
                  color: card.color,
                  textTransform: card.text ? 'uppercase' : 'none',
                }}
              >
                {card.text || (typeof card.value === 'number' ? card.value.toFixed(card.unit === 'cyc' ? 0 : 2) : card.value)}
              </motion.span>
              {card.unit && !card.text && (
                <span className="mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {card.unit}
                </span>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TelemetryMonitor;
