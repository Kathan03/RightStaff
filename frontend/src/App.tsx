import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CandidatePortal } from './pages/CandidatePortal';
import { RecruiterDashboard } from './pages/RecruiterDashboard';
import { Navbar } from './components/shared/Navbar';
import { ErrorBoundary } from './components/shared/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <Routes>
            <Route path="/" element={<CandidatePortal />} />
            <Route path="/recruiter" element={<RecruiterDashboard />} />
          </Routes>
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
