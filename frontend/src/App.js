import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Import components
import JobManager from './components/JobManager';
import ResumeManager from './components/ResumeManager';
import MatchingDashboard from './components/MatchingDashboard';
import Analytics from './components/Analytics';
import LoadingSpinner from './components/LoadingSpinner';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [dashboardStats, setDashboardStats] = useState({
    totalJobs: 0,
    totalResumes: 0,
    totalMatches: 0
  });

  useEffect(() => {
    checkSystemHealth();
    loadDashboardStats();
    // Check health every 30 seconds
    const interval = setInterval(() => {
      checkSystemHealth();
      if (activeTab === 'dashboard') {
        loadDashboardStats();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Health check failed:', error);
      setSystemHealth({ status: 'unhealthy' });
    }
  };

  const loadDashboardStats = async () => {
    try {
      const [jobsRes, resumesRes, analyticsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/v2/jobs`).catch(() => ({ data: [] })),
        axios.get(`${API_BASE_URL}/api/v2/resumes`).catch(() => ({ data: [] })),
        axios.get(`${API_BASE_URL}/api/v2/analytics/overview`).catch(() => ({ data: { total_matches: 0 } }))
      ]);
      
      setDashboardStats({
        totalJobs: jobsRes.data?.length || 0,
        totalResumes: resumesRes.data?.length || 0,
        totalMatches: analyticsRes.data?.total_matches || 0
      });
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
    }
  };

  const showNotification = (message, type) => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'healthy': case 'active': case 'completed': return '#28a745';
      case 'processing': return '#ffc107';
      case 'failed': case 'unhealthy': return '#dc3545';
      default: return '#6c757d';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🎯 Smart Resume Screening System</h1>
          <div className="system-status">
            <div 
              className="status-indicator"
              style={{ 
                backgroundColor: getStatusColor(systemHealth?.status),
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                marginRight: '8px'
              }}
            />
            <span>{systemHealth?.status || 'checking...'}</span>
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
          className={activeTab === 'dashboard' ? 'active' : ''} 
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button 
          className={activeTab === 'jobs' ? 'active' : ''} 
          onClick={() => setActiveTab('jobs')}
        >
          💼 Jobs ({dashboardStats.totalJobs})
        </button>
        <button 
          className={activeTab === 'resumes' ? 'active' : ''} 
          onClick={() => setActiveTab('resumes')}
        >
          📄 Resumes ({dashboardStats.totalResumes})
        </button>
        <button 
          className={activeTab === 'matching' ? 'active' : ''} 
          onClick={() => setActiveTab('matching')}
        >
          🎯 Matching
        </button>
        <button 
          className={activeTab === 'analytics' ? 'active' : ''} 
          onClick={() => setActiveTab('analytics')}
        >
          📊 Analytics
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <div className="dashboard">
            <h2>System Overview</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <h3>{dashboardStats.totalJobs}</h3>
                <p>Total Jobs</p>
              </div>
              <div className="stat-card">
                <h3>{dashboardStats.totalResumes}</h3>
                <p>Total Resumes</p>
              </div>
              <div className="stat-card">
                <h3>{dashboardStats.totalMatches}</h3>
                <p>Total Matches</p>
              </div>
              <div className="stat-card">
                <h3>{systemHealth?.status === 'healthy' ? '✅' : '❌'}</h3>
                <p>System Status</p>
              </div>
            </div>

            <div className="recent-activity">
              <h3>Quick Actions</h3>
              <div className="action-buttons">
                <button 
                  className="action-btn" 
                  onClick={() => setActiveTab('jobs')}
                >
                  💼 Manage Jobs
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => setActiveTab('resumes')}
                >
                  📄 Upload Resumes
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => setActiveTab('matching')}
                >
                  🎯 Find Matches
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => setActiveTab('analytics')}
                >
                  📊 View Analytics
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => {
                    checkSystemHealth();
                    loadDashboardStats();
                    showNotification('Data refreshed successfully!', 'success');
                  }}
                >
                  🔄 Refresh Status
                </button>
              </div>
            </div>
          </div>
        )}
        
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
