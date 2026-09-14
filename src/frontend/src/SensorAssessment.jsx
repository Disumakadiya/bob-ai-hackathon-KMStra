import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Plane, ArrowRight, ArrowLeft, Upload, X, FileText,
  Activity, ShieldCheck, AlertTriangle, Cpu, BrainCircuit,
  TrendingUp, Download, Info, CheckCircle,
  Zap, Target, RefreshCw, PenLine, Plus, Trash2
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine
} from 'recharts';
import { Link } from 'react-router-dom';
import './index.css';

// ---------------------------------------------------------------------------
// Schema — exact backend columns (cleaned 19-col format, lowercase for API)
// ---------------------------------------------------------------------------
const SAMPLE_CSV_COLS = [
  'unit','cycle','op1','op2',
  'S2','S3','S4','S6','S7','S8','S9',
  'S11','S12','S13','S14','S15','S17','S20','S21'
];

// Sensor/op fields a user enters per cycle (excludes unit & cycle)
const MANUAL_FIELDS = [
  { key: 'op1',  label: 'OP1',  placeholder: '0.0000',  title: 'Operational Setting 1' },
  { key: 'op2',  label: 'OP2',  placeholder: '0.0003',  title: 'Operational Setting 2' },
  { key: 's2',   label: 'S2',   placeholder: '642.0',   title: 'Sensor 2' },
  { key: 's3',   label: 'S3',   placeholder: '1585.0',  title: 'Sensor 3' },
  { key: 's4',   label: 'S4',   placeholder: '1405.0',  title: 'Sensor 4' },
  { key: 's6',   label: 'S6',   placeholder: '21.61',   title: 'Sensor 6' },
  { key: 's7',   label: 'S7',   placeholder: '554.4',   title: 'Sensor 7' },
  { key: 's8',   label: 'S8',   placeholder: '2388.1',  title: 'Sensor 8' },
  { key: 's9',   label: 'S9',   placeholder: '9062.0',  title: 'Sensor 9' },
  { key: 's11',  label: 'S11',  placeholder: '47.28',   title: 'Sensor 11' },
  { key: 's12',  label: 'S12',  placeholder: '522.0',   title: 'Sensor 12' },
  { key: 's13',  label: 'S13',  placeholder: '2388.1',  title: 'Sensor 13' },
  { key: 's14',  label: 'S14',  placeholder: '8144.0',  title: 'Sensor 14' },
  { key: 's15',  label: 'S15',  placeholder: '8.38',    title: 'Sensor 15' },
  { key: 's17',  label: 'S17',  placeholder: '392.0',   title: 'Sensor 17' },
  { key: 's20',  label: 'S20',  placeholder: '38.90',   title: 'Sensor 20' },
  { key: 's21',  label: 'S21',  placeholder: '23.32',   title: 'Sensor 21' },
];

const SENSOR_GROUPS = [
  { label: 'Operational Settings', keys: ['op1', 'op2'] },
  { label: 'Sensors', keys: ['s2','s3','s4','s6','s7','s8','s9','s11','s12','s13','s14','s15','s17','s20','s21'] },
];

const ALL_SENSOR_KEYS = MANUAL_FIELDS.map(f => f.key);

/** Build a blank row — sensor fields start empty (optional) */
function emptyRow(cycle) {
  const row = { cycle: String(cycle) };
  MANUAL_FIELDS.forEach(f => { row[f.key] = ''; });
  return row;
}

/** Convert manual rows + unit into a CSV Blob — only selected sensors are included */
function buildCsvBlob(unit, rows, selectedKeys) {
  const fields = MANUAL_FIELDS.filter(f => selectedKeys.includes(f.key));
  const header = ['unit', 'cycle', ...fields.map(f => f.key)].join(',');
  const lines = rows.map(r =>
    [unit, r.cycle, ...fields.map(f => r[f.key] ?? '')].join(',')
  );
  return new Blob([[header, ...lines].join('\n')], { type: 'text/csv' });
}

function generateSampleCSV() {
  const rows = [SAMPLE_CSV_COLS.join(',')];
  const seed = (n) => ((n * 9301 + 49297) % 233280) / 233280;
  for (let cycle = 1; cycle <= 10; cycle++) {
    const r = (min, max, i) => (min + seed(cycle * 17 + i * 31) * (max - min)).toFixed(4);
    rows.push([
      1, cycle,
      r(-0.0042, 0.0042, 0), r(0.0001, 0.0005, 1),
      r(641.5, 644.0, 2), r(1582.0, 1590.0, 3), r(1402.0, 1410.0, 4),
      r(21.55, 21.62, 5), r(554.0, 556.0, 6), r(2388.0, 2392.0, 7),
      r(9060.0, 9065.0, 8), r(47.10, 47.50, 9), r(521.5, 523.5, 10),
      r(2388.0, 2392.0, 11), r(8140.0, 8150.0, 12), r(8.32, 8.50, 13),
      r(391.0, 393.0, 14), r(38.82, 39.02, 15), r(23.15, 23.45, 16)
    ].join(','));
  }
  return rows.join('\n');
}

