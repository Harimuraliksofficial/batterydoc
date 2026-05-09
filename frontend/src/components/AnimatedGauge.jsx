import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

const AnimatedGauge = ({ value, label, unit, color }) => {
  const data = [
    { name: 'Value', value: value },
    { name: 'Empty', value: 100 - value }
  ];

  return (
    <div style={{ position: 'relative', width: '100%', height: '140px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="70%"
            startAngle={180}
            endAngle={0}
            innerRadius="75%"
            outerRadius="95%"
            dataKey="value"
            stroke="none"
            isAnimationActive={true}
          >
            <Cell key="cell-0" fill={color} />
            <Cell key="cell-1" fill="rgba(255,255,255,0.05)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      
      <div style={{ position: 'absolute', top: '55%', textAlign: 'center', width: '100%' }}>
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="ai-card-value" 
          style={{ justifyContent: 'center', color: color, marginBottom: '4px' }}
        >
          <span>{value.toFixed(1)}</span>
          <span className="ai-card-unit" style={{ color, opacity: 0.8 }}>{unit}</span>
        </motion.div>
        <span className="ai-card-label mono" style={{ margin: 0 }}>{label}</span>
      </div>
    </div>
  );
};

export default AnimatedGauge;
