import React from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as RechartsTooltip
} from 'recharts';
import { Cpu } from 'lucide-react';

const MLReportGraph = ({ predictionData }) => {
  if (!predictionData) return null;

  const { soh_prediction, degradation_percentage, estimated_rul } = predictionData;

  // Calculate RUL score (assuming max 500 for a typical EV battery in this app)
  const rulScore = Math.min(100, Math.max(0, (estimated_rul / 500) * 100));
  
  // Inverse metrics for a "Health" radar (100 is best)
  const data = [
    { subject: 'State of Health', A: soh_prediction, fullMark: 100 },
    { subject: 'Integrity', A: 100 - degradation_percentage, fullMark: 100 },
    { subject: 'Remaining Life', A: rulScore, fullMark: 100 },
    { subject: 'Thermal Profile', A: soh_prediction > 85 ? 90 : 60, fullMark: 100 },
    { subject: 'Power Capacity', A: 100 - (degradation_percentage * 0.5), fullMark: 100 },
  ];

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '280px', marginTop: '16px' }}>
      <h2 className="panel-title">
         <Cpu size={20} color="#8b5cf6" />
         ML Health Profile Radar
      </h2>
      <div style={{ flex: 1, width: '100%', height: '100%', position: 'relative' }}>
        {/* Decorative background glow */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          width: '150px', height: '150px', background: 'radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, rgba(0,0,0,0) 70%)',
          borderRadius: '50%', filter: 'blur(20px)', pointerEvents: 'none'
        }}></div>
        
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="65%" data={data}>
            <PolarGrid stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <RechartsTooltip 
              contentStyle={{ backgroundColor: 'rgba(10, 10, 10, 0.9)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '8px', color: '#fff', fontSize: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
              itemStyle={{ color: '#a78bfa' }}
            />
            <Radar name="AI Assessment" dataKey="A" stroke="#8b5cf6" strokeWidth={2} fill="url(#colorRadar)" fillOpacity={0.6} isAnimationActive={false} />
            <defs>
              <linearGradient id="colorRadar" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.2}/>
              </linearGradient>
            </defs>
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default MLReportGraph;
