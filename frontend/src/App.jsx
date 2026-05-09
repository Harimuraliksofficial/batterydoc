import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, AlertTriangle, ShieldAlert, Navigation, Zap, Loader2, WifiOff } from 'lucide-react';
import TelemetryControl from './components/TelemetryControl';
import AIIntelligence from './components/AIIntelligence';
import TrendCharts from './components/TrendCharts';
import VehicleGraphic from './components/VehicleGraphic';
import TelemetryMonitor from './components/TelemetryMonitor';

// ─────────────────────────────────────────────────────────────
// Axios instance — single source of truth for API base URL
// ─────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 5000,
});

// ─────────────────────────────────────────────────────────────
// App Component — Production Telemetry Dashboard
// ─────────────────────────────────────────────────────────────
const App = () => {

  // ═══════════════════════════════════════════════════════════
  // 1. STATE — all live data, no hardcoded values after init
  // ═══════════════════════════════════════════════════════════

  // Telemetry slider state (maps to backend TelemetryInput schema)
  const [telemetry, setTelemetry] = useState({
    voltage: 4.1,
    current: 2.2,
    temperature: 31.0,
    battery_percentage: 82.0,
    humidity: 45.0,
    cycle: 120,
    capacity: 0.91,
  });

  // AI prediction response from backend (null until first fetch)
  const [predictionData, setPredictionData] = useState(null);

  // Chart history — array of snapshot objects, max 20
  const [history, setHistory] = useState([]);

  // UI flags
  const [isLive, setIsLive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Debounce timer ref (stable across renders)
  const debounceRef = useRef(null);

  // Track whether initial fetch has completed (prevents double-fire)
  const initialFetchDone = useRef(false);

  // ═══════════════════════════════════════════════════════════
  // 2. API FUNCTIONS — useCallback to keep stable references
  // ═══════════════════════════════════════════════════════════

  /**
   * fetchPrediction — POST telemetry → backend → receive AI prediction
   * 
   * This is the CORE pipeline:
   *   slider change → fetchPrediction → setPredictionData → UI rerenders
   *   
   * The function maps frontend field names (cycle, capacity) to
   * backend field names (cycle_num, capacity_ah) before sending.
   */
  const fetchPrediction = useCallback(async (currentTelemetry) => {
    setIsLoading(true);
    setError(null);

    try {
      // Map frontend keys → backend Pydantic schema
      const payload = {
        voltage: currentTelemetry.voltage,
        current: currentTelemetry.current,
        temperature: currentTelemetry.temperature,
        battery_percentage: currentTelemetry.battery_percentage,
        humidity: currentTelemetry.humidity,
        cycle_num: currentTelemetry.cycle,
        capacity_ah: currentTelemetry.capacity,
      };

      console.log("LIVE TELEMETRY", payload);

      const response = await api.post('/predict', payload);
      const data = response.data;

      console.log("BACKEND RESPONSE", data);

      // Update prediction state → triggers rerender of gauges, cards, etc.
      setPredictionData(data);

      // Build a COMPLETE history snapshot with ALL required fields
      const newPoint = {
        time: new Date().toLocaleTimeString(),
        voltage: currentTelemetry.voltage,
        current: currentTelemetry.current,
        temperature: currentTelemetry.temperature,
        battery_percentage: currentTelemetry.battery_percentage,
        humidity: currentTelemetry.humidity,
        cycle: currentTelemetry.cycle,
        capacity: currentTelemetry.capacity,
        soh_prediction: data.soh_prediction,
        degradation_percentage: data.degradation_percentage,
        estimated_rul: data.estimated_rul,
      };

      console.log("NEW HISTORY POINT", newPoint);

      // Append to history using immutable update — NEVER overwrite
      setHistory(prev => {
        const updated = [...prev.slice(-19), newPoint];
        console.log("UPDATED HISTORY", updated);
        return updated;
      });

    } catch (err) {
      console.error("❌ [API Error]", err.message);
      setError("Backend Offline. Ensure FastAPI runs at http://127.0.0.1:8000");
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * fetchLiveData — polls backend for live telemetry
   * 
   * PRIORITY ORDER:
   *   1. GET /latest — real ESP32 hardware data (if ESP32 is connected)
   *   2. GET /live-data — simulation fallback (if no ESP32)
   * 
   * This creates a seamless pipeline:
   *   ESP32 connected → dashboard shows real hardware data
   *   ESP32 absent → dashboard shows simulated drift
   */
  const fetchLiveData = useCallback(async () => {
    setError(null);
    try {
      // First, try to get real ESP32 data from /latest
      const latestResponse = await api.get('/latest');
      const latestData = latestResponse.data;

      let data;
      if (latestData.status === 'waiting_for_esp32') {
        // No ESP32 connected — fall back to simulation
        const simResponse = await api.get('/live-data');
        data = simResponse.data;
        console.log("LIVE TELEMETRY (SIMULATION)", data);
      } else {
        // Real ESP32 data available!
        data = latestData;
        console.log("LIVE ESP32 DATA", data);
      }

      // Map backend field names back to frontend state keys
      const updatedTelemetry = {
        voltage: data.voltage,
        current: data.current,
        temperature: data.temperature,
        battery_percentage: data.battery_percentage,
        humidity: data.humidity,
        cycle: data.cycle_num,
        capacity: data.capacity_ah,
      };

      // Sync sliders + prediction cards simultaneously
      setTelemetry(updatedTelemetry);
      setPredictionData(data);

      // Build complete history snapshot
      const newPoint = {
        time: new Date().toLocaleTimeString(),
        voltage: data.voltage,
        current: data.current,
        temperature: data.temperature,
        battery_percentage: data.battery_percentage,
        humidity: data.humidity,
        cycle: data.cycle_num,
        capacity: data.capacity_ah,
        soh_prediction: data.soh_prediction,
        degradation_percentage: data.degradation_percentage,
        estimated_rul: data.estimated_rul,
      };

      console.log("NEW HISTORY POINT", newPoint);

      setHistory(prev => {
        const updated = [...prev.slice(-19), newPoint];
        console.log("UPDATED HISTORY", updated);
        return updated;
      });

    } catch (err) {
      console.error("❌ Live Feed Error:", err.message);
      setError("Live Feed Disconnected. Check backend.");
      setIsLive(false);
    }
  }, []);

  // ═══════════════════════════════════════════════════════════
  // 3. EFFECTS — controls when API calls fire
  // ═══════════════════════════════════════════════════════════

  // (A) Initial fetch on mount — runs exactly once
  useEffect(() => {
    if (!initialFetchDone.current) {
      initialFetchDone.current = true;
      fetchPrediction(telemetry);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // (B) Live mode polling loop — 2 second interval
  useEffect(() => {
    if (!isLive) return;
    const id = setInterval(fetchLiveData, 2000);
    return () => clearInterval(id);
  }, [isLive, fetchLiveData]);

  // ═══════════════════════════════════════════════════════════
  // 4. SLIDER HANDLER — debounced 300ms
  // ═══════════════════════════════════════════════════════════

  /**
   * handleInputChange — called by TelemetryControl on every slider drag
   * 
   * Flow:
   *   1. Immediately update telemetry state (slider moves visually)
   *   2. Clear any pending debounce timer
   *   3. Set new 300ms timer to call fetchPrediction
   *   4. When timer fires, backend receives new telemetry
   *   5. Response updates predictionData + history
   *   6. React rerenders gauges, charts, monitor, etc.
   */
  const handleInputChange = (field, value) => {
    if (isLive) return; // sliders locked during live mode

    const newTelemetry = { ...telemetry, [field]: parseFloat(value) };
    setTelemetry(newTelemetry);

    // Debounce: wait 300ms after user stops dragging before hitting API
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchPrediction(newTelemetry);
    }, 300);
  };

  // ═══════════════════════════════════════════════════════════
  // 5. RENDER — the dashboard
  // ═══════════════════════════════════════════════════════════

  return (
    <div className="app-container">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="header"
      >
        <div>
          <h1 className="title">
            <Zap size={40} color="white" />
            Battery<span style={{ fontWeight: 300, color: 'var(--text-muted)' }}>Dock</span>
          </h1>
          <p className="subtitle mono">
            AI Telemetry Intelligence for High-Performance EV Batteries
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {isLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '12px' }} className="mono">
              <Loader2 size={14} className="animate-spin" />
              ANALYZING TELEMETRY...
            </div>
          )}

          <button
            onClick={() => setIsLive(!isLive)}
            className={`btn-live ${isLive ? 'active' : ''}`}
          >
            <Activity size={16} className={isLive ? 'animate-pulse' : ''} />
            {isLive ? 'LIVE TELEMETRY ACTIVE' : 'START LIVE FEED'}
          </button>
        </div>
      </motion.header>

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-panel"
            style={{ borderColor: 'rgba(239, 68, 68, 0.5)', background: 'rgba(239, 68, 68, 0.1)', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px' }}
          >
            <WifiOff color="#ef4444" size={28} />
            <div>
              <h4 style={{ color: '#ef4444', fontWeight: 'bold', marginBottom: '4px', fontSize: '14px' }} className="mono">CONNECTION ERROR</h4>
              <p style={{ fontSize: '14px', color: '#fca5a5' }}>{error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Dashboard Grid */}
      <div className="grid-layout">

        {/* Left Column: Controls & Vehicle */}
        <div className="col-flex">
          <div className="glass-panel">
            <h2 className="panel-title">
              <Navigation size={20} color="var(--text-muted)" />
              Live Telemetry Input
            </h2>
            <TelemetryControl
              telemetry={telemetry}
              onChange={handleInputChange}
              disabled={isLive}
            />
          </div>

          <div className="glass-panel" style={{ flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <h3 className="vehicle-label mono">Chassis Systems</h3>
            <VehicleGraphic severity={predictionData?.battery_condition || 'Healthy'} />
            {predictionData && (
              <div style={{ position: 'absolute', bottom: '24px', left: '24px', right: '24px', display: 'flex', justifyContent: 'space-between' }}>
                <div className="vehicle-stress mono">
                  <p style={{ color: 'var(--text-muted)', fontSize: '10px' }}>CYCLE AGING</p>
                  <p className="ai-card-value text-accent" style={{ fontSize: '1.5rem' }}>
                    {telemetry.cycle}
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '4px' }}>cycles</span>
                  </p>
                </div>
                <div className="vehicle-stress mono" style={{ textAlign: 'right' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '10px' }}>CAPACITY FADE</p>
                  <p className="ai-card-value text-orange" style={{ fontSize: '1.5rem' }}>
                    {telemetry.capacity.toFixed(2)}
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '4px' }}>Ah</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: AI Intelligence & Charts */}
        <div className="col-flex">
          {predictionData && <AIIntelligence predictionData={predictionData} />}

          {/* Charts */}
          <div className="glass-panel" style={{ flex: 1 }}>
            <h2 className="panel-title">
              <Activity size={20} color="var(--text-muted)" />
              Real-Time Degradation Forecast
            </h2>
            <TrendCharts history={history} />
          </div>
        </div>
      </div>

      {/* Telemetry Monitor Section */}
      <TelemetryMonitor telemetry={telemetry} predictionData={predictionData} />

      {/* Alerts & Recommendations */}
      <AnimatePresence>
        {predictionData && (predictionData.alerts.length > 0 || predictionData.recommendations.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="alerts-grid"
          >
            {predictionData.alerts.length > 0 && (
              <div className={`glass-panel alert-box ${predictionData.battery_condition === 'Critical' ? 'critical' : ''}`}>
                <h3 className="panel-title text-red">
                  <AlertTriangle size={20} />
                  System Alerts
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {predictionData.alerts.map((alert, i) => (
                    <motion.div
                      key={`${i}-${alert}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`alert-item ${alert.toLowerCase().includes('warning') ? 'warning' : ''}`}
                    >
                      {alert}
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {predictionData.recommendations.length > 0 && (
              <div className="glass-panel">
                <h3 className="panel-title">
                  <ShieldAlert size={20} color="var(--text-muted)" />
                  AI Recommendations
                </h3>
                <div>
                  {predictionData.recommendations.map((rec, i) => (
                    <motion.div
                      key={`${i}-${rec}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.1 }}
                      className="rec-item"
                    >
                      <span className="text-green">•</span>
                      {rec}
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
