import React, { useState, useMemo, useEffect } from 'react';
import {
  Database,
  Plane, AlertTriangle, CheckCircle, Clock, Search,
  ArrowRight, ShieldCheck, Activity, Target, BrainCircuit,
  TrendingUp, TrendingDown, Bell, Zap, Calendar, Wrench, Menu, X, Cpu
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Link } from 'react-router-dom';
import './index.css';

// Time-series data is now fetched from the backend.

// Utility for formatting
const formatNum = (num, decimals = 2) => (num === -1 || num === '' || num == null) ? 'N/A' : Number(num).toFixed(decimals);
const getStatusColor = (val, type) => {
  if (val === -1 || val == null) return 'var(--text-light)';
  if (type === 'health') return val > 80 ? 'var(--text-teal)' : val > 50 ? 'var(--accent-copper)' : 'var(--text-error)';
  if (type === 'risk') return val < 0.2 ? 'var(--text-teal)' : val < 0.6 ? 'var(--accent-copper)' : 'var(--text-error)';
  return 'var(--text-main)';
};

function CustomGauge({ percentage, label }) {
  const dashArray = 251.2;
  const dashOffset = dashArray - (dashArray * percentage) / 100;
  return (
    <div style={{ position: 'relative', width: '160px', height: '160px', margin: '0 auto' }}>
      <svg width="160" height="160" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="transparent" stroke="var(--bg-card)" strokeWidth="8" />
        <circle 
          cx="50" cy="50" r="40" fill="transparent" 
          stroke={percentage > 80 ? 'var(--accent-teal)' : percentage > 50 ? 'var(--accent-copper)' : 'var(--text-error)'} 
          strokeWidth="8" 
          strokeDasharray={dashArray} 
          strokeDashoffset={dashOffset} 
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--text-main)', display: 'block', lineHeight: 1 }}>{percentage}%</span>
        {label && <span style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: '0.25rem' }}>{label}</span>}
      </div>
    </div>
  );
}

