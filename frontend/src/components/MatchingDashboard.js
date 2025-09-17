import React, { useState, useEffect } from 'react';
import axios from 'axios';

const MatchingDashboard = ({ apiUrl, setLoading, showNotification }) => {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [matches, setMatches] = useState([]);
  const [matchingParams, setMatchingParams] = useState({
    top_k: 20,
    min_score: 0.0,
    experience_filter: ''
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const response = await axios.get(`${apiUrl}/api/v2/jobs`);
      setJobs(response.data || []);
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
      setMatches(response.data || []);
      setSelectedJob(jobs.find(job => job.job_id === jobId));
      
      const matchCount = response.data?.length || 0;
      showNotification(`Found ${matchCount} matching candidates!`, matchCount > 0 ? 'success' : 'error');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      showNotification('Error finding matches: ' + errorMsg, 'error');
      setMatches([]);
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

  const getScoreColor = (score) => {
    if (score >= 80) return '#28a745';
    if (score >= 60) return '#ffc107';
    return '#dc3545';
  };

  const filteredJobs = jobs.filter(job =>
    job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.company.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="matching-dashboard">
      <div className="dashboard-header">
        <h2>Smart Candidate Matching</h2>
        <p>AI-powered resume matching with detailed scoring and analysis</p>
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
            {filteredJobs.length === 0 ? (
              <div className="no-jobs">
                <p>No jobs found. {searchQuery ? 'Try adjusting your search.' : 'Create some jobs first!'}</p>
              </div>
            ) : (
              filteredJobs.map((job) => (
                <div key={job.job_id} className="job-item-compact">
                  <div className="job-info">
                    <h4>{job.title}</h4>
                    <p>{job.company} • {job.location}</p>
                    <div className="job-meta">
                      <span className="experience-badge">{job.experience_level}</span>
                      <span className="skills-count">{job.required_skills_count} skills</span>
                      {job.remote_allowed && <span className="remote-badge">🌐 Remote</span>}
                    </div>
                    <div className="job-status">
                      <span className={`status-badge ${job.embedding_status}`}>
                        {job.embedding_status === 'completed' ? 'Ready' : 'Processing'}
                      </span>
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
              ))
            )}
          </div>
        </div>

        <div className="matches-panel">
          {selectedJob ? (
            <>
              <div className="panel-header">
                <h3>Matching Results</h3>
                <div className="job-summary">
                  <div className="selected-job-info">
                    <h4>{selectedJob.title}</h4>
                    <p>{selectedJob.company} • {selectedJob.location}</p>
                    <span className="match-count">{matches.length} candidates found</span>
                  </div>
                </div>
              </div>

              <div className="matches-list">
                {matches.length === 0 ? (
                  <div className="empty-matches">
                    <div className="empty-icon">🔍</div>
                    <h3>No matches found</h3>
                    <p>Try adjusting your matching parameters or check if resumes are processed.</p>
                    <div className="suggestions">
                      <p><strong>Suggestions:</strong></p>
                      <ul>
                        <li>Lower the minimum score threshold</li>
                        <li>Remove experience level filters</li>
                        <li>Upload more resumes</li>
                        <li>Check if resumes are fully processed</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  matches.map((match, index) => (
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
                              <strong style={{ color: getScoreColor(match.overall_score) }}>
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
                        {match.explanation && (
                          <div className="explanation">
                            <h5>Analysis:</h5>
                            <p>{match.explanation}</p>
                          </div>
                        )}

                        <div className="skills-analysis">
                          {match.matched_skills && match.matched_skills.length > 0 && (
                            <div className="matched-skills">
                              <h6>✅ Matched Skills ({match.matched_skills.length})</h6>
                              <div className="skill-tags">
                                {match.matched_skills.map((skill, i) => (
                                  <span key={i} className="skill-tag matched">{skill}</span>
                                ))}
                              </div>
                            </div>
                          )}

                          {match.missing_skills && match.missing_skills.length > 0 && (
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
                          <button className="btn-secondary" title="View resume details">
                            📄 View Resume
                          </button>
                          <button className="btn-secondary" title="Contact candidate">
                            📧 Contact
                          </button>
                          <button className="btn-secondary" title="Add to shortlist">
                            ⭐ Shortlist
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="no-job-selected">
              <div className="placeholder-icon">🎯</div>
              <h3>Select a Job to Find Matches</h3>
              <p>Choose a job posting from the left panel to start finding the best matching candidates using our advanced AI algorithms.</p>
              <div className="features-list">
                <h4>Our Matching Features:</h4>
                <ul>
                  <li>🧠 AI-powered semantic matching</li>
                  <li>⚡ Real-time skill analysis</li>
                  <li>📊 Comprehensive scoring system</li>
                  <li>🎯 Experience level filtering</li>
                  <li>📈 Confidence indicators</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MatchingDashboard;
