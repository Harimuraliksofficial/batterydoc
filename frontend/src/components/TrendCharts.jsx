import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, LineChart, Line
} from 'recharts';

/**
 * Custom Tooltip — F1 telemetry style
 */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-panel mono" style={{
        padding: '10px 14px', fontSize: '10px',
        border: '1px solid rgba(255,255,255,0.1)',
        minWidth: '120px',
      }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '9px' }}>
          T: {label}
        </p>
        {payload.map((entry, index) => (
          <p key={index} style={{
            color: entry.color, fontWeight: 'bold',
            display: 'flex', justifyContent: 'space-between', gap: '12px'
          }}>
            <span>{entry.name}</span>
            <span>{typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * TrendCharts — Live telemetry visualization.
 * 
 * IMPORTANT: `isAnimationActive` is set to FALSE.
 * Recharts animation only fires on mount. On subsequent data pushes,
 * the animation blocks the update, making charts appear "frozen".
 * Disabling it ensures every new data point renders immediately.
 */
const TrendCharts = ({ history }) => {
  console.log("LIVE HISTORY", history);

  if (!history || history.length === 0) {
    return (
      <div style={{
        height: '100%', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)',
        minHeight: '200px',
      }}>
        <div style={{
          width: '12px', height: '12px', borderRadius: '50%',
          border: '2px solid var(--text-muted)',
          borderTopColor: 'transparent',
          animation: 'spin 1s linear infinite',
          marginBottom: '16px',
        }} />
        <span className="mono" style={{ fontSize: '11px', letterSpacing: '0.1em' }}>
          Waiting for telemetry stream...
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>

      {/* [00] ELECTRICAL LOAD */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px', flex: 1 }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#3b82f6', marginBottom: '6px' }}>
          [00] ELECTRICAL LOAD (V / A)
        </h4>
        <ResponsiveContainer width="100%" height={70}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line yAxisId="left" type="monotone" dataKey="voltage" name="Voltage V" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="right" type="monotone" dataKey="current" name="Current A" stroke="#8b5cf6" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* [01] SOH TREND */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px', flex: 1 }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#4ade80', marginBottom: '6px' }}>
          [01] STATE OF HEALTH TREND
        </h4>
        <ResponsiveContainer width="100%" height={70}>
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
            <Area type="monotone" dataKey="soh_prediction" name="SOH %" stroke="#4ade80" fillOpacity={1} fill="url(#colorSoh)" strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* [02] THERMAL ANALYSIS */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px', flex: 1 }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#fb923c', marginBottom: '6px' }}>
          [02] THERMAL ANALYSIS (°C)
        </h4>
        <ResponsiveContainer width="100%" height={70}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="temperature" name="Temp °C" stroke="#fb923c" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* [03] DEGRADATION FORECAST */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px', flex: 1 }}>
        <h4 className="chart-title mono" style={{ fontSize: '10px', color: '#ef4444', marginBottom: '6px' }}>
          [03] DEGRADATION GROWTH FORECAST
        </h4>
        <ResponsiveContainer width="100%" height={70}>
          <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} stroke="#444" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="degradation_percentage" name="Degradation %" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
};

export default TrendCharts;
