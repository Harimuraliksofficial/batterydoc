import React from 'react';

const InputSlider = ({ label, value, min, max, step, unit, onChange, disabled }) => (
  <div className="slider-group">
    <div className="slider-header mono">
      <label className="slider-label">{label}</label>
      <span className="slider-value">{value} {unit}</span>
    </div>
    <input 
      type="range" 
      min={min} 
      max={max} 
      step={step} 
      value={value} 
      onChange={(e) => onChange(e.target.value)} 
      disabled={disabled}
      style={{ opacity: disabled ? 0.5 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
    />
  </div>
);

const TelemetryControl = ({ telemetry, onChange, disabled }) => {
  return (
    <div>
      <InputSlider 
        label="Voltage" 
        value={telemetry.voltage} 
        min="3.0" max="4.3" step="0.01" unit="V"
        onChange={(v) => onChange('voltage', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Current Draw" 
        value={telemetry.current} 
        min="0" max="5" step="0.1" unit="A"
        onChange={(v) => onChange('current', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Temperature" 
        value={telemetry.temperature} 
        min="20" max="80" step="0.5" unit="°C"
        onChange={(v) => onChange('temperature', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Battery SOC" 
        value={telemetry.battery_percentage} 
        min="0" max="100" step="0.1" unit="%"
        onChange={(v) => onChange('battery_percentage', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Humidity" 
        value={telemetry.humidity} 
        min="20" max="100" step="1" unit="%"
        onChange={(v) => onChange('humidity', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Cycle Number" 
        value={telemetry.cycle} 
        min="0" max="500" step="1" unit="cycles"
        onChange={(v) => onChange('cycle', v)}
        disabled={disabled}
      />
      <InputSlider 
        label="Capacity" 
        value={telemetry.capacity} 
        min="0.5" max="1.1" step="0.01" unit="Ah"
        onChange={(v) => onChange('capacity', v)}
        disabled={disabled}
      />
    </div>
  );
};

export default TelemetryControl;