// ---------------------------------------------------------------------------
// Readiness derivation — mirrors MissionIntelligence thresholds
// ---------------------------------------------------------------------------
function deriveReadiness(result) {
  if (!result) return null;
  const { health_score, failure_probability, predicted_rul_cycles } = result;
  if (
    health_score < 40 ||
    failure_probability > 0.7 ||
    (predicted_rul_cycles !== undefined && predicted_rul_cycles < 20)
  ) {
    return { label: 'NOT READY', color: '#e54f4f', bg: 'rgba(229,79,79,0.08)', border: '#e54f4f', icon: 'error' };
  }
  if (
    health_score < 70 ||
    failure_probability > 0.3 ||
    (predicted_rul_cycles !== undefined && predicted_rul_cycles < 50)
  ) {
    return { label: 'AT RISK', color: '#C9725D', bg: 'rgba(201,114,93,0.08)', border: '#C9725D', icon: 'warn' };
  }
  return { label: 'MISSION READY', color: '#5B9B98', bg: 'rgba(91,155,152,0.08)', border: '#5B9B98', icon: 'ok' };
}

// ---------------------------------------------------------------------------
// Risk explanation — only from actual model outputs
// ---------------------------------------------------------------------------
function buildRiskExplanation(result) {
  if (!result) return '';
  const reasons = [];
  if (result.failure_probability > 0.7)
    reasons.push('very high estimated failure probability (' + (result.failure_probability * 100).toFixed(1) + '%)');
  else if (result.failure_probability > 0.3)
    reasons.push('elevated failure probability (' + (result.failure_probability * 100).toFixed(1) + '%)');
  if (result.anomaly_score > 0.5)
    reasons.push('anomaly score above normal threshold (' + result.anomaly_score.toFixed(4) + ')');
  if (result.predicted_rul_cycles < 20)
    reasons.push('critically low predicted RUL (' + result.predicted_rul_cycles + ' cycles remaining)');
  else if (result.predicted_rul_cycles < 50)
    reasons.push('reduced predicted RUL (' + result.predicted_rul_cycles + ' cycles remaining)');
  if (result.health_score < 40)
    reasons.push('health score in critical range (' + result.health_score.toFixed(1) + '/100)');
  else if (result.health_score < 70)
    reasons.push('health score below nominal (' + result.health_score.toFixed(1) + '/100)');

  if (reasons.length === 0)
    return 'All monitored indicators are within nominal operating bounds. Continue standard operational monitoring.';
  return 'Risk is elevated based on ' + reasons.join(', ') + '. These are model-derived signals; detailed physical root-cause analysis requires additional inspection data.';
}

// ---------------------------------------------------------------------------
// Bob context builder
// ---------------------------------------------------------------------------
function buildBobContext(results, allCycles) {
  if (!results) return '';
  const arr = Array.isArray(results) ? results : [results];
  const lines = arr.map(r => {
    const rd = deriveReadiness(r);
    return (
      `Unit ${r.unit} (cycle ${r.cycle}): ` +
      `Health=${r.health_score.toFixed(1)}/100 (${r.health_status}), ` +
      `Failure probability=${(r.failure_probability * 100).toFixed(2)}% (${r.failure_status}), ` +
      `Predicted RUL=${r.predicted_rul_cycles} cycles, ` +
      `Anomaly score=${r.anomaly_score.toFixed(4)}, ` +
      `Readiness=${rd ? rd.label : 'UNKNOWN'}`
    );
  });
  const allCycleInfo = allCycles && allCycles.length > 0
    ? `\nFull cycle history spans ${allCycles.length} cycles (${allCycles[0].cycle}–${allCycles[allCycles.length - 1].cycle}).`
    : '';
  return (
    'UNSEEN ASSET SENSOR ASSESSMENT\n' +
    'Assessment generated by AstraPulse using trained IsolationForest (health), XGBoost (failure), and RandomForest (RUL) models.\n\n' +
    lines.join('\n') +
    allCycleInfo +
    '\n\nPlease explain what these model outputs mean for mission readiness, what maintenance actions may be appropriate, and what limitations apply to this inference.'
  );
}

