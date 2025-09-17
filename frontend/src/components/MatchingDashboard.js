// frontend/src/components/MatchingDashboard.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const MatchingDashboard = ({ apiUrl, setLoading, showNotification }) => {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [matches, setMatches] = useState([]);
  const [matchingParams, setMatchingParams] = useState({
    top_k: 20,
    min_score: 0.0,
    experience_filter: '',
    skill_filter: ''
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const response = await axios.get(`${apiUrl}/api/v2/jobs`);
      setJobs(response.data.filter(job => job.embedding_status === 'completed'));
    } catch (error) {
      showNotification('Error loading jobs: ' + error.message, 'error');
    }
  };

  const findMatches = async (jobId) => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        job_id: jobId,
        top_k: matchingParams.top_k,
        min_score: matchingParams.min_score
      });
      
      if (matchingParams.experience_filter) {
        params.append('experience_filter', matchingParams.experience_filter);
      }

      const response = await axios.post(`${apiUrl}/api/v2/match/advanced?${params}`);
      setMatches(response.data);
      setSelectedJob(jobs.find(job => job.job_id === jobId));
      showNotification(`Found ${response.data.length} matching candidates!`, 'success');
    } catch (error) {
      showNotification('Error finding matches: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationColor = (recommendation) => {
    switch (recommendation) {
      case 'strongly_recommended': return '#28a745';
      case 'recommended': return '#17a2b8';
      case 'consider': return '#ffc107';
      default: return '#dc3545';
    }
  };

  const getRecommendationIcon = (recommendation) => {
    switch (recommendation) {
      case 'strongly_recommended': return '⭐';
      case 'recommended': return '✅';
      case 'consider': return '🤔';
      default: return '❌';
    }
  };

  const filteredJobs = jobs.filter(job =>
    job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.company.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="matching-dashboard">
      <div className="dashboard-header">
        <h2>Smart Candidate Matching</h2>
        <p>Advanced AI-powered resume matching with detailed scoring</p>
      </div>

      <div className="dashboard-content">
        <div className="jobs-panel">
          <div className="panel-header">
            <h3>Select Job for Matching</h3>
            <div className="search-box">
              <input
                type="text"
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="matching-params">
            <h4>Matching Parameters</h4>
            <div className="params-grid">
              <div className="param-group">
                <label>Top Candidates</label>
                <select
                  value={matchingParams.top_k}
                  onChange={(e) => setMatchingParams({...matchingParams, top_k: parseInt(e.target.value)})}
                >
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                  <option value={30}>Top 30</option>
                  <option value={50}>Top 50</option>
                </select>
              </div>
              
              <div className="param-group">
                <label>Minimum Score (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={matchingParams.min_score * 100}
                  onChange={(e) => setMatchingParams({...matchingParams, min_score: e.target.value / 100})}
                />
              </div>
              
              <div className="param-group">
                <label>Experience Filter</label>
                <select
                  value={matchingParams.experience_filter}
                  onChange={(e) => setMatchingParams({...matchingParams, experience_filter: e.target.value})}
                >
                  <option value="">All Levels</option>
                  <option value="entry">Entry Level</option>
                  <option value="mid">Mid Level</option>
                  <option value="senior">Senior Level</option>
                  <option value="lead">Lead/Principal</option>
                </select>
              </div>
            </div>
          </div>

          <div className="job-list-compact">
            {filteredJobs.map((job) => (
              <div key={job.job_id} className="job-item-compact">
                <div className="job-info">
                  <h4>{job.title}</h4>
                  <p>{job.company} • {job.location}</p>
                  <div className="job-meta">
                    <span className="experience-badge">{job.experience_level}</span>
                    <span className="skills-count">{job.required_skills_count} skills</span>
                  </div>
                </div>
                <button
                  className="btn-primary"
                  onClick={() => findMatches(job.job_id)}
                  disabled={job.embedding_status !== 'completed'}
                >
                  {job.embedding_status === 'completed' ? 'Find Matches' : 'Processing...'}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="matches-panel">
          {selectedJob ? (
            <>
              <div className="panel-header">
                <h3>Matching Results for {selectedJob.title}</h3>
                <div className="job-summary">
                  <span>{selectedJob.company}</span>
                  <span>•</span>
                  <span>{matches.length} candidates found</span>
                </div>
              </div>

              <div className="matches-list">
                {matches.map((match, index) => (
                  <div key={match.resume_id} className="match-card-detailed">
                    <div className="match-header">
                      <div className="candidate-info">
                        <h4>
                          {getRecommendationIcon(match.recommendation)}
                          #{index + 1} - {match.filename}
                        </h4>
                        <div className="scores-summary">
                          <div className="score-item">
                            <span>Overall: </span>
                            <strong style={{ color: match.overall_score >= 80 ? '#28a745' : match.overall_score >= 60 ? '#ffc107' : '#dc3545' }}>
                              {match.overall_score}%
                            </strong>
                          </div>
                          <div className="score-item">
                            <span>Skills: </span>
                            <strong>{match.skill_match_score}%</strong>
                          </div>
                          <div className="score-item">
                            <span>Experience: </span>
                            <strong>{match.experience_match_score}%</strong>
                          </div>
                        </div>
                      </div>
                      
                      <div className="recommendation-badge">
                        <span 
                          className="recommendation"
                          style={{ 
                            backgroundColor: getRecommendationColor(match.recommendation),
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: '15px',
                            fontSize: '12px',
                            fontWeight: 'bold'
                          }}
                        >
                          {match.recommendation.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className={`confidence confidence-${match.confidence_level}`}>
                          {match.confidence_level} confidence
                        </span>
                      </div>
                    </div>

                    <div className="match-details">
                      <div className="explanation">
                        <h5>Why This Candidate Matches:</h5>
                        <p>{match.explanation}</p>
                      </div>

                      <div className="skills-analysis">
                        <div className="matched-skills">
                          <h6>✅ Matched Skills ({match.matched_skills.length})</h6>
                          <div className="skill-tags">
                            {match.matched_skills.map((skill, i) => (
                              <span key={i} className="skill-tag matched">{skill}</span>
                            ))}
                          </div>
                        </div>

                        {match.missing_skills.length > 0 && (
                          <div className="missing-skills">
                            <h6>❌ Missing Skills ({match.missing_skills.length})</h6>
                            <div className="skill-tags">
                              {match.missing_skills.map((skill, i) => (
                                <span key={i} className="skill-tag missing">{skill}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="match-actions">
                        <button className="btn-secondary">
                          📄 View Resume
                        </button>
                        <button className="btn-secondary">
                          📧 Contact Candidate
                        </button>
                        <button className="btn-secondary">
                          ⭐ Shortlist
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {matches.length === 0 && (
                <div className="empty-matches">
                  <div className="empty-icon">🔍</div>
                  <h3>No matches found</h3>
                  <p>Try adjusting your matching parameters or check if resumes are processed.</p>
                </div>
              )}
            </>
          ) : (
            <div className="no-job-selected">
              <div className="placeholder-icon">🎯</div>
              <h3>Select a Job to Find Matches</h3>
              <p>Choose a job posting from the left panel to start finding the best matching candidates using our advanced AI algorithms.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
