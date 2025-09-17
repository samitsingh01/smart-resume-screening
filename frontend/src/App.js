// frontend/src/App.js
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
            showNotification('Error creating job: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="job-manager">
      <div className="manager-header">
        <h2>Job Management</h2>
        <div className="job-stats">
          <span className="stat">Total Jobs: {jobs.length}</span>
        </div>
      </div>

      <div className="manager-content">
        <div className="form-section">
          <h3>Create New Job Posting</h3>
          <form onSubmit={handleSubmit} className="enhanced-form">
            <div className="form-grid">
              <div className="form-group">
                <label>Job Title *</label>
                <input
                  type="text"
                  value={jobForm.title}
                  onChange={(e) => setJobForm({...jobForm, title: e.target.value})}
                  placeholder="e.g. Senior Software Engineer"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Company *</label>
                <input
                  type="text"
                  value={jobForm.company}
                  onChange={(e) => setJobForm({...jobForm, company: e.target.value})}
                  placeholder="e.g. TechCorp Inc"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Experience Level *</label>
                <select
                  value={jobForm.experience_level}
                  onChange={(e) => setJobForm({...jobForm, experience_level: e.target.value})}
                  required
                >
                  <option value="entry">Entry Level</option>
                  <option value="mid">Mid Level</option>
                  <option value="senior">Senior Level</option>
                  <option value="lead">Lead/Principal</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Job Type</label>
                <select
                  value={jobForm.job_type}
                  onChange={(e) => setJobForm({...jobForm, job_type: e.target.value})}
                >
                  <option value="full_time">Full Time</option>
                  <option value="part_time">Part Time</option>
                  <option value="contract">Contract</option>
                  <option value="remote">Remote</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Location *</label>
                <input
                  type="text"
                  value={jobForm.location}
                  onChange={(e) => setJobForm({...jobForm, location: e.target.value})}
                  placeholder="e.g. San Francisco, CA"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Department</label>
                <input
                  type="text"
                  value={jobForm.department}
                  onChange={(e) => setJobForm({...jobForm, department: e.target.value})}
                  placeholder="e.g. Engineering"
                />
              </div>
            </div>
            
            <div className="form-group full-width">
              <label>Job Description *</label>
              <textarea
                value={jobForm.description}
                onChange={(e) => setJobForm({...jobForm, description: e.target.value})}
                placeholder="Detailed job description..."
                rows={4}
                required
              />
            </div>
            
            <div className="form-group full-width">
              <label>Requirements * (comma-separated)</label>
              <textarea
                value={jobForm.requirements}
                onChange={(e) => setJobForm({...jobForm, requirements: e.target.value})}
                placeholder="Bachelor's degree, 3+ years experience, etc."
                rows={3}
                required
              />
            </div>
            
            <div className="form-group full-width">
              <label>Required Skills * (comma-separated)</label>
              <textarea
                value={jobForm.required_skills}
                onChange={(e) => setJobForm({...jobForm, required_skills: e.target.value})}
                placeholder="Python, React, AWS, Docker, etc."
                rows={2}
                required
              />
            </div>
            
            <div className="form-actions">
              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={jobForm.remote_allowed}
                    onChange={(e) => setJobForm({...jobForm, remote_allowed: e.target.checked})}
                  />
                  Remote Work Allowed
                </label>
              </div>
              
              <button type="submit" className="btn-primary">
                Create Job Posting
              </button>
            </div>
          </form>
        </div>

        <div className="list-section">
          <div className="section-header">
            <h3>Job Postings ({jobs.length})</h3>
            <div className="filters">
              <input
                type="text"
                placeholder="Filter by company..."
                value={filters.company}
                onChange={(e) => setFilters({...filters, company: e.target.value})}
              />
            </div>
          </div>
          
          <div className="job-list">
            {jobs.map((job) => (
              <div key={job.job_id} className="job-card">
                <div className="card-header">
                  <h4>{job.title}</h4>
                  <div className="status-badges">
                    <span className={`badge ${job.status}`}>{job.status}</span>
                    <span className={`badge ${job.embedding_status}`}>
                      {job.embedding_status === 'completed' ? '✓ Ready' : '⏳ Processing'}
                    </span>
                  </div>
                </div>
                
                <div className="card-content">
                  <p><strong>Company:</strong> {job.company}</p>
                  <p><strong>Location:</strong> {job.location}</p>
                  <p><strong>Experience:</strong> {job.experience_level}</p>
                  <p><strong>Skills:</strong> {job.required_skills_count} required</p>
                  {job.remote_allowed && <span className="remote-badge">🌐 Remote OK</span>}
                </div>
                
                <div className="card-footer">
                  <small>Created: {new Date(job.created_at).toLocaleDateString()}</small>
                  <button 
                    className="btn-secondary"
                    onClick={() => window.open(`/api/v2/jobs/${job.job_id}`, '_blank')}
                  >
                    View Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