// ---------------------------------------------------------------------------
// Mini metric card
// ---------------------------------------------------------------------------
function MetricCard({ label, value, sub, color, icon: Icon, accent }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-light)',
      borderRadius: '1rem',
      padding: '1.25rem 1.5rem',
      borderTop: `3px solid ${accent || 'var(--accent-teal)'}`,
      boxShadow: 'var(--shadow-subtle)',
      display: 'flex', flexDirection: 'column', gap: '0.5rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
        {Icon && <Icon size={14} />}{label}
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: color || 'var(--text-main)', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function SensorAssessment() {
  const [isScrolled, setIsScrolled] = useState(false);
  // --- mode: 'upload' | 'manual' ---
  const [mode, setMode] = useState('upload');
  // --- upload state ---
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  // --- manual entry state ---
  const [manualUnit, setManualUnit] = useState('1');
  const [manualRows, setManualRows] = useState(
    Array.from({ length: 5 }, (_, i) => emptyRow(i + 1))
  );
  const [selectedSensors, setSelectedSensors] = useState(() => [...ALL_SENSOR_KEYS]);
  // --- shared state ---
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [allCycles, setAllCycles] = useState([]);
  const [showBobModal, setShowBobModal] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Build chart data from results when we have all cycle data
  // allCycles is populated from the raw parsed CSV (client-side) for trend charts
  const handleFile = useCallback((f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setError('Only CSV files are accepted.');
      return;
    }
    setFile(f);
    setError(null);
    setResults(null);
    setAllCycles([]);

    // Parse locally for charting (no RUL column)
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target.result;
        const lines = text.trim().split('\n');
        if (lines.length < 2) return;
        const header = lines[0].split(',').map(c => c.trim().toLowerCase());
        const cycleIdx = header.indexOf('cycle');
        if (cycleIdx === -1) return;
        const parsed = lines.slice(1).map(line => {
          const cols = line.split(',');
          const row = {};
          header.forEach((h, i) => { row[h] = cols[i] !== undefined ? cols[i].trim() : ''; });
          return row;
        }).filter(r => r.cycle !== '' && !isNaN(Number(r.cycle)));
        setAllCycles(parsed);
      } catch { /* ignore parse errors here; backend will surface them */ }
    };
    reader.readAsText(f);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }, [handleFile]);

  const onDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = () => setIsDragging(false);

  const removeFile = () => {
    setFile(null);
    setResults(null);
    setAllCycles([]);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // --- Manual row helpers ---
  const updateManualRow = (rowIdx, fieldKey, value) => {
    setManualRows(prev => prev.map((r, i) => i === rowIdx ? { ...r, [fieldKey]: value } : r));
  };

  const addManualRow = () => {
    setManualRows(prev => [...prev, emptyRow(prev.length + 1)]);
  };

  const removeManualRow = (rowIdx) => {
    setManualRows(prev => {
      const next = prev.filter((_, i) => i !== rowIdx);
      // Re-number cycles sequentially
      return next.map((r, i) => ({ ...r, cycle: String(i + 1) }));
    });
  };

  const resetManual = () => {
    setManualRows(Array.from({ length: 5 }, (_, i) => emptyRow(i + 1)));
    setManualUnit('1');
    setSelectedSensors([...ALL_SENSOR_KEYS]);
    setResults(null);
    setAllCycles([]);
    setError(null);
  };

  // --- Shared submit helpers ---
  const _postForm = async (form) => {
    const resp = await fetch('/api/assess', { method: 'POST', body: form });
    const body = await resp.json();
    if (!resp.ok) throw new Error(body.detail || `Server error (${resp.status})`);
    return Array.isArray(body) ? body : [body];
  };

  const runAssessment = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await _postForm(form);
      setResults(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const runManualAssessment = async () => {
    // 1. Unit ID required
    const unitNum = Number(manualUnit);
    if (!manualUnit || isNaN(unitNum) || unitNum < 1) {
      setError('Unit ID must be a positive integer.');
      return;
    }

    // 2. Minimum cycles required for rolling/delta features
    if (manualRows.length < 5) {
      setError('At least 5 cycles are required for rolling/delta features. Click "+ Add Cycle" to add more.');
      return;
    }

    // 3. At least one sensor selected
    if (selectedSensors.length === 0) {
      setError('Please select at least one sensor to enter data for.');
      return;
    }

    // 4. Pre-flight schema check — must match the full 17-field schema
    //    before reaching the backend. Never fabricate missing values.
    if (selectedSensors.length < ALL_SENSOR_KEYS.length) {
      const missing = ALL_SENSOR_KEYS.filter(k => !selectedSensors.includes(k));
      const missingLabels = missing.map(k => MANUAL_FIELDS.find(f => f.key === k)?.label).join(', ');
      setError(
        `Insufficient sensor data for this model. The trained models require all ${ALL_SENSOR_KEYS.length} ` +
        `sensor/operational fields to produce a prediction. ` +
        `Missing: ${missingLabels}. ` +
        `Please select all fields, or use the CSV upload with a complete sensor history file.`
      );
      return;
    }

    // 5. All selected fields must have a numeric value for every cycle
    const activeFields = MANUAL_FIELDS.filter(f => selectedSensors.includes(f.key));
    for (let i = 0; i < manualRows.length; i++) {
      for (const f of activeFields) {
        const v = manualRows[i][f.key];
        if (v === '' || isNaN(Number(v))) {
          setError(`Cycle ${i + 1}: "${f.label}" value is missing or not a number.`);
          return;
        }
      }
    }

    setIsLoading(true);
    setError(null);
    setResults(null);
    setAllCycles([]);

    try {
      const blob = buildCsvBlob(manualUnit, manualRows, selectedSensors);
      const form = new FormData();
      form.append('file', new File([blob], 'manual_entry.csv', { type: 'text/csv' }));
      const res = await _postForm(form);
      setResults(res);
      setAllCycles(manualRows.map(r => ({ ...r, unit: manualUnit })));
    } catch (err) {
      const msg = err.message || '';
      if (msg.includes('do not match expected schema') || msg.includes('Insufficient')) {
        setError(
          'Insufficient sensor data for this model. Please provide all required sensor measurements ' +
          '(OP1, OP2, S2–S4, S6–S9, S11–S15, S17, S20, S21), or upload a CSV with the full schema.'
        );
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const downloadSample = () => {
    const csv = generateSampleCSV();
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_sensor_history.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openBob = () => {
    setShowBobModal(true);
  };

  // Build per-unit trend data from allCycles parsed rows
  const getTrendData = (unit) => {
    const unitStr = String(unit);
    return allCycles
      .filter(r => String(r.unit) === unitStr)
      .sort((a, b) => Number(a.cycle) - Number(b.cycle))
      .map(r => ({ cycle: Number(r.cycle) }));
  };

  // Merge backend per-cycle results with parsed CSV for charts
  // Note: /api/assess only returns the latest cycle; for multi-cycle charts we
  // show the raw sensor trend from the uploaded CSV (no fabricated model outputs).
  const getCycleTrend = (unit) => getTrendData(unit);

  const resultsArr = results || [];


  return (
    <div className="app" style={{ minHeight: '100vh', paddingBottom: '5rem' }}>

      {/* ── Navbar ── */}
      <nav className={`navbar ${isScrolled ? 'scrolled' : ''}`}>
        <div className="container navbar-content">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
            <Plane className="text-teal" size={28} />
            <span>Astra<span className="text-copper">Pulse</span></span>
          </Link>
          <div className="nav-links" style={{ display: 'flex', gap: '2rem' }}>
            <Link to="/mission-intelligence" className="nav-link">Mission Intelligence</Link>
            <span className="nav-link" style={{ fontWeight: 600, color: 'var(--text-main)' }}>Sensor Assessment</span>
          </div>
          <div className="nav-actions" style={{ display: 'flex', gap: '0.75rem' }}>
            <Link to="/mission-intelligence" className="btn btn-secondary" style={{ padding: '0.6rem 1.25rem', fontSize: '0.9rem' }}>
              <ArrowLeft size={16} /> Mission Intelligence
            </Link>
          </div>
        </div>
      </nav>

      <div className="container" style={{ paddingTop: '8rem' }}>

        {/* ── Page Header ── */}
        <div style={{ marginBottom: '2.5rem' }}>
          <div className="badge" style={{ marginBottom: '1rem' }}>
            <span className="badge-dot animate-pulse-soft" />
            UNSEEN ASSET INFERENCE
          </div>
          <h1 className="hero-title" style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
            Assess a New Asset
          </h1>
          <p className="hero-description" style={{ margin: 0, maxWidth: '640px' }}>
            Upload unseen sensor history to generate an AI-powered health, failure-risk and
            remaining-useful-life assessment. Models run without retraining on the uploaded data.
          </p>
        </div>

        {/* ── Model badge ── */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.625rem 1.25rem',
          background: 'rgba(91,155,152,0.06)',
          border: '1px solid rgba(91,155,152,0.25)',
          borderRadius: '999px',
          fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.04em',
          color: 'var(--accent-teal)',
          marginBottom: '2.5rem'
        }}>
          <Cpu size={14} />
          UNSEEN ASSET INFERENCE — IsolationForest · XGBoost · RandomForest
          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>No retraining on uploaded data</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '2rem' }} className="sa-layout">
          <style dangerouslySetInnerHTML={{ __html: `
            @media (min-width: 1100px) { .sa-layout { grid-template-columns: 480px 1fr; } }
            .sa-upload-zone {
              border: 2px dashed var(--border-light);
              border-radius: 1.25rem;
              padding: 2.5rem 2rem;
              text-align: center;
              transition: all 0.2s ease;
              cursor: pointer;
              background: var(--bg-surface);
            }
            .sa-upload-zone.drag { border-color: var(--accent-teal); background: rgba(91,155,152,0.04); }
            .sa-upload-zone:hover { border-color: rgba(91,155,152,0.5); }
            @keyframes sa-spin { 100% { transform: rotate(360deg); } }
            .sa-spin { animation: sa-spin 1s linear infinite; }
            .sa-tab { padding: 0.6rem 1.25rem; border-radius: 999px; font-size: 0.875rem; font-weight: 600; cursor: pointer; border: 1px solid var(--border-light); background: transparent; color: var(--text-muted); transition: all 0.2s; display: inline-flex; align-items: center; gap: 0.4rem; }
            .sa-tab.active { background: var(--text-main); color: white; border-color: var(--text-main); }
            .sa-field input { width: 100%; padding: 0.5rem 0.625rem; border: 1px solid var(--border-light); border-radius: 0.5rem; font-size: 0.8rem; background: var(--bg-surface); color: var(--text-main); outline: none; font-family: monospace; }
            .sa-field input:focus { border-color: var(--accent-teal); box-shadow: 0 0 0 3px rgba(91,155,152,0.12); }
            .sa-field label { display: block; font-size: 0.7rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
          ` }} />

          {/* LEFT COLUMN — Input (tabbed) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* ── Tab switcher ── */}
            <div style={{ display: 'flex', gap: '0.5rem', padding: '0.25rem', background: 'var(--bg-surface)', border: '1px solid var(--border-light)', borderRadius: '999px', width: 'fit-content' }}>
              <button className={`sa-tab ${mode === 'upload' ? 'active' : ''}`} onClick={() => { setMode('upload'); setError(null); setResults(null); }}>
                <Upload size={14} /> Upload CSV
              </button>
              <button className={`sa-tab ${mode === 'manual' ? 'active' : ''}`} onClick={() => { setMode('manual'); setError(null); setResults(null); }}>
                <PenLine size={14} /> Enter Manually
              </button>
            </div>

            {/* ── UPLOAD PANEL ── */}
            {mode === 'upload' && (
              <section className="feature-card" style={{ padding: '2rem' }}>
                <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Upload size={20} className="text-teal" /> Upload Sensor History
                </h2>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                  Requires <strong>multiple cycles</strong> of raw sensor data.
                  Minimum 2 cycles; more cycles improve trend accuracy.
                </p>

                {!file ? (
                  <div
                    className={`sa-upload-zone ${isDragging ? 'drag' : ''}`}
                    onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload size={40} style={{ color: 'var(--accent-teal)', marginBottom: '1rem', opacity: 0.7 }} />
                    <p style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Drag & drop or click to browse</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>CSV files only · multi-cycle engine sensor history</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      style={{ display: 'none' }}
                      onChange={(e) => handleFile(e.target.files[0])}
                    />
                  </div>
                ) : (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '1rem',
                    padding: '1rem 1.25rem',
                    background: 'rgba(91,155,152,0.06)',
                    border: '1px solid rgba(91,155,152,0.2)',
                    borderRadius: '0.875rem'
                  }}>
                    <FileText size={28} style={{ color: 'var(--accent-teal)', flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {(file.size / 1024).toFixed(1)} KB
                        {allCycles.length > 0 && ` · ${allCycles.length} rows parsed`}
                      </div>
                    </div>
                    <button onClick={removeFile} style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}>
                      <X size={18} />
                    </button>
                  </div>
                )}

                {error && (
                  <div style={{ marginTop: '1rem', padding: '0.875rem 1rem', background: 'rgba(229,79,79,0.06)', border: '1px solid rgba(229,79,79,0.3)', borderRadius: '0.75rem', color: '#e54f4f', fontSize: '0.875rem', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '0.1rem' }} />{error}
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.5rem' }}>
                  <button className="btn btn-primary" onClick={runAssessment} disabled={!file || isLoading} style={{ width: '100%', justifyContent: 'center', opacity: (!file || isLoading) ? 0.6 : 1 }}>
                    {isLoading ? <><RefreshCw size={18} className="sa-spin" /> Running Assessment…</> : <><Zap size={18} /> Run Assessment</>}
                  </button>
                  <button className="btn btn-secondary" onClick={downloadSample} style={{ width: '100%', justifyContent: 'center' }}>
                    <Download size={16} /> Download Sample CSV
                  </button>
                </div>
              </section>
            )}

            {/* ── MANUAL ENTRY PANEL ── */}
            {mode === 'manual' && (
              <section className="feature-card" style={{ padding: '2rem' }}>
                <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <PenLine size={20} className="text-teal" /> Enter Sensor Data Manually
                </h2>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                  Select only the sensors you have data for, then enter readings for <strong>at least 5 cycles</strong>.
                  Individual sensor fields are optional — enter only what you have.
                  A prediction requires all 17 fields to be present; see the message below the selector.
                </p>

                {/* Unit ID */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.35rem' }}>
                    Engine Unit ID <span style={{ color: '#e54f4f' }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={manualUnit}
                    onChange={e => setManualUnit(e.target.value)}
                    style={{ width: '120px', padding: '0.5rem 0.75rem', border: '1px solid var(--border-light)', borderRadius: '0.5rem', fontSize: '0.9rem', background: 'var(--bg-surface)', color: 'var(--text-main)', outline: 'none', fontFamily: 'monospace' }}
                    placeholder="1"
                  />
                </div>

                {/* ── Sensor Selector ── */}
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.625rem' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Available Sensors
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => setSelectedSensors([...ALL_SENSOR_KEYS])}
                        style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--accent-teal)', background: 'none', border: 'none', cursor: 'pointer', padding: '0.15rem 0.4rem', borderRadius: '0.25rem' }}
                      >
                        Select All
                      </button>
                      <button
                        onClick={() => setSelectedSensors([])}
                        style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: '0.15rem 0.4rem', borderRadius: '0.25rem' }}
                      >
                        Clear All
                      </button>
                    </div>
                  </div>
                  {SENSOR_GROUPS.map(group => (
                    <div key={group.label} style={{ marginBottom: '0.625rem' }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem', letterSpacing: '0.04em' }}>
                        {group.label}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {group.keys.map(key => {
                          const field = MANUAL_FIELDS.find(f => f.key === key);
                          const active = selectedSensors.includes(key);
                          return (
                            <button
                              key={key}
                              onClick={() => setSelectedSensors(prev =>
                                active ? prev.filter(k => k !== key) : [...prev, key]
                              )}
                              title={field.title}
                              style={{
                                padding: '0.3rem 0.6rem',
                                borderRadius: '999px',
                                fontSize: '0.72rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                border: `1px solid ${active ? 'var(--accent-teal)' : 'var(--border-light)'}`,
                                background: active ? 'rgba(91,155,152,0.12)' : 'transparent',
                                color: active ? 'var(--accent-teal)' : 'var(--text-muted)',
                                transition: 'all 0.15s ease',
                              }}
                            >
                              {field.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem', fontStyle: 'italic' }}>
                    {selectedSensors.length} of {ALL_SENSOR_KEYS.length} fields selected.
                    {selectedSensors.length === ALL_SENSOR_KEYS.length
                      ? <span style={{ color: 'var(--accent-teal)' }}> ✓ All fields selected — prediction is possible.</span>
                      : <span style={{ color: '#C9725D' }}> {ALL_SENSOR_KEYS.length - selectedSensors.length} field(s) not selected — prediction will be blocked until all are present.</span>
                    }
                  </p>
                </div>

                {/* Cycle rows */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '420px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                  {manualRows.map((row, rowIdx) => {
                    const visibleFields = MANUAL_FIELDS.filter(f => selectedSensors.includes(f.key));
                    return (
                      <div key={rowIdx} style={{ border: '1px solid var(--border-light)', borderRadius: '0.875rem', padding: '1rem', background: 'var(--bg-color)', position: 'relative' }}>
                        {/* Row header */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-teal)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            Cycle {rowIdx + 1}
                          </span>
                          {manualRows.length > 5 && (
                            <button onClick={() => removeManualRow(rowIdx)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#e54f4f', padding: '0.2rem', display: 'flex', alignItems: 'center' }} title="Remove cycle">
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                        {/* Fields grid — only selected sensors */}
                        {visibleFields.length > 0 ? (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))', gap: '0.625rem' }}>
                            {visibleFields.map(f => (
                              <div key={f.key} className="sa-field">
                                <label title={f.title}>{f.label}</label>
                                <input
                                  type="number"
                                  step="any"
                                  value={row[f.key]}
                                  onChange={e => updateManualRow(rowIdx, f.key, e.target.value)}
                                  placeholder={f.placeholder}
                                />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Select at least one sensor above to enter data for this cycle.
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Add cycle button */}
                <button
                  onClick={addManualRow}
                  style={{ marginTop: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-teal)', background: 'rgba(91,155,152,0.06)', border: '1px dashed rgba(91,155,152,0.4)', borderRadius: '0.625rem', padding: '0.5rem 1rem', cursor: 'pointer', width: '100%', justifyContent: 'center' }}
                >
                  <Plus size={15} /> Add Cycle ({manualRows.length + 1})
                </button>

                {error && (
                  <div style={{ marginTop: '1rem', padding: '0.875rem 1rem', background: 'rgba(229,79,79,0.06)', border: '1px solid rgba(229,79,79,0.3)', borderRadius: '0.75rem', color: '#e54f4f', fontSize: '0.875rem', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '0.1rem' }} />{error}
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.25rem' }}>
                  <button className="btn btn-primary" onClick={runManualAssessment} disabled={isLoading} style={{ width: '100%', justifyContent: 'center', opacity: isLoading ? 0.6 : 1 }}>
                    {isLoading ? <><RefreshCw size={18} className="sa-spin" /> Running Assessment…</> : <><Zap size={18} /> Run Assessment</>}
                  </button>
                  <button className="btn btn-secondary" onClick={resetManual} style={{ width: '100%', justifyContent: 'center' }}>
                    <RefreshCw size={15} /> Reset All Fields
                  </button>
                </div>
              </section>
            )}

            {/* Schema reference card — shown for both modes */}
            <section className="feature-card" style={{ padding: '1.5rem', background: 'var(--bg-color)' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Info size={15} className="text-teal" /> Required Input Schema
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
                Cleaned format (19 cols):
              </p>
              <code style={{ display: 'block', fontSize: '0.75rem', background: 'var(--bg-surface)', border: '1px solid var(--border-light)', borderRadius: '0.5rem', padding: '0.75rem', color: 'var(--text-main)', lineHeight: 1.8, overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {SAMPLE_CSV_COLS.join(', ')}
              </code>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem', lineHeight: 1.5 }}>
                <strong>Note:</strong> Do not include a <code>rul</code> column — RUL is a model output, not an input.
                Manual entry: at least 5 cycles required. Individual sensor fields are optional to enter,
                but all 17 must be selected and filled before a prediction can run.
              </p>
            </section>
          </div>

          {/* RIGHT COLUMN — Results */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {!results && !isLoading && (
              <div style={{
                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', minHeight: '300px',
                background: 'var(--bg-surface)',
                border: '1px dashed var(--border-light)',
                borderRadius: '1.5rem',
                color: 'var(--text-muted)', textAlign: 'center', padding: '3rem 2rem'
              }}>
                <BrainCircuit size={48} style={{ opacity: 0.25, marginBottom: '1rem' }} />
                <p style={{ fontSize: '1rem', fontWeight: 500 }}>Assessment results will appear here</p>
                <p style={{ fontSize: '0.875rem', opacity: 0.7, marginTop: '0.5rem' }}>Upload a CSV and click Run Assessment</p>
              </div>
            )}

            {isLoading && (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', minHeight: '300px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-light)',
                borderRadius: '1.5rem',
                color: 'var(--text-muted)', textAlign: 'center', padding: '3rem 2rem',
                gap: '1rem'
              }}>
                <RefreshCw size={40} className="sa-spin" style={{ color: 'var(--accent-teal)' }} />
                <p style={{ fontWeight: 600 }}>Running assessment pipeline…</p>
                <p style={{ fontSize: '0.85rem' }}>Preprocessing → IsolationForest → XGBoost → RandomForest</p>
              </div>
            )}

            {results && resultsArr.map((result) => {
              const rd = deriveReadiness(result);
              const explanation = buildRiskExplanation(result);
              const cycleTrend = getCycleTrend(result.unit);

              return (
                <div key={result.unit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                  {/* ── Mission Readiness Banner ── */}
                  <div style={{
                    padding: '1.75rem 2rem',
                    background: rd.bg,
                    border: `2px solid ${rd.border}`,
                    borderRadius: '1.25rem',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    flexWrap: 'wrap', gap: '1rem'
                  }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                        Unit {result.unit} · Cycle {result.cycle}
                      </div>
                      <div style={{ fontSize: '2rem', fontWeight: 800, color: rd.color, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}>
                        {rd.icon === 'ok' ? <CheckCircle size={28} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} /> :
                         rd.icon === 'warn' ? <AlertTriangle size={28} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} /> :
                         <X size={28} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />}
                        {rd.label}
                      </div>
                    </div>
                    <div style={{
                      fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.06em',
                      color: 'var(--accent-teal)',
                      background: 'rgba(91,155,152,0.08)',
                      border: '1px solid rgba(91,155,152,0.2)',
                      borderRadius: '999px', padding: '0.375rem 0.875rem',
                      display: 'flex', alignItems: 'center', gap: '0.4rem'
                    }}>
                      <Cpu size={12} /> UNSEEN ASSET INFERENCE
                    </div>
                  </div>

                  {/* ── 6 Metric Cards ── */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem' }}>
                    <MetricCard
                      label="Health Score" icon={Activity}
                      value={result.health_score.toFixed(1) + '/100'}
                      sub={result.health_status}
                      color={result.health_score >= 70 ? '#5B9B98' : result.health_score >= 40 ? '#C9725D' : '#e54f4f'}
                      accent={result.health_score >= 70 ? '#5B9B98' : result.health_score >= 40 ? '#C9725D' : '#e54f4f'}
                    />
                    <MetricCard
                      label="Health Status" icon={ShieldCheck}
                      value={result.health_status}
                      sub="IsolationForest output"
                      color={result.health_status === 'NORMAL' ? '#5B9B98' : result.health_status === 'WARNING' ? '#C9725D' : '#e54f4f'}
                      accent="#9994B6"
                    />
                    <MetricCard
                      label="Failure Probability" icon={AlertTriangle}
                      value={(result.failure_probability * 100).toFixed(2) + '%'}
                      sub={result.failure_status}
                      color={result.failure_probability < 0.3 ? '#5B9B98' : result.failure_probability < 0.7 ? '#C9725D' : '#e54f4f'}
                      accent={result.failure_probability < 0.3 ? '#5B9B98' : result.failure_probability < 0.7 ? '#C9725D' : '#e54f4f'}
                    />
                    <MetricCard
                      label="Failure Status" icon={Target}
                      value={result.failure_status}
                      sub="XGBoost output"
                      color={result.failure_status === 'LOW' ? '#5B9B98' : result.failure_status === 'MEDIUM' ? '#C9725D' : '#e54f4f'}
                      accent="#C9725D"
                    />
                    <MetricCard
                      label="Predicted RUL" icon={TrendingUp}
                      value={result.predicted_rul_cycles + ' cycles'}
                      sub="RandomForest output"
                      color={result.predicted_rul_cycles > 100 ? '#5B9B98' : result.predicted_rul_cycles > 30 ? '#C9725D' : '#e54f4f'}
                      accent="#5B9B98"
                    />
                    <MetricCard
                      label="Anomaly Score" icon={Zap}
                      value={result.anomaly_score.toFixed(4)}
                      sub="Higher = more anomalous"
                      color={result.anomaly_score < 0.3 ? '#5B9B98' : result.anomaly_score < 0.6 ? '#C9725D' : '#e54f4f'}
                      accent="#9994B6"
                    />
                  </div>

                  {/* ── Why at risk ── */}
                  <section className="feature-card" style={{ padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#C9725D', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <BrainCircuit size={18} /> Why is this asset {rd.label === 'MISSION READY' ? 'assessed as ready' : 'at risk'}?
                    </h3>
                    <p style={{
                      fontSize: '0.9rem', lineHeight: 1.65, color: 'var(--text-main)',
                      padding: '1rem', borderRadius: '0.75rem', borderLeft: '4px solid #C9725D',
                      background: 'rgba(201,114,93,0.05)'
                    }}>
                      {explanation}
                    </p>
                    <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', marginTop: '0.75rem', fontStyle: 'italic' }}>
                      Explanation derived solely from model outputs above. No specific physical component failure is claimed without inspection data.
                    </p>
                  </section>

                  {/* ── Cycle Trend Charts ── */}
                  {cycleTrend.length >= 2 && (
                    <section className="feature-card" style={{ padding: '1.75rem' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <TrendingUp size={18} className="text-copper" /> Sensor Cycle History — Unit {result.unit}
                      </h3>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
                        {cycleTrend.length} cycles uploaded · assessment based on latest (cycle {result.cycle})
                      </p>

                      {/* Cycle count bar — shows how many cycles were uploaded */}
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '0.5rem',
                        padding: '0.75rem 1rem',
                        background: 'rgba(91,155,152,0.06)',
                        borderRadius: '0.625rem', marginBottom: '1.25rem',
                        fontSize: '0.82rem', color: 'var(--text-muted)'
                      }}>
                        <Activity size={14} style={{ color: 'var(--accent-teal)' }} />
                        <strong style={{ color: 'var(--text-main)' }}>{cycleTrend.length}</strong> sensor cycles detected in uploaded file.
                        Latest cycle <strong style={{ color: 'var(--text-main)' }}>{result.cycle}</strong> used for all model predictions.
                        {cycleTrend.length < 5 && (
                          <span style={{ color: '#C9725D', marginLeft: '0.25rem' }}>
                            ⚠ More cycles improve rolling-feature quality.
                          </span>
                        )}
                      </div>

                      {/* Raw sensor trends from uploaded CSV — two example sensors if available */}
                      {(() => {
                        const sensorsToPlot = ['s2', 's7', 's11', 's14'].filter(s =>
                          allCycles.some(r => r[s] !== undefined && r[s] !== '' && !isNaN(Number(r[s])))
                        ).slice(0, 2);

                        if (sensorsToPlot.length === 0) return null;

                        const chartData = cycleTrend.map((_, i) => {
                          const unitRows = allCycles
                            .filter(r => String(r.unit) === String(result.unit))
                            .sort((a, b) => Number(a.cycle) - Number(b.cycle));
                          const row = unitRows[i];
                          if (!row) return null;
                          const pt = { cycle: Number(row.cycle) };
                          sensorsToPlot.forEach(s => { pt[s] = row[s] !== '' ? Number(row[s]) : null; });
                          return pt;
                        }).filter(Boolean);

                        const COLORS = ['var(--accent-teal)', '#C9725D'];
                        const latestCycle = result.cycle;

                        return (
                          <div style={{ height: 220 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                                <XAxis dataKey="cycle" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} width={55} />
                                <Tooltip
                                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', fontSize: '0.8rem' }}
                                  formatter={(v, n) => [typeof v === 'number' ? v.toFixed(3) : v, n.toUpperCase()]}
                                />
                                <Legend iconType="circle" wrapperStyle={{ paddingTop: '0.75rem', fontSize: '0.8rem' }} />
                                <ReferenceLine x={latestCycle} stroke="var(--accent-copper)" strokeDasharray="4 2" label={{ value: 'Latest', position: 'top', fontSize: 10, fill: 'var(--accent-copper)' }} />
                                {sensorsToPlot.map((s, i) => (
                                  <Line key={s} type="monotone" dataKey={s} name={s.toUpperCase()} stroke={COLORS[i]} strokeWidth={2} dot={false} connectNulls />
                                ))}
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      })()}
                    </section>
                  )}

                  {/* ── Ask Mission Copilot ── */}
                  <section style={{
                    padding: '1.75rem 2rem',
                    background: 'linear-gradient(135deg, var(--bg-color) 0%, rgba(91,155,152,0.06) 100%)',
                    border: '1px solid rgba(91,155,152,0.2)',
                    borderRadius: '1.25rem',
                    display: 'flex', flexWrap: 'wrap', gap: '1.5rem',
                    alignItems: 'center', justifyContent: 'space-between'
                  }}>
                    <div>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <BrainCircuit size={18} className="text-teal" /> Ask Mission Copilot →
                      </h3>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '420px' }}>
                        Pass this assessment — health, failure risk, RUL, anomaly score, and readiness — to IBM Bob for interpretation and maintenance guidance.
                      </p>
                    </div>
                    <button className="btn btn-primary" onClick={openBob} style={{ whiteSpace: 'nowrap' }}>
                      Open Copilot Context <ArrowRight size={16} />
                    </button>
                  </section>

                </div>
              );
            })}

          </div>
        </div>
      </div>
      {/* ── Bob Modal ── */}
      {showBobModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '2rem'
        }}>
          <div style={{
            background: 'var(--bg-color)', borderRadius: '1rem',
            padding: '2rem', maxWidth: '800px', width: '100%',
            maxHeight: '90vh', overflowY: 'auto',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            position: 'relative'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <BrainCircuit className="text-teal" size={24} /> Ask Mission Copilot (IBM Bob)
              </h2>
              <button onClick={() => setShowBobModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={24} />
              </button>
            </div>
            
            <div style={{ marginBottom: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <p style={{ marginBottom: '0.5rem' }}>
                The AI conversation occurs in your secure IBM Bob environment. 
                Please copy the exact context and question below, then paste it into your IBM Bob chat to begin the analysis.
              </p>
              <p>
                <strong>Note:</strong> AstraPulse does not embed Bob directly to ensure your AI reasoning remains secure within the designated Copilot environment.
              </p>
            </div>

            <div style={{ position: 'relative', marginBottom: '1.5rem' }}>
              <pre style={{
                background: 'var(--bg-surface)', padding: '1.5rem',
                borderRadius: '0.5rem', border: '1px solid var(--border-light)',
                whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem',
                lineHeight: 1.5, color: 'var(--text-main)', margin: 0
              }}>
                {buildBobContext(results, allCycles)}
              </pre>
              <button
                onClick={(e) => {
                  navigator.clipboard.writeText(buildBobContext(results, allCycles));
                  const btn = e.currentTarget;
                  const oldText = btn.innerText;
                  btn.innerText = 'Copied!';
                  setTimeout(() => { btn.innerText = oldText; }, 2000);
                }}
                style={{
                  position: 'absolute', top: '0.5rem', right: '0.5rem',
                  padding: '0.4rem 0.8rem', fontSize: '0.75rem', fontWeight: 600,
                  background: 'var(--accent-teal)', color: 'white',
                  border: 'none', borderRadius: '0.25rem', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.4rem'
                }}
              >
                Copy Context
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowBobModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <footer className="footer" style={{ marginTop: '4rem' }}>
        <div className="container">
          <div className="logo" style={{ justifyContent: 'center', marginBottom: '0.75rem', color: 'var(--text-main)' }}>
            <Plane className="text-teal" size={22} />
            <span>Astra<span className="text-copper">Pulse</span></span>
          </div>
          <p>© 2026 AstraPulse. Defense & Aerospace Mission Readiness Copilot.</p>
        </div>
      </footer>
    </div>
  );
}
