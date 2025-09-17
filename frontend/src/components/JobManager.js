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
      showNotification
