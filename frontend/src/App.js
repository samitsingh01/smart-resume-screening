import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [systemHealth, setSystemHealth] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [matches, setMatches] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);

  useEffect(() => {
    checkSystemHealth();
    loadJobs();
    loadResumes();
  }, []);

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Health check failed:', error);
      setSystemHealth({ status: 'unhealthy' });
    }
  };

  const loadJobs = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v2/jobs`);
      setJobs(response.data || []);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    }
  };

  const loadResumes = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v2/resumes`);
      setResumes(response.data || []);
    } catch (error) {
      console.error('Failed to load resumes:', error);
    }
  };

  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (!files.length) return;

    setLoading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        await axios.post(`${API_BASE_URL}/api/v2/resumes/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }
      
      showNotification('Files uploaded successfully!', 'success');
      loadResumes();
    } catch (error) {
      showNotification('Upload failed: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const findMatches = async (jobId) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v2/match/advanced?job_id=${jobId}&top_k=10`);
      setMatches(response.data || []);
      setSelectedJob(jobs.find(job => job.job_id === jobId));
      showNotification(`Found ${response.data?.length || 0} matching candidates!`, 'success');
    } catch (error) {
      showNotification('Matching failed: ' + error.message, 'error');
    } finally {
      setLoading(false);
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
          💼 Jobs ({jobs.length})
        </button>
        <button 
          className={activeTab === 'resumes' ? 'active' : ''} 
          onClick={() => setActiveTab('resumes')}
        >
          📄 Resumes ({resumes.length})
        </button>
        <button 
          className={activeTab === 'matching' ? 'active' : ''} 
          onClick={() => setActiveTab('matching')}
        >
          🎯 Matching
        </button>
        <button 
          className={activeTab === 'upload' ? 'active' : ''} 
          onClick={() => setActiveTab('upload')}
        >
          ⬆️ Upload
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <div className="dashboard">
            <h2>System Overview</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <h3>{jobs.length}</h3>
                <p>Total Jobs</p>
              </div>
              <div className="stat-card">
                <h3>{resumes.length}</h3>
                <p>Total Resumes</p>
              </div>
              <div className="stat-card">
                <h3>{matches.length}</h3>
                <p>Recent Matches</p>
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
                  onClick={() => setActiveTab('upload')}
                >
                  📁 Upload Resumes
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => setActiveTab('matching')}
                >
                  🎯 Find Matches
                </button>
                <button 
                  className="action-btn" 
                  onClick={() => {loadJobs(); loadResumes(); checkSystemHealth();}}
                >
                  🔄 Refresh Data
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="jobs-section">
            <h2>Job Postings</h2>
            {jobs.length === 0 ? (
              <div className="empty-state">
                <p>No jobs available. Create jobs using the API endpoint:</p>
                <code>POST /api/v2/jobs</code>
              </div>
            ) : (
              <div className="job-list">
                {jobs.map((job) => (
                  <div key={job.job_id} className="job-card">
                    <div className="card-header">
                      <h4>{job.title}</h4>
                      <span className={`badge ${job.status}`}>{job.status}</span>
                    </div>
                    <div className="card-content">
                      <p><strong>Company:</strong> {job.company}</p>
                      <p><strong>Location:</strong> {job.location}</p>
                      <p><strong>Experience:</strong> {job.experience_level}</p>
                      <p><strong>Skills Required:</strong> {job.required_skills_count}</p>
                      {job.remote_allowed && <span className="remote-badge">🌐 Remote OK</span>}
                    </div>
                    <div className="card-actions">
                      <button 
                        className="btn-primary"
                        onClick={() => findMatches(job.job_id)}
                        disabled={loading}
                      >
                        🎯 Find Matches
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'resumes' && (
          <div className="resumes-section">
            <h2>Uploaded Resumes</h2>
            {resumes.length === 0 ? (
              <div className="empty-state">
                <p>No resumes uploaded yet.</p>
                <button 
                  className="btn-primary"
                  onClick={() => setActiveTab('upload')}
                >
                  Upload Your First Resume
                </button>
              </div>
            ) : (
              <div className="resume-list">
                {resumes.map((resume) => (
                  <div key={resume.resume_id} className="resume-card">
                    <div className="card-header">
                      <h4>{resume.filename}</h4>
                      <span className={`badge ${resume.processing_status}`}>
                        {resume.processing_status}
                      </span>
                    </div>
                    <div className="card-content">
                      <p><strong>Type:</strong> {resume.file_type?.toUpperCase()}</p>
                      <p><strong>Size:</strong> {Math.round(resume.file_size / 1024)} KB</p>
                      <p><strong>Skills Found:</strong> {resume.extracted_skills_count || 0}</p>
                      {resume.quality_score && (
                        <div className="quality-score">
                          <span>Quality Score: </span>
                          <div className="score-bar">
                            <div 
                              className="score-fill"
                              style={{
                                width: `${resume.quality_score * 100}%`,
                                backgroundColor: resume.quality_score > 0.7 ? '#28a745' : '#ffc107'
                              }}
                            />
                            <span>{Math.round(resume.quality_score * 100)}%</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'matching' && (
          <div className="matching-section">
            <h2>Smart Candidate Matching</h2>
            
            <div className="matching-controls">
              <h3>Select Job for Matching</h3>
              {jobs.length === 0 ? (
                <p>No jobs available for matching.</p>
              ) : (
                <div className="job-selector">
                  {jobs.slice(0, 5).map((job) => (
                    <button
                      key={job.job_id}
                      className={`job-select-btn ${selectedJob?.job_id === job.job_id ? 'selected' : ''}`}
                      onClick={() => findMatches(job.job_id)}
                      disabled={loading}
                    >
                      <div className="job-info">
                        <strong>{job.title}</strong>
                        <span>{job.company}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedJob && (
              <div className="selected-job-info">
                <h3>Matches for: {selectedJob.title} at {selectedJob.company}</h3>
                {matches.length === 0 ? (
                  <p>No matches found. Try uploading more resumes or check processing status.</p>
                ) : (
                  <div className="matches-list">
                    {matches.map((match, index) => (
                      <div key={match.resume_id} className="match-card">
                        <div className="match-header">
                          <div className="candidate-info">
                            <h4>#{index + 1} - {match.filename}</h4>
                            <div className="scores">
                              <span className="overall-score">
                                Overall: {match.overall_score}%
                              </span>
                              <span className="skill-score">
                                Skills: {match.skill_match_score}%
                              </span>
                            </div>
                          </div>
                          <span className={`recommendation ${match.recommendation}`}>
                            {match.recommendation.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                        
                        <div className="match-details">
                          <div className="skills-section">
                            {match.matched_skills?.length > 0 && (
                              <div className="matched-skills">
                                <strong>✅ Matched Skills:</strong>
                                <div className="skill-tags">
                                  {match.matched_skills.slice(0, 5).map((skill, i) => (
                                    <span key={i} className="skill-tag matched">{skill}</span>
                                  ))}
                                  {match.matched_skills.length > 5 && (
                                    <span className="skill-tag">+{match.matched_skills.length - 5} more</span>
                                  )}
                                </div>
                              </div>
                            )}
                            
                            {match.missing_skills?.length > 0 && (
                              <div className="missing-skills">
                                <strong>❌ Missing Skills:</strong>
                                <div className="skill-tags">
                                  {match.missing_skills.slice(0, 3).map((skill, i) => (
                                    <span key={i} className="skill-tag missing">{skill}</span>
                                  ))}
                                  {match.missing_skills.length > 3 && (
                                    <span className="skill-tag">+{match.missing_skills.length - 3} more</span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                          
                          {match.explanation && (
                            <div className="explanation">
                              <strong>Analysis:</strong>
                              <p>{match.explanation}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="upload-section">
            <h2>Upload Resumes</h2>
            <div className="file-upload">
              <div className="upload-area">
                <div className="upload-icon">📁</div>
                <h3>Drag & Drop Files Here</h3>
                <p>or click to browse</p>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileUpload}
                  disabled={loading}
                  id="file-input"
                />
                <label htmlFor="file-input" className="btn-primary">
                  {loading ? 'Uploading...' : 'Choose Files'}
                </label>
              </div>
              
              <div className="upload-info">
                <h4>Supported Formats:</h4>
                <ul>
                  <li>📄 PDF files (.pdf)</li>
                  <li>📝 Word documents (.docx)</li>
                  <li>📃 Text files (.txt)</li>
                </ul>
                <p><strong>Maximum file size:</strong> 10MB</p>
                <p><strong>Multiple files:</strong> Supported</p>
              </div>
            </div>

            {loading && (
              <div className="progress-section">
                <div className="progress-bar">
                  <div className="progress-fill"></div>
                </div>
                <p>Processing files...</p>
              </div>
            )}
          </div>
        )}
      </main>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Processing...</p>
        </div>
      )}
    </div>
  );
}

export default App;
