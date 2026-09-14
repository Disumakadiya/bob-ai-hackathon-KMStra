import React, { useEffect, useState } from 'react';
import { 
  Plane, 
  Activity, 
  ShieldCheck, 
  Crosshair, 
  ArrowRight, 
  Target, 
  Wrench, 
  Menu, 
  X, 
  TrendingUp,
  BrainCircuit,
  Database
} from 'lucide-react';
import { Link } from 'react-router-dom';
import './index.css';

function LandingPage() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
      
      // Scroll reveal logic
      const revealElements = document.querySelectorAll('.reveal');
      revealElements.forEach((el) => {
        const windowHeight = window.innerHeight;
        const elementTop = el.getBoundingClientRect().top;
        const elementVisible = 100;
        
        if (elementTop < windowHeight - elementVisible) {
          el.classList.add('active');
        }
      });
    };

    window.addEventListener('scroll', handleScroll);
    // Trigger once on mount
    handleScroll();
    
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="app">
      {/* Navigation */}
      <nav className={`navbar ${isScrolled ? 'scrolled' : ''}`}>
        <div className="container navbar-content">
          <div className="logo">
            <Plane className="text-teal" size={28} />
            <span>Astra<span className="text-copper">Pulse</span></span>
          </div>
          
          <div className="nav-links">
            <a href="#home" className="nav-link">Home</a>
            <a href="#solutions" className="nav-link">Solutions</a>
            <a href="#impact" className="nav-link">Impact</a>
            <a href="#how-it-works" className="nav-link">How It Works</a>
            <Link to="/sensor-assessment" className="nav-link">Sensor Assessment</Link>
          </div>
          
          <div className="nav-actions">
            <Link to="/mission-intelligence" className="btn btn-primary d-none-mobile" style={{ display: 'inline-flex', alignItems: 'center' }}>
              Launch Copilot <ArrowRight size={18} />
            </Link>
            <button 
              className="mobile-toggle d-desktop-none"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'none' }}
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section id="home" className="hero">
        <div className="hero-bg-accent"></div>
        <div className="container hero-container">
          <div className="hero-content reveal">
            <div className="badge">
              <span className="badge-dot animate-pulse-soft"></span>
              DEFENSE & AEROSPACE
            </div>
            
            <h1 className="hero-title">
              Predict Today.<br />
              <span className="text-copper">Fly Tomorrow.</span>
            </h1>
            
            <p className="hero-description">
              AI-powered predictive maintenance that keeps aircraft, vehicles, and equipment mission-ready, always.
            </p>
            
            <div className="hero-actions">
              <Link to="/mission-intelligence" className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center' }}>
                Launch Mission Copilot <ArrowRight size={18} />
              </Link>
              <Link to="/sensor-assessment" className="btn btn-secondary" style={{ display: 'inline-flex', alignItems: 'center' }}>
                Assess New Asset <ArrowRight size={18} />
              </Link>
            </div>
          </div>
          
          <div className="hero-visual reveal animate-float">
            <div className="aircraft-container">
              {/* Unsplash fallback for aerospace visualization */}
              {/* Complex animated tech radar for hero visual */}
              <div className="hero-animation-wrapper aircraft-img" style={{ borderRadius: '2rem' }}>
                <div className="radar-grid"></div>
                <div className="scanner-line"></div>
                <div className="tech-circle"></div>
                <div className="tech-circle-inner"></div>
                <div className="data-node node-1"></div>
                <div className="data-node node-2"></div>
                <div className="data-node node-3"></div>
                <div className="data-node node-4"></div>
                <Plane size={80} style={{ color: 'rgba(91, 155, 152, 0.8)', zIndex: 10, filter: 'drop-shadow(0 0 20px rgba(91, 155, 152, 0.5))' }} />
              </div>
              <div className="aircraft-overlay"></div>
            </div>
            
            {/* Animated HUD Cards */}
            <div className="hud-card hud-1 animate-hud">
              <span className="hud-card-title">Engine Health</span>
              <div className="hud-card-value">
                98<span className="hud-unit">%</span>
              </div>
              <div className="hud-status status-good">
                <TrendingUp size={14} /> +2% vs last week
              </div>
            </div>
            
            <div className="hud-card hud-2 animate-hud-delayed">
              <span className="hud-card-title">Predicted RUL</span>
              <div className="hud-card-value">
                320<span className="hud-unit">cycles</span>
              </div>
              <div className="hud-status status-good">
                <span className="status-indicator"></span> Optimal
              </div>
            </div>
            
            <div className="hud-card hud-3 animate-hud">
              <span className="hud-card-title">Risk Level</span>
              <div className="hud-card-value" style={{ color: 'var(--accent-teal)' }}>
                LOW
              </div>
              <div className="hud-status">
                <ShieldCheck size={14} className="text-teal" /> Verified
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Proposition Strip */}
      <section className="value-prop-strip">
        <div className="container value-props reveal">
          <div className="value-prop-item">
            <div className="value-icon-box"><Crosshair size={22} /></div>
            Predict Failures Early
          </div>
          <div className="value-prop-item">
            <div className="value-icon-box" style={{ background: 'rgba(201,114,93,0.1)', color: 'var(--accent-copper)' }}><Wrench size={22} /></div>
            Optimize Maintenance
          </div>
          <div className="value-prop-item">
            <div className="value-icon-box" style={{ background: 'rgba(153,148,182,0.1)', color: 'var(--accent-lavender)' }}><Target size={22} /></div>
            Maximize Mission Readiness
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="solutions" className="section-padding">
        <div className="container">
          <div className="section-header reveal">
            <h2 className="hero-title" style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
              Turn Data Into <span className="text-teal">Readiness</span>
            </h2>
            <p className="hero-description" style={{ margin: '0 auto' }}>
              From raw sensor data to real-time insights, AstraPulse helps you predict failures, optimize maintenance, and keep your fleet ready for what's next.
            </p>
          </div>
          
          <div className="grid-features reveal">
            {/* Feature 1 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <Activity size={28} />
              </div>
              <h3 className="feature-title">Real-Time Monitoring</h3>
              <p className="feature-desc">
                Ingest and analyze HUMS and operational data for live asset health insights.
              </p>
            </div>
            
            {/* Feature 2 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <Wrench size={28} />
              </div>
              <h3 className="feature-title">Predictive Maintenance</h3>
              <p className="feature-desc">
                Identify potential failures weeks in advance and reduce unplanned downtime.
              </p>
            </div>
            
            {/* Feature 3 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <Target size={28} />
              </div>
              <h3 className="feature-title">Mission Readiness Copilot</h3>
              <p className="feature-desc">
                AI-powered recommendations tailored to your missions, assets, and risk tolerance.
              </p>
            </div>
            
            {/* Feature 4 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <ShieldCheck size={28} />
              </div>
              <h3 className="feature-title">Secure & Explainable AI</h3>
              <p className="feature-desc">
                Built with trust, transparency, and defense-grade security in mind.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Visual Flow Section */}
      <section id="how-it-works" className="flow-section reveal">
        <div className="flow-bg-grid"></div>
        <div className="flow-content container">
          <h2 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Intelligence in Action</h2>
          <p style={{ opacity: 0.8, maxWidth: '600px', margin: '0 auto' }}>A seamless pipeline from raw data acquisition to prioritized actionable intelligence.</p>
          
          <div className="flow-steps">
            <div className="flow-step">
              <div className="flow-icon-circle"><Database size={24} /></div>
              <span className="flow-step-text">Sensor Data</span>
            </div>
            <div className="flow-connector"></div>
            
            <div className="flow-step">
              <div className="flow-icon-circle"><Activity size={24} /></div>
              <span className="flow-step-text">Health & Anomaly Detection</span>
            </div>
            <div className="flow-connector"></div>
            
            <div className="flow-step">
              <div className="flow-icon-circle"><BrainCircuit size={24} /></div>
              <span className="flow-step-text">Failure Prediction & RUL</span>
            </div>
            <div className="flow-connector"></div>
            
            <div className="flow-step">
              <div className="flow-icon-circle"><Target size={24} /></div>
              <span className="flow-step-text">Mission Readiness</span>
            </div>
          </div>
        </div>
      </section>

      {/* Mission Section */}
      <section id="impact" className="section-padding" style={{ backgroundColor: 'var(--bg-surface)' }}>
        <div className="container mission-section reveal">
          <div>
            <div className="badge">
              <span className="badge-dot"></span>
              OUR MISSION
            </div>
            <h2 className="hero-title" style={{ fontSize: '3rem' }}>
              Smarter Maintenance.<br />
              <span className="text-copper">Stronger Tomorrows.</span>
            </h2>
            <p className="hero-description" style={{ marginTop: '1.5rem', marginBottom: '2.5rem' }}>
              We empower defense and aerospace organizations with AI-driven insights to reduce risk, extend asset life, and ensure mission success. Less time in the hangar means more time in the skies.
            </p>
            <button className="btn btn-primary">
              Learn About Our Impact <ArrowRight size={18} />
            </button>
          </div>
          
          <div className="mission-image-wrapper reveal animate-float-delayed">
            {/* Complex animated data grid for mission section */}
            <div className="mission-animation-wrapper mission-image">
              <div className="hex-grid"></div>
              <div className="ripple-wrapper">
                <div className="pulse-ring-mission"></div>
                <div className="pulse-ring-mission"></div>
                <div className="pulse-ring-mission"></div>
              </div>
              <div className="mission-center-icon">
                <ShieldCheck size={64} />
              </div>
            </div>
            <div className="mission-quote-card">
              <Target className="quote-icon" size={32} />
              <p className="quote-text">
                "Readiness isn't built in the hangar. It's built in the data."
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="logo" style={{ justifyContent: 'center', marginBottom: '1rem', color: 'var(--text-main)' }}>
            <Plane className="text-teal" size={24} />
            <span>Astra<span className="text-copper">Pulse</span></span>
          </div>
          <p>© 2026 AstraPulse. Defense & Aerospace Mission Readiness Copilot.</p>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
