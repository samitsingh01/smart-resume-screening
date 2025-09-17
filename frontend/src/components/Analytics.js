import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Analytics = ({ apiUrl, setLoading, showNotification }) => {
  const [overview, setOverview] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const [overviewRes, performanceRes] = await Promise.all([
        axios.get(`${apiUrl}/api/v2/analytics/overview`).catch(err => {
          console.error('Analytics overview failed:', err);
          return { data: null };
        }),
        axios.get(`${apiUrl}/api/v2/performance/metrics`).catch(err => {
          console.error('Performance metrics failed:', err);
          return { data: null };
        })
      ]);
      
      setOverview(overviewRes.data);
      setPerformanceMetrics(performanceRes.data);
      
      if (!overviewRes.data && !performanceRes.data) {
        showNotification('Unable to load analytics data', 'error');
      }
    } catch (error) {
      showNotification('Error loading analytics: ' + error.message, 'error');
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

  const calculatePercentage = (value, total) => {
    if (!total || total === 0) return 0;
    return Math.round((value / total) * 100);
  };

  return (
    <div className="analytics-dashboard">
      <div className="dashboard-header">
        <h2>System Analytics & Performance</h2>
        <p>Comprehensive insights into your resume screening system</p>
        <button 
          className="btn-secondary"
          onClick={loadAnalyticsData}
        >
          🔄 Refresh Data
        </button>
      </div>

      {overview ? (
        <div className="analytics-overview">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">💼</div>
              <div className="stat-content">
                <h3>{formatNumber(overview.total_jobs)}</h3>
                <p>Total Jobs</p>
              </div>
            </div>
            
            <div className="stat-card">
              <div className="stat-icon">📄</div>
              <div className="stat-content">
                <h3>{formatNumber(overview.total_resumes)}</h3>
                <p>Total Resumes</p>
              </div>
            </div>
            
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
                <h3>{overview.total_matches > 0 && overview.total_resumes > 0 ? 
                  Math.round((overview.total_matches / overview.total_resumes) * 100) : 0}%</h3>
                <p>Match Rate</p>
              </div>
            </div>
          </div>

          <div className="analytics-sections">
            {overview.resume_status_distribution && Object.keys(overview.resume_status_distribution).length > 0 && (
              <div className="section">
                <h3>Resume Processing Status</h3>
                <div className="status-chart">
                  {Object.entries(overview.resume_status_distribution).map(([status, count]) => (
                    <div key={status} className="status-item">
                      <div className="status-info">
                        <span className="status-label">{status}</span>
                        <span className="status-count">{count}</span>
                        <span className="status-percent">
                          ({calculatePercentage(count, overview.total_resumes)}%)
                        </span>
                      </div>
                      <div className="status-bar">
                        <div 
                          className="status-fill"
                          style={{ 
                            width: `${calculatePercentage(count, overview.total_resumes)}%`,
                            backgroundColor: getStatusColor(status)
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {overview.job_status_distribution && Object.keys(overview.job_status_distribution).length > 0 && (
              <div className="section">
                <h3>Job Status Distribution</h3>
                <div className="status-chart">
                  {Object.entries(overview.job_status_distribution).map(([status, count]) => (
                    <div key={status} className="status-item">
                      <div className="status-info">
                        <span className="status-label">{status}</span>
                        <span className="status-count">{count}</span>
                        <span className="status-percent">
                          ({calculatePercentage(count, overview.total_jobs)}%)
                        </span>
                      </div>
                      <div className="status-bar">
                        <div 
                          className="status-fill"
                          style={{ 
                            width: `${calculatePercentage(count, overview.total_jobs)}%`,
                            backgroundColor: getStatusColor(status)
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {overview.top_skills && overview.top_skills.length > 0 && (
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
            )}
          </div>
        </div>
      ) : (
        <div className="analytics-placeholder">
          <div className="placeholder-icon">📊</div>
          <h3>Analytics Data Unavailable</h3>
          <p>Analytics data is currently not available. This might be because:</p>
          <ul>
            <li>The system is still initializing</li>
            <li>Database connection issues</li>
            <li>No data has been processed yet</li>
          </ul>
          <button 
            className="btn-primary"
            onClick={loadAnalyticsData}
          >
            Try Again
          </button>
        </div>
      )}

      {performanceMetrics ? (
        <div className="performance-section">
          <h3>System Performance (Last 24 Hours)</h3>
          <div className="performance-grid">
            <div className="perf-card">
              <h4>Total Operations</h4>
              <div className="perf-value">{performanceMetrics.last_24_hours.total_operations}</div>
              <div className="perf-subtitle">API calls processed</div>
            </div>
            
            <div className="perf-card">
              <h4>Success Rate</h4>
              <div className="perf-value">
                {performanceMetrics.last_24_hours.total_operations > 0 
                  ? Math.round((performanceMetrics.last_24_hours.successful_operations / performanceMetrics.last_24_hours.total_operations) * 100)
                  : 0}%
              </div>
              <div className="perf-subtitle">
                {performanceMetrics.last_24_hours.successful_operations}/{performanceMetrics.last_24_hours.total_operations} successful
              </div>
            </div>
            
            <div className="perf-card">
              <h4>Avg Processing Time</h4>
              <div className="perf-value">{performanceMetrics.last_24_hours.average_processing_time}s</div>
              <div className="perf-subtitle">Per operation</div>
            </div>
            
            <div className="perf-card">
              <h4>System Status</h4>
              <div 
                className="perf-value"
                style={{ color: getStatusColor(performanceMetrics.system_status) }}
              >
                {performanceMetrics.system_status}
              </div>
              <div className="perf-subtitle">
                Last updated: {new Date(performanceMetrics.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="performance-placeholder">
          <h3>Performance Metrics</h3>
          <p>Performance data is currently unavailable.</p>
        </div>
      )}

      <div className="system-info-section">
        <h3>System Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <h4>API Version</h4>
            <p>v2.0.0</p>
          </div>
          <div className="info-item">
            <h4>Features</h4>
            <ul>
              <li>✅ Resume Processing</li>
              <li>✅ Job Management</li>
              <li>✅ AI Matching</li>
              <li>✅ Vector Search</li>
              <li>✅ Analytics</li>
            </ul>
          </div>
          <div className="info-item">
            <h4>Data Generated</h4>
            <p>{overview ? new Date(overview.generated_at).toLocaleString() : 'N/A'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
