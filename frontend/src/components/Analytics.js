// frontend/src/components/Analytics.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Analytics = ({ apiUrl, setLoading, showNotification }) => {
  const [overview, setOverview] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [selectedResume, setSelectedResume] = useState(null);
  const [resumeAnalytics, setResumeAnalytics] = useState(null);

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const [overviewRes, performanceRes] = await Promise.all([
        axios.get(`${apiUrl}/api/v2/analytics/overview`),
        axios.get(`${apiUrl}/api/v2/performance/metrics`)
      ]);
      
      setOverview(overviewRes.data);
      setPerformanceMetrics(performanceRes.data);
    } catch (error) {
      showNotification('Error loading analytics: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadResumeAnalytics = async (resumeId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${apiUrl}/api/v2/analytics/resume/${resumeId}`);
      setResumeAnalytics(response.data);
    } catch (error) {
      showNotification('Error loading resume analytics: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    return num?.toLocaleString() || '0';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return '#28a745';
      case 'degraded': return '#ffc107';
      default: return '#dc3545';
    }
  };

  return (
    <div className="analytics-dashboard">
      <div className="dashboard-header">
        <h2>System Analytics & Performance</h2>
        <p>Comprehensive insights into your resume screening system</p>
      </div>

      {overview && (
        <div className="analytics-overview">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">🎯</div>
              <div className="stat-content">
                <h3>{formatNumber(overview.total_matches)}</h3>
                <p>Total Matches</p>
              </div>
            </div>
            
            <div className="stat-card">
              <div className="stat-icon">⭐</div>
              <div className="stat-content">
                <h3>{overview.total_matches > 0 ? Math.round((overview.total_matches / overview.total_resumes) * 100) : 0}%</h3>
                <p>Match Rate</p>
              </div>
            </div>
          </div>

          <div className="analytics-sections">
            <div className="section">
              <h3>Resume Processing Status</h3>
              <div className="status-chart">
                {Object.entries(overview.resume_status_distribution).map(([status, count]) => (
                  <div key={status} className="status-item">
                    <div className="status-bar">
                      <div 
                        className="status-fill"
                        style={{ 
                          width: `${(count / overview.total_resumes) * 100}%`,
                          backgroundColor: getStatusColor(status)
                        }}
                      />
                    </div>
                    <span className="status-label">{status}: {count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="section">
              <h3>Job Status Distribution</h3>
              <div className="status-chart">
                {Object.entries(overview.job_status_distribution).map(([status, count]) => (
                  <div key={status} className="status-item">
                    <div className="status-bar">
                      <div 
                        className="status-fill"
                        style={{ 
                          width: `${(count / overview.total_jobs) * 100}%`,
                          backgroundColor: getStatusColor(status)
                        }}
                      />
                    </div>
                    <span className="status-label">{status}: {count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="section">
              <h3>Top Skills in Demand</h3>
              <div className="skills-ranking">
                {overview.top_skills.slice(0, 10).map((skillData, index) => (
                  <div key={index} className="skill-rank-item">
                    <span className="rank">#{index + 1}</span>
                    <span className="skill-name">{skillData.skill}</span>
                    <span className="skill-count">{skillData.count} jobs</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {performanceMetrics && (
        <div className="performance-section">
          <h3>System Performance (Last 24 Hours)</h3>
          <div className="performance-grid">
            <div className="perf-card">
              <h4>Total Operations</h4>
              <div className="perf-value">{performanceMetrics.last_24_hours.total_operations}</div>
            </div>
            
            <div className="perf-card">
              <h4>Success Rate</h4>
              <div className="perf-value">
                {performanceMetrics.last_24_hours.total_operations > 0 
                  ? Math.round((performanceMetrics.last_24_hours.successful_operations / performanceMetrics.last_24_hours.total_operations) * 100)
                  : 0}%
              </div>
            </div>
            
            <div className="perf-card">
              <h4>Avg Processing Time</h4>
              <div className="perf-value">{performanceMetrics.last_24_hours.average_processing_time}s</div>
            </div>
            
            <div className="perf-card">
              <h4>System Status</h4>
              <div 
                className="perf-value"
                style={{ color: getStatusColor(performanceMetrics.system_status) }}
              >
                {performanceMetrics.system_status}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="resume-analytics-section">
        <h3>Individual Resume Analytics</h3>
        <div className="resume-search">
          <input
            type="text"
            placeholder="Enter Resume ID to analyze..."
            value={selectedResume || ''}
            onChange={(e) => setSelectedResume(e.target.value)}
          />
          <button 
            className="btn-primary"
            onClick={() => selectedResume && loadResumeAnalytics(selectedResume)}
            disabled={!selectedResume}
          >
            Analyze Resume
          </button>
        </div>

        {resumeAnalytics && (
          <div className="resume-analytics-results">
            <h4>Analytics for {resumeAnalytics.filename}</h4>
            
            <div className="resume-stats-grid">
              <div className="resume-stat">
                <label>Total Matches</label>
                <value>{resumeAnalytics.total_matches}</value>
              </div>
              
              <div className="resume-stat">
                <label>Average Score</label>
                <value>{resumeAnalytics.average_score}%</value>
              </div>
              
              <div className="resume-stat">
                <label>Best Score</label>
                <value>{resumeAnalytics.best_score}%</value>
              </div>
              
              <div className="resume-stat">
                <label>Quality Score</label>
                <value>{resumeAnalytics.quality_score ? Math.round(resumeAnalytics.quality_score * 100) : 'N/A'}%</value>
              </div>
            </div>

            {resumeAnalytics.skill_frequency && Object.keys(resumeAnalytics.skill_frequency).length > 0 && (
              <div className="skill-frequency">
                <h5>Most Matched Skills</h5>
                <div className="skill-freq-list">
                  {Object.entries(resumeAnalytics.skill_frequency)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 10)
                    .map(([skill, frequency]) => (
                      <div key={skill} className="skill-freq-item">
                        <span className="skill">{skill}</span>
                        <span className="frequency">{frequency} matches</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
