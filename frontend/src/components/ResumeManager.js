// frontend/src/components/ResumeManager.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ResumeManager = ({ apiUrl, setLoading, showNotification }) => {
  const [resumes, setResumes] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  useEffect(() => {
    loadResumes();
  }, []);

  const loadResumes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${apiUrl}/api/v2/resumes`);
      setResumes(response.data);
    } catch (error) {
      showNotification('Error loading resumes: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (files) => {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
      if (!file.name.toLowerCase().match(/\.(pdf|docx|txt)$/)) {
        showNotification(`Invalid file format: ${file.name}. Please use PDF, DOCX, or TXT.`, 'error');
        continue;
      }
      
      if (file.size > 10 * 1024 * 1024) {
        showNotification(`File too large: ${file.name}. Maximum size is 10MB.`, 'error');
        continue;
      }

      const formData = new FormData();
      formData.append('file', file);

      try {
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
        
        await axios.post(`${apiUrl}/api/v2/resumes/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(prev => ({ ...prev, [file.name]: percentCompleted }));
          }
        });
        
        showNotification(`Resume "${file.name}" uploaded successfully!`, 'success');
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[file.name];
          return newProgress;
        });
        
      } catch (error) {
        showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[file.name];
          return newProgress;
        });
      }
    }
    
    loadResumes();
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#28a745';
      case 'processing': return '#ffc107';
      case 'failed': return '#dc3545';
      default: return '#6c757d';
    }
  };

  return (
    <div className="resume-manager">
      <div className="manager-header">
        <h2>Resume Management</h2>
        <div className="resume-stats">
          <span className="stat">Total Resumes: {resumes.length}</span>
          <span className="stat">
            Processed: {resumes.filter(r => r.processing_status === 'completed').length}
          </span>
        </div>
      </div>

      <div className="manager-content">
        <div className="upload-section">
          <h3>Upload Resumes</h3>
          
          <div 
            className={`file-upload-zone ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="upload-content">
              <div className="upload-icon">📁</div>
              <h4>Drag & Drop Files Here</h4>
              <p>or click to browse</p>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt"
                onChange={(e) => handleFileUpload(e.target.files)}
                style={{ display: 'none' }}
                id="file-input"
              />
              <label htmlFor="file-input" className="btn-secondary">
                Choose Files
              </label>
            </div>
            
            <div className="upload-info">
              <p>Supported formats: PDF, DOCX, TXT</p>
              <p>Maximum file size: 10MB</p>
              <p>Multiple files supported</p>
            </div>
          </div>

          {Object.keys(uploadProgress).length > 0 && (
            <div className="upload-progress">
              <h4>Uploading Files...</h4>
              {Object.entries(uploadProgress).map(([filename, progress]) => (
                <div key={filename} className="progress-item">
                  <span>{filename}</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <span>{progress}%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="list-section">
          <div className="section-header">
            <h3>Uploaded Resumes ({resumes.length})</h3>
            <div className="view-controls">
              <button 
                className="btn-secondary"
                onClick={loadResumes}
              >
                🔄 Refresh
              </button>
            </div>
          </div>
          
          <div className="resume-grid">
            {resumes.map((resume) => (
              <div key={resume.resume_id} className="resume-card">
                <div className="card-header">
                  <h4 title={resume.filename}>
                    {resume.filename.length > 30 
                      ? resume.filename.substring(0, 30) + '...' 
                      : resume.filename}
                  </h4>
                  <div className="file-type-badge">
                    {resume.file_type?.toUpperCase()}
                  </div>
                </div>
                
                <div className="card-content">
                  <div className="status-row">
                    <span>Processing:</span>
                    <span 
                      className="status-indicator"
                      style={{ color: getStatusColor(resume.processing_status) }}
                    >
                      {resume.processing_status}
                    </span>
                  </div>
                  
                  <div className="status-row">
                    <span>Embeddings:</span>
                    <span 
                      className="status-indicator"
                      style={{ color: getStatusColor(resume.embedding_status) }}
                    >
                      {resume.embedding_status}
                    </span>
                  </div>
                  
                  {resume.quality_score && (
                    <div className="quality-score">
                      <span>Quality Score:</span>
                      <div className="score-bar">
                        <div 
                          className="score-fill"
                          style={{ 
                            width: `${resume.quality_score * 100}%`,
                            backgroundColor: resume.quality_score > 0.7 ? '#28a745' : 
                                           resume.quality_score > 0.4 ? '#ffc107' : '#dc3545'
                          }}
                        />
                        <span className="score-text">
                          {Math.round(resume.quality_score * 100)}%
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {resume.extracted_skills_count > 0 && (
                    <div className="skills-info">
                      <span>Skills Extracted: {resume.extracted_skills_count}</span>
                    </div>
                  )}
                  
                  {resume.experience_level && (
                    <div className="experience-info">
                      <span>Experience: {resume.experience_level}</span>
                      {resume.experience_years && (
                        <span> ({resume.experience_years} years)</span>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="card-footer">
                  <small>
                    Uploaded: {new Date(resume.created_at).toLocaleDateString()}
                  </small>
                  <div className="card-actions">
                    <button 
                      className="btn-small"
                      onClick={() => window.open(`/api/v2/resumes/${resume.resume_id}/status`, '_blank')}
                    >
                      Details
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {resumes.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">📄</div>
              <h3>No resumes uploaded yet</h3>
              <p>Upload your first resume to get started with AI-powered matching!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResumeManager;={showNotification}
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