function MissionIntelligence() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // --- API state ---
  const [fleetData, setFleetData] = useState([]);
  const [apiLoading, setApiLoading] = useState(true);
  const [apiError, setApiError] = useState(null);

  const [timeSeriesData, setTimeSeriesData] = useState({});
  const [tsLoading, setTsLoading] = useState(false);
  const [tsError, setTsError] = useState(null);

  useEffect(() => {
    if (!selectedAssetId) return;
    if (timeSeriesData[selectedAssetId]) return; // Already cached

    setTsLoading(true);
    setTsError(null);
    fetch(`/api/assets/${selectedAssetId}/timeseries`)
      .then(res => {
        if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
        return res.json();
      })
      .then(data => {
        setTimeSeriesData(prev => ({ ...prev, [selectedAssetId]: data }));
        setTsLoading(false);
      })
      .catch(err => {
        setTsError(err.message);
        setTsLoading(false);
      });
  }, [selectedAssetId, timeSeriesData]);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Fetch real fleet readiness from backend on mount
  useEffect(() => {
    setApiLoading(true);
    setApiError(null);
    fetch('/api/readiness')
      .then(res => {
        if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
        return res.json();
      })
      .then(data => {
        setFleetData(data);
        setApiLoading(false);
      })
      .catch(err => {
        setApiError(err.message);
        setApiLoading(false);
      });
  }, []);

  // Set default selection once data arrives
  useEffect(() => {
    if (fleetData.length > 0 && !selectedAssetId) {
      const demoTarget =
        fleetData.find(d => d.readiness_status === 'NOT_READY') ||
        fleetData.find(d => d.readiness_status === 'ADVISORY') ||
        fleetData[0];
      setSelectedAssetId(demoTarget.asset_id);
    }
  }, [fleetData, selectedAssetId]);

  // KPIs — derived from readiness_status returned by the backend engine
  const totalAssets = fleetData.length;
  const readyAssets    = fleetData.filter(d => d.readiness_status === 'READY');
  const atRiskAssets   = fleetData.filter(d => d.readiness_status === 'ADVISORY');
  const maintenanceAssets = fleetData.filter(d => d.readiness_status === 'NOT_READY');

  const filteredAssets = useMemo(() => {
    return fleetData.filter(a => String(a.asset_id).toLowerCase().includes(searchTerm.toLowerCase()));
  }, [searchTerm, fleetData]);

  const selectedAsset = useMemo(() => fleetData.find(a => a.asset_id === selectedAssetId), [selectedAssetId, fleetData]);
  
  // Prepare Time Series Data
  const selectedTimeSeries = useMemo(() => {
    if (!selectedAssetId || !timeSeriesData[selectedAssetId]) return [];
    return timeSeriesData[selectedAssetId].map(d => ({
      cycle: d.cycle,
      health: d.health_score !== -1 ? Number(formatNum(d.health_score)) : null,
      risk: d.failure_probability !== -1 ? Number(formatNum(d.failure_probability * 100)) : null
    })).slice(-50); // Show last 50 cycles
  }, [selectedAssetId, timeSeriesData]);

  // Prepare Condition Change (Current vs Previous)
  const conditionChange = useMemo(() => {
    if (!selectedAssetId || !timeSeriesData[selectedAssetId]) return null;
    const history = timeSeriesData[selectedAssetId];
    if (history.length < 2) return null;
    const current = history[history.length - 1];
    const prev = history[history.length - 10] || history[0]; // compare with 10 cycles ago if possible
    
    return {
      healthChange: current.health_score - prev.health_score,
      riskChange: current.failure_probability - prev.failure_probability,
      rulChange: (current.predicted_rul === -1 || prev.predicted_rul === -1) ? 0 : current.predicted_rul - prev.predicted_rul
    };
  }, [selectedAssetId, timeSeriesData]);

  const generateRiskExplanation = (asset) => {
    if (!asset) return "";
    let reasons = [];
    if (asset.failure_probability > 0.7) reasons.push("a stark increase in structural failure probability");
    else if (asset.failure_probability > 0.3) reasons.push("elevated failure probability indices");

    if (asset.anomaly_score > 0.5) reasons.push("recent abnormal sensor readings");
    
    if (asset.predicted_rul !== -1 && asset.predicted_rul < 50) reasons.push("a rapidly decreasing Remaining Useful Life (RUL)");

    if (reasons.length === 0) return "All subsystems are currently reporting nominal readings. Continue standard operational monitoring.";
    return `Risk is elevated due to ${reasons.join(" and ")} across monitored subsystems.`;
  };

  // Maintenance Priority ranking — use maintenance_priority_score from the backend
  const priorityList = useMemo(() => {
    return [...fleetData]
      .sort((a, b) => (b.maintenance_priority_score ?? 0) - (a.maintenance_priority_score ?? 0))
      .slice(0, 5);
  }, [fleetData]);

  // Loading state
  if (apiLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem', background: 'var(--bg-main)' }}>
        <Activity size={40} style={{ color: 'var(--accent-teal)', animation: 'spin 1s linear infinite' }} />
        <p style={{ color: 'var(--text-light)', fontSize: '1.1rem' }}>Loading fleet readiness data…</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Error state
  if (apiError) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem', background: 'var(--bg-main)', padding: '2rem' }}>
        <AlertTriangle size={40} style={{ color: 'var(--text-error)' }} />
        <p style={{ color: 'var(--text-main)', fontSize: '1.1rem', fontWeight: 600 }}>Failed to load readiness data</p>
        <p style={{ color: 'var(--text-light)', fontSize: '0.9rem', maxWidth: '480px', textAlign: 'center' }}>
          {apiError}
        </p>
        <p style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>
          Make sure the backend is running: <code>uvicorn src.api.main:app --port 8000</code>
        </p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
      <div className="app bg-surface" style={{ minHeight: '100vh', paddingBottom: '4rem' }}>
      {/* Navigation */}
      <nav className={`navbar ${isScrolled ? 'scrolled' : ''}`} style={{ background: isScrolled ? 'rgba(255, 255, 255, 0.9)' : 'var(--bg-main)' }}>
        <div className="container navbar-content">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
            <Plane className="text-teal" size={28} />
            <span>Astra<span className="text-copper">Pulse</span></span>
          </Link>
          <div className="nav-links" style={{ display: 'flex', gap: '2rem' }}>
            <span className="nav-link" style={{ fontWeight: 600 }}>Mission Intelligence</span>
            <Link to="/sensor-assessment" className="nav-link">Sensor Assessment</Link>
          </div>
          <div className="nav-actions" style={{ display: 'flex', gap: '0.75rem' }}>
            <Link to="/sensor-assessment" className="btn btn-primary" style={{ padding: '0.6rem 1.25rem', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              <Cpu size={16} /> Assess New Asset
            </Link>
            <Link to="/" className="btn btn-secondary" style={{ padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}>Back to Home</Link>
          </div>
        </div>
      </nav>

      <div className="container" style={{ paddingTop: '8rem' }}>
        
        {/* HERO / SUMMARY */}
        <div style={{ marginBottom: '3rem', animation: 'fade-in 0.8s ease' }}>
          <h1 className="hero-title" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Mission Intelligence</h1>
          <p className="hero-description" style={{ fontSize: '1.1rem', margin: 0, opacity: 0.8 }}>Turn predictive signals into clear readiness decisions.</p>
        </div>

        {/* Global KPIs */}
        <div className="grid-features" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', marginBottom: '3rem' }}>
          <div className="feature-card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-light)' }}>
              <Database size={20} /> Total Assets
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-main)' }}>{totalAssets}</div>
          </div>
          <div className="feature-card" style={{ padding: '1.5rem', borderBottom: '4px solid var(--accent-teal)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--accent-teal)' }}>
              <ShieldCheck size={20} /> Mission Ready
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-main)' }}>{readyAssets.length}</div>
          </div>
          <div className="feature-card" style={{ padding: '1.5rem', borderBottom: '4px solid var(--accent-copper)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--accent-copper)' }}>
              <AlertTriangle size={20} /> At Risk
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-main)' }}>{atRiskAssets.length}</div>
          </div>
          <div className="feature-card" style={{ padding: '1.5rem', borderBottom: '4px solid var(--text-error)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-error)' }}>
              <Wrench size={20} /> Maintenance Required
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-main)' }}>{maintenanceAssets.length}</div>
          </div>
        </div>

        {/* FLEET READINESS */}
        <section className="feature-card" style={{ padding: '2rem', marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={24} className="text-teal" /> Fleet Readiness Overview
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3rem', alignItems: 'center' }}>
            <CustomGauge percentage={Math.round((readyAssets.length / totalAssets) * 100)} label="Readiness" />
            <div style={{ flex: 1, minWidth: '300px' }}>
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <span style={{ fontWeight: 600 }}>Distribution:</span>
              </div>
              <div style={{ display: 'flex', height: '24px', borderRadius: '12px', overflow: 'hidden', backgroundColor: 'var(--bg-main)' }}>
                <div style={{ width: `${(readyAssets.length/totalAssets)*100}%`, backgroundColor: 'var(--accent-teal)', transition: 'width 1s ease' }}></div>
                <div style={{ width: `${(atRiskAssets.length/totalAssets)*100}%`, backgroundColor: 'var(--accent-copper)', transition: 'width 1s ease' }}></div>
                <div style={{ width: `${(maintenanceAssets.length/totalAssets)*100}%`, backgroundColor: 'var(--text-error)', transition: 'width 1s ease' }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', fontSize: '0.875rem', color: 'var(--text-light)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-teal)' }}></span> Ready ({readyAssets.length})</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-copper)' }}></span> At Risk ({atRiskAssets.length})</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--text-error)' }}></span> Maint. ({maintenanceAssets.length})</span>
              </div>
            </div>
          </div>
        </section>

        {/* TWO COLUMN LAYOUT FOR TABLE AND DETAILS */}
        <div style={{ display: 'grid', gridTemplateColumns: 'revert', gap: '2rem' }} className="grid-responsive-layout">
          <style dangerouslySetInnerHTML={{__html:`
            .grid-responsive-layout { grid-template-columns: 2fr 1fr; }
            @media (max-width: 1024px) {
              .grid-responsive-layout { grid-template-columns: 1fr; }
            }
            .table-container { overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; text-align: left; }
            th, td { padding: 1rem; border-bottom: 1px solid rgba(0,0,0,0.05); }
            th { color: var(--text-light); font-weight: 500; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; }
            tr { cursor: pointer; transition: background 0.2s; }
            tr:hover { background: rgba(0,0,0,0.02); }
            tr.selected { background: rgba(91, 155, 152, 0.08); }
          `}} />
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* ASSET HEALTH TABLE */}
            <section className="feature-card" style={{ padding: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Asset Health</h2>
                <div style={{ position: 'relative' }}>
                  <Search size={16} style={{ position: 'absolute', top: '50%', left: '1rem', transform: 'translateY(-50%)', color: 'var(--text-light)' }} />
                  <input 
                    type="text" 
                    placeholder="Search asset..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{ padding: '0.75rem 1rem 0.75rem 2.5rem', borderRadius: '2rem', border: '1px solid rgba(0,0,0,0.1)', background: 'var(--bg-main)', width: '250px', outline: 'none' }}
                  />
                </div>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>Health Score</th>
                      <th>Failure Risk</th>
                      <th>Pred RUL</th>
                      <th>Status</th>
                      <th>Next Mission</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAssets.slice(0, 10).map(asset => (
                      <tr key={asset.asset_id} className={selectedAssetId === asset.asset_id ? 'selected' : ''} onClick={() => setSelectedAssetId(asset.asset_id)}>
                        <td style={{ fontWeight: 600 }}>{asset.asset_id}</td>
                        <td style={{ color: getStatusColor(asset.health_score, 'health') }}>{formatNum(asset.health_score, 1)}</td>
                        <td style={{ color: getStatusColor(asset.failure_probability, 'risk') }}>{asset.failure_probability !== -1 ? (asset.failure_probability * 100).toFixed(1)+'%' : 'N/A'}</td>
                        <td>{asset.predicted_rul === -1 ? 'N/A' : Math.round(asset.predicted_rul)}</td>
                        <td>
                          {asset.failure_probability > 0.7 || asset.health_score < 40 ? <span style={{ color: 'var(--text-error)', fontWeight: 600 }}>CRITICAL</span> : 
                           asset.failure_probability > 0.3 || asset.health_score < 70 ? <span style={{ color: 'var(--accent-copper)', fontWeight: 600 }}>WARNING</span> : 
                           <span style={{ color: 'var(--text-teal)', fontWeight: 600 }}>NORMAL</span>}
                        </td>
                        <td>{asset.mission_type || 'NONE'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            
            {/* HEALTH TREND */}
            <section className="feature-card" style={{ padding: '2rem' }}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp size={20} className="text-copper" /> Health & Risk Trend ({selectedAssetId || 'None'})
              </h2>
              {tsLoading ? (
                <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ color: 'var(--text-light)' }}>Loading history...</div>
                </div>
              ) : tsError ? (
                <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ color: 'var(--text-error)' }}>Failed to load history: {tsError}</div>
                </div>
              ) : selectedTimeSeries.length > 0 ? (
                <div style={{ height: '300px', width: '100%' }}>
                  <ResponsiveContainer>
                    <LineChart data={selectedTimeSeries}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                      <XAxis dataKey="cycle" stroke="var(--text-light)" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis yAxisId="left" stroke="var(--text-teal)" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis yAxisId="right" orientation="right" stroke="var(--accent-copper)" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip 
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                        formatter={(value, name) => [typeof value === 'number' ? value.toFixed(2) : value, name]}
                      />
                      <Legend iconType="circle" wrapperStyle={{ paddingTop: '1rem' }} />
                      <Line yAxisId="left" type="monotone" dataKey="health" name="Health Score" stroke="var(--text-teal)" strokeWidth={3} dot={false} />
                      <Line yAxisId="right" type="monotone" dataKey="risk" name="Failure Risk (%)" stroke="var(--accent-copper)" strokeWidth={3} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-light)' }}>
                  No trend data available.
                </div>
              )}
            </section>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* ASSET DETAIL / WHY AT RISK */}
            {selectedAsset && (
              <section className="feature-card" style={{ padding: '2rem', background: 'linear-gradient(145deg, #ffffff, var(--bg-main))' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Asset Details</h2>
                  <span className="badge" style={{ background: 'var(--text-teal)', color: 'white' }}>{selectedAsset.asset_id}</span>
                </div>
                
                <h3 style={{ fontSize: '1rem', color: 'var(--accent-copper)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <BrainCircuit size={18} /> Why is this asset at risk?
                </h3>
                <p style={{ fontSize: '0.95rem', lineHeight: 1.6, color: 'var(--text-main)', marginBottom: '1.5rem', padding: '1rem', background: 'rgba(201, 114, 93, 0.05)', borderRadius: '8px', borderLeft: '4px solid var(--accent-copper)' }}>
                  {generateRiskExplanation(selectedAsset)}
                </p>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'uppercase' }}>Health Score</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{formatNum(selectedAsset.health_score, 1)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'uppercase' }}>Anomaly Score</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{formatNum(selectedAsset.anomaly_score, 3)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'uppercase' }}>Failure Prob.</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{selectedAsset.failure_probability !== -1 ? (selectedAsset.failure_probability * 100).toFixed(2)+'%' : 'N/A'}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'uppercase' }}>Predicted RUL</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{selectedAsset.predicted_rul !== -1 ? Math.round(selectedAsset.predicted_rul) + ' cyc' : 'N/A'}</div>
                  </div>
                </div>

                <div style={{ paddingTop: '1rem', borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Calendar size={16} className="text-teal" /> Upcoming Mission
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600 }}>{selectedAsset.mission_type || 'No scheduled mission'}</div>
                  {selectedAsset.mission_date && <div style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>{selectedAsset.mission_date} • Criticality: {selectedAsset.mission_criticality}</div>}
                </div>
              </section>
            )}

            {/* CONDITION CHANGE */}
            {conditionChange && (
              <section className="feature-card" style={{ padding: '2rem' }}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Zap size={20} className="text-copper" /> Condition Change
                </h2>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-light)', marginBottom: '1rem' }}>Last 10 cycles assessment</div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                    <span style={{ fontWeight: 500 }}>Health Change</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: conditionChange.healthChange < 0 ? 'var(--text-error)' : 'var(--text-teal)', fontWeight: 600 }}>
                      {conditionChange.healthChange < 0 ? <TrendingDown size={16} /> : <TrendingUp size={16} />}
                      {Math.abs(conditionChange.healthChange).toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
                    <span style={{ fontWeight: 500 }}>Risk Change</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: conditionChange.riskChange > 0 ? 'var(--text-error)' : 'var(--text-teal)', fontWeight: 600 }}>
                      {conditionChange.riskChange > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                      {(Math.abs(conditionChange.riskChange)*100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 500 }}>RUL Decrease</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--accent-copper)', fontWeight: 600 }}>
                      <TrendingDown size={16} />
                      {Math.abs(conditionChange.rulChange).toFixed(0)} cyc
                    </span>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>

        {/* MAINTENANCE PRIORITY */}
        <section className="feature-card" style={{ padding: '2rem', marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Target size={24} className="text-error" /> Maintenance Priority
          </h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Asset</th>
                  <th>Risk</th>
                  <th>RUL</th>
                  <th>Next Mission</th>
                  <th>Recommended Action</th>
                </tr>
              </thead>
              <tbody>
                {priorityList.map((asset, index) => (
                  <tr key={asset.asset_id}>
                    <td>
                      <span className="badge" style={{ background: index === 0 ? 'var(--text-error)' : index < 3 ? 'var(--accent-copper)' : 'var(--bg-card)', color: index < 3 ? 'white' : 'var(--text-main)', border: index >= 3 ? '1px solid rgba(0,0,0,0.1)' : 'none' }}>
                        #{index + 1}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{asset.asset_id}</td>
                    <td style={{ color: getStatusColor(asset.failure_probability, 'risk') }}>{asset.failure_probability !== -1 ? (asset.failure_probability * 100).toFixed(1)+'%' : 'N/A'}</td>
                    <td>{asset.predicted_rul !== -1 ? Math.round(asset.predicted_rul) : 'N/A'}</td>
                    <td>{asset.mission_type || 'N/A'}</td>
                    <td>
                      {index === 0 ? 'Immediate Grounding & Inspection' : index < 3 ? 'Schedule Expedited Maintenance' : 'Monitor Closely'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ASSESS NEW ASSET CTA */}
        <section style={{ marginTop: '3rem', marginBottom: '0', padding: '2.5rem 2rem', background: 'linear-gradient(135deg, rgba(91,155,152,0.06) 0%, var(--bg-surface) 100%)', borderRadius: '1.5rem', border: '1px solid rgba(91,155,152,0.2)', display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <Cpu size={20} style={{ color: 'var(--accent-teal)' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>Assess a New Asset</h3>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', maxWidth: '480px', margin: 0 }}>
              Upload unseen sensor history and run Health, Failure-Risk and RUL inference on an asset not in the fleet registry.
            </p>
          </div>
          <Link to="/sensor-assessment" className="btn btn-primary" style={{ whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
            Assess New Asset <ArrowRight size={18} />
          </Link>
        </section>

        {/* COPILOT CTA */}
        <section style={{ marginTop: '2rem', marginBottom: '2rem', textAlign: 'center', padding: '4rem 2rem', background: 'linear-gradient(135deg, var(--bg-main) 0%, rgba(91, 155, 152, 0.1) 100%)', borderRadius: '2rem', border: '1px solid rgba(91, 155, 152, 0.2)' }}>
          <h2 style={{ fontSize: '2rem', marginBottom: '1rem', color: 'var(--text-main)' }}>Need a deeper answer?</h2>
          <p style={{ fontSize: '1.1rem', color: 'var(--text-light)', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
            Interact with our IBM Bob/MCP-powered Copilot to trace AI rationale to the raw sensor data and maintenance logs.
          </p>
          <button className="btn btn-primary" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>
            Ask Mission Copilot <ArrowRight size={20} />
          </button>
        </section>

      </div>
    </div>
  );
}

export default MissionIntelligence;
