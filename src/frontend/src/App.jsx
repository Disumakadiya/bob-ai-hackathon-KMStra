import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from './LandingPage';
import MissionIntelligence from './MissionIntelligence';
import './index.css';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/mission-intelligence" element={<MissionIntelligence />} />
    </Routes>
  );
}

export default App;
