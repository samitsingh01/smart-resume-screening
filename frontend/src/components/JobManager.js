// frontend/src/components/JobManager.js - Complete fixed version
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const JobManager = ({ apiUrl, setLoading, showNotification }) => {
  const [jobs, setJobs] = useState([]);
  const [jobForm, setJobForm] = useState({
    title: '',
    company: '',
    description: '',
    requirements: '',
    required_skills: '',
    experience_level: 'mid',
    location: '',
    salary_range: '',
    department: '',
    job_type: 'full_time',
    remote_allowed: false
  });
  const [filters, setFilters] = useState({
    company: '',
    status: '',
    skip: 0,
    limit: 20
  });

  useEffect(() => {
    loadJobs();
  }, [filters]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      const response = await axios.get(`${apiUrl}/api/v2/jobs?${params}`);
      setJobs(response.data);
    } catch (error) {
      showNotification('Error loading jobs: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const jobData = {
        ...jobForm,
        requirements: jobForm.requirements.split(',').map(r => r.trim()).filter(r => r),
        required_skills: jobForm.required_skills.split(',').map(s => s.trim()).filter(s => s)
      };
      
      await axios.post(`${apiUrl}/api/v2/jobs`, jobData);
      
      setJobForm({
        title: '', company: '', description: '', requirements: '',
        required_skills: '', experience_level: 'mid', location: '',
        salary_range: '', department: '', job_type: 'full_time', remote_allowed: false
      });
      
      loadJobs();
      showNotification('Job created successfully and is being processed!', 'success');
    } catch (error) {
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

export default JobManager;
