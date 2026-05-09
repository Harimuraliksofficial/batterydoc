import React from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, 
  ResponsiveContainer, CartesianGrid, LineChart, Line 
} from 'recharts';

/**
 * Custom Tooltip for professional telemetry feel
 */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-panel mono" style={{ padding: '12px', fontSize: '10px', border: '1px solid rgba(255,255,255,0.1)' }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px' }}>
          T-STAMP: {label}
        </p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color, fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
            <span>{entry.name.toUpperCase()}</span>
            <span>{entry.value.toFixed(2)}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * TrendCharts Component
 * Formula E inspired telemetry visualization system.
 * Powered by live history prop.
 */
const TrendCharts = ({ history }) => {
  // Debug log for history stream
  console.log("LIVE HISTORY", history);

  // Elegant placeholder when no data stream is active
  if (!history || history.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <div className="loader-ring" style={{ marginBottom: '16px', opacity: 0.5 }}></div>
        <span className="mono" style={{ fontSize: '12px', letterSpacing: '0.1em' }}>Waiting for telemetry stream...</span>
      </div>
    );
  }

  return (
    <div className="charts-grid" style={{ display: 'grid', gridTemplateRows: 'repeat(4, 1fr)', gap: '16px', height: '100%', overflowY: 'auto', paddingRight: '8px' }}>
      
      {/* 0. ELECTRICAL LOAD (VOLTAGE & CURRENT) */}
      <div className="chart-container" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#3b82f6', marginBottom: '8px' }}>
          [00] ELECTRICAL LOAD (V / A)
        </h4>
        <ResponsiveContainer width="100%" height={80}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line yAxisId="left" type="monotone" dataKey="voltage" name="Voltage" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={true} />
            <Line yAxisId="right" type="monotone" dataKey="current" name="Current" stroke="#8b5cf6" strokeWidth={2} dot={false} isAnimationActive={true} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* 1. SOH TREND (GREEN NEON AREA) */}
      <div className="chart-container" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#4ade80', marginBottom: '8px' }}>
          [01] STATE OF HEALTH TREND
        </h4>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorSoh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#4ade80" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area 
              type="monotone" 
              dataKey="soh_prediction" 
              name="SOH" 
              stroke="#4ade80" 
              fillOpacity={1} 
              fill="url(#colorSoh)" 
              strokeWidth={2} 
              isAnimationActive={true}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 2. THERMAL STRESS (ORANGE LINE) */}
      <div className="chart-container" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#fb923c', marginBottom: '8px' }}>
          [02] THERMAL ANALYSIS (TEMP °C)
        </h4>
        <ResponsiveContainer width="100%" height={100}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="temperature" 
              name="Temperature" 
              stroke="#fb923c" 
              strokeWidth={2} 
              dot={false} 
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 3. DEGRADATION FORECAST (RED LINE) */}
      <div className="chart-container" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#ef4444', marginBottom: '8px' }}>
          [03] DEGRADATION GROWTH FORECAST
        </h4>
        <ResponsiveContainer width="100%" height={100}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="degradation_percentage" 
              name="Degradation" 
              stroke="#ef4444" 
              strokeWidth={2} 
              dot={false} 
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
};

export default TrendCharts;
