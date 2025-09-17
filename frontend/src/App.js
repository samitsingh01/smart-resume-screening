// frontend/src/App.js - Fixed version
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import JobManager from './components/JobManager';
import ResumeManager from './components/ResumeManager';
import MatchingDashboard from './components/MatchingDashboard';
import Analytics from './components/Analytics';
import LoadingSpinner from './components/LoadingSpinner';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('jobs');
  const [loading, setLoading] = useState(false);
  const [systemHealth, setSystemHealth] = useState(null);
  const [notification, setNotification] = useState(null);

  // Check system health on startup
  useEffect(() => {
    checkSystemHealth();
    const interval = setInterval(checkSystemHealth, 60000); // Check every minute
    return () => clearInterval(interval);
  }, []);

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health/detailed`);
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Health check failed:', error);
      setSystemHealth({ status: 'unhealthy', error: error.message });
    }
  };

  const showNotification = useCallback((message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  }, []);

  const healthStatusColor = () => {
    if (!systemHealth) return '#gray';
    switch (systemHealth.status) {
      case 'healthy': return '#28a745';
      case 'degraded': return '#ffc107';
      default: return '#dc3545';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-main">
            <h1>🎯 Smart Resume Screening System</h1>
            <p>AI-Powered Candidate Matching with Advanced RAG Technology</p>
          </div>
          <div className="system-status">
            <div 
              className="status-indicator"
              style={{ backgroundColor: healthStatusColor() }}
              title={systemHealth ? `System Status: ${systemHealth.status}` : 'Checking...'}
            />
            <span className="status-text">
              {systemHealth ? systemHealth.status : 'checking...'}
            </span>
          </div>
        </div>
      </header>

      {notification && (
        <div className={`notification notification-${notification.type}`}>
          {notification.message}
          <button onClick={() => setNotification(null)}>×</button>
        </div>
      )}

      <nav className="nav-tabs">
        <button 
          className={activeTab === 'jobs' ? 'active' : ''} 
          onClick={() => setActiveTab('jobs')}
        >
          <span className="tab-icon">💼</span>
          Job Postings
        </button>
        <button 
          className={activeTab === 'resumes' ? 'active' : ''} 
          onClick={() => setActiveTab('resumes')}
        >
          <span className="tab-icon">📄</span>
          Resumes
        </button>
        <button 
          className={activeTab === 'matching' ? 'active' : ''} 
          onClick={() => setActiveTab('matching')}
        >
          <span className="tab-icon">🎯</span>
          Smart Matching
        </button>
        <button 
          className={activeTab === 'analytics' ? 'active' : ''} 
          onClick={() => setActiveTab('analytics')}
        >
          <span className="tab-icon">📊</span>
          Analytics
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'jobs' && (
          <JobManager 
            apiUrl={API_BASE_URL}
            setLoading={setLoading}
            showNotification={showNotification}
          />
        )}
        
        {activeTab === 'resumes' && (
          <ResumeManager 
            apiUrl={API_BASE_URL}
            setLoading={setLoading}
            showNotification={showNotification}
          />
        )}
        
        {activeTab === 'matching' && (
          <MatchingDashboard 
            apiUrl={API_BASE_URL}
            setLoading={setLoading}
            showNotification={showNotification}
          />
        )}
        
        {activeTab === 'analytics' && (
          <Analytics 
            apiUrl={API_BASE_URL}
            setLoading={setLoading}
            showNotification={showNotification}
          />
        )}
      </main>

      {loading && <LoadingSpinner />}
    </div>
  );
}

export default App;
