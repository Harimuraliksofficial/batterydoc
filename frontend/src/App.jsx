import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, AlertTriangle, ShieldAlert, Navigation, Zap, Loader2, WifiOff } from 'lucide-react';
import TelemetryControl from './components/TelemetryControl';
import AIIntelligence from './components/AIIntelligence';
import TrendCharts from './components/TrendCharts';
import VehicleGraphic from './components/VehicleGraphic';

// Configure Axios defaults for backend communication
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 5000, // 5 second timeout to detect offline backend
});

const App = () => {
  // --- STATE MANAGEMENT ---
  
  const [telemetry, setTelemetry] = useState({
    voltage: 4.1,
    current: 2.2,
    temperature: 31.0,
    battery_percentage: 82.0,
    humidity: 45.0,
    cycle: 120,
    capacity: 0.91
  });

  // AI Prediction State (from FastAPI)
  const [predictionData, setPredictionData] = useState(null);
  
  // History State for Recharts
  const [history, setHistory] = useState([]);
  
  // UI States
  const [isLive, setIsLive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Reference for debouncing manual slider inputs
  const timeoutRef = useRef(null);

  // --- API INTEGRATION ---

  /**
   * POSTs current manual telemetry to the FastAPI /predict endpoint.
   * Updates AI intelligence and chart history.
   */
  const fetchPrediction = async (currentTelemetry) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Map frontend state to backend expected schema
      const payload = {
        ...currentTelemetry,
        cycle_num: currentTelemetry.cycle,
        capacity_ah: currentTelemetry.capacity
      };
      
      console.log("🚀 [API] Outgoing Telemetry Payload (POST /predict):", payload);
      
      const response = await api.post('/predict', payload);
      const data = response.data;
      
      console.log("✅ [API] Backend Response Received:", data);
      
      // Update dashboard state with real intelligence
      setPredictionData(data);
      
      // 3. Append LIVE SNAPSHOT to history
      const newPoint = {
        time: new Date().toLocaleTimeString(),
        soh_prediction: data.soh_prediction,
        degradation_percentage: data.degradation_percentage,
        temperature: currentTelemetry.temperature,
        voltage: currentTelemetry.voltage,
        current: currentTelemetry.current,
      };
      
      console.log("NEW HISTORY POINT", newPoint);
      
      setHistory(prev => {
        const updatedHistory = [...prev.slice(-19), newPoint];
        console.log("FULL HISTORY", updatedHistory);
        return updatedHistory;
      });
      
    } catch (err) {
      console.error("❌ [API Error] Failed to fetch prediction:", err.message);
      setError("Backend Offline or Timeout. Ensure FastAPI is running at http://127.0.0.1:8000.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * GETs live simulated hardware telemetry from FastAPI /live-data endpoint.
   * Completely replaces local fake math with actual backend stream.
   */
  const fetchLiveData = async () => {
    setError(null);
    try {
      console.log("📡 [API] Polling Live Telemetry Feed (GET /live-data)...");
      const response = await api.get('/live-data');
      const data = response.data;
      
      console.log("✅ [API] Live Feed Received:", data);

      const updatedTelemetry = {
        voltage: data.voltage,
        current: data.current,
        temperature: data.temperature,
        battery_percentage: data.battery_percentage,
        humidity: data.humidity,
        cycle: data.cycle_num,
        capacity: data.capacity_ah
      };
      
      // 2. Synchronize UI sliders and AI intelligence cards concurrently
      setTelemetry(updatedTelemetry);
      setPredictionData(data);
      
      // 3. Push real-time data to charts
      const newPoint = {
        time: new Date().toLocaleTimeString(),
        soh_prediction: data.soh_prediction,
        degradation_percentage: data.degradation_percentage,
        temperature: updatedTelemetry.temperature,
        voltage: updatedTelemetry.voltage,
        current: updatedTelemetry.current,
      };
      
      console.log("NEW HISTORY POINT", newPoint);
      
      setHistory(prev => {
        const updatedHistory = [...prev.slice(-19), newPoint];
        console.log("FULL HISTORY", updatedHistory);
        return updatedHistory;
      });

    } catch (err) {
      console.error("❌ [API Error] Live Feed Disconnected:", err.message);
      setError("Live Feed Disconnected. Check backend connection.");
      setIsLive(false); // Auto-disable live mode on crash
    }
  };

  // --- REACT HOOKS (USE EFFECT) ---

  // Initial load: Fetch baseline prediction on mount
  useEffect(() => {
    fetchPrediction(telemetry);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync Telemetry Changes to Backend (Debounced)
  useEffect(() => {
    // Skip if in live mode (live mode handles its own polling)
    if (isLive) return;

    // Debounce the API call by 300ms to prevent overwhelming the server
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      fetchPrediction(telemetry);
    }, 300);

    return () => clearTimeout(timeoutRef.current);
  }, [telemetry, isLive]);

  // Live Telemetry Polling Loop
  useEffect(() => {
    let intervalId;
    if (isLive) {
      // Poll the backend every 1.5 seconds if LIVE mode is active
      intervalId = setInterval(() => {
        fetchLiveData();
      }, 1500);
    }
    // Cleanup interval when component unmounts or live mode is toggled off
    return () => clearInterval(intervalId);
  }, [isLive]);

  /**
   * Handle manual slider inputs
   * State update triggers the useEffect above to fetch new predictions
   */
  const handleInputChange = (field, value) => {
    setTelemetry(prev => ({ ...prev, [field]: parseFloat(value) }));
  };

  const getSeverityColor = (severity) => {
    if (severity === 'Critical') return 'text-red';
    if (severity === 'Warning') return 'text-orange';
    if (severity === 'Monitor') return 'text-yellow';
    return 'text-green';
  };

  return (
    <div className="app-container">
      {/* Premium Landing Hero Section */}
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
          {/* Loading State Indicator */}
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
                    <p className="ai-card-value text-accent">
                      {telemetry.cycle}
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '4px' }}>cycles</span>
                    </p>
                 </div>
                 <div className="vehicle-stress mono" style={{ textAlign: 'right' }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '10px' }}>CAPACITY FADE</p>
                    <p className="ai-card-value text-orange">
                      {telemetry.capacity.toFixed(2)}
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '4px' }}>Ah</span>
                    </p>
                 </div>
               </div>
             )}
          </div>
        </div>

        {/* Middle Column: AI Intelligence & Trends */}
        <div className="col-flex">
          {predictionData && <AIIntelligence predictionData={predictionData} />}
          
          {/* Recharts Visualization */}
          <div className="glass-panel" style={{ flex: 1 }}>
             <h2 className="panel-title">
              <Activity size={20} color="var(--text-muted)" />
              Real-Time Degradation Forecast
            </h2>
            <TrendCharts history={history} />
          </div>
        </div>
      </div>

      {/* Alerts & Recommendations Bottom Section */}
      <AnimatePresence>
        {predictionData && (predictionData.alerts.length > 0 || predictionData.recommendations.length > 0) && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="alerts-grid"
          >
            {/* Alerts */}
            {predictionData.alerts.length > 0 && (
              <div className={`glass-panel alert-box ${predictionData.battery_condition === 'Critical' ? 'critical' : ''}`}>
                <h3 className="panel-title text-red">
                  <AlertTriangle size={20} />
                  System Alerts
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {predictionData.alerts.map((alert, i) => (
                    <motion.div 
                      key={i}
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

            {/* Recommendations */}
            {predictionData.recommendations.length > 0 && (
              <div className="glass-panel">
                <h3 className="panel-title">
                  <ShieldAlert size={20} color="var(--text-muted)" />
                  AI Recommendations
                </h3>
                <div>
                  {predictionData.recommendations.map((rec, i) => (
                    <motion.div 
                      key={i}
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
