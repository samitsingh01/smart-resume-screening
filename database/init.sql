# database/init.sql (Enhanced)
-- Create database and user
CREATE DATABASE resume_screening;
CREATE USER app_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE resume_screening TO app_user;

-- Connect to the database
\c resume_screening app_user;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enhanced tables
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT[] NOT NULL,
    required_skills TEXT[] NOT NULL,
    experience_level VARCHAR(50) NOT NULL,
    location VARCHAR(255) NOT NULL,
    salary_range VARCHAR(100),
    department VARCHAR(100),
    job_type VARCHAR(50) DEFAULT 'full_time',
    remote_allowed BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',
    embedding_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_content TEXT,
    processed_content TEXT,
    extracted_skills TEXT[],
    experience_years INTEGER,
    experience_level VARCHAR(50),
    education JSONB,
    certifications TEXT[],
    contact_info JSONB,
    file_size INTEGER,
    file_type VARCHAR(50),
    processing_status VARCHAR(50) DEFAULT 'pending',
    embedding_status VARCHAR(50) DEFAULT 'pending',
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_resume_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) NOT NULL,
    skill_match_score DECIMAL(5,2),
    experience_match_score DECIMAL(5,2),
    education_match_score DECIMAL(5,2),
    matched_skills TEXT[],
    missing_skills TEXT[],
    explanation TEXT,
    confidence_level VARCHAR(20),
    recommendation VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, resume_id)
);

CREATE TABLE IF NOT EXISTS resume_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id UUID REFERENCES resumes(id) ON DELETE CASCADE,
    total_matches INTEGER DEFAULT 0,
    avg_match_score DECIMAL(5,2),
    best_match_score DECIMAL(5,2),
    skill_frequency JSONB,
    match_trends JSONB,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    operation VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details JSONB,
    error_message TEXT,
    processing_time DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create optimized indexes for EC2 Large performance
CREATE INDEX CONCURRENTLY idx_jobs_status ON jobs(status);
CREATE INDEX CONCURRENTLY idx_jobs_company ON jobs(company);
CREATE INDEX CONCURRENTLY idx_jobs_experience_level ON jobs(experience_level);
CREATE INDEX CONCURRENTLY idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX CONCURRENTLY idx_jobs_embedding_status ON jobs(embedding_status);

CREATE INDEX CONCURRENTLY idx_resumes_status ON resumes(processing_status);
CREATE INDEX CONCURRENTLY idx_resumes_created_at ON resumes(created_at DESC);
CREATE INDEX CONCURRENTLY idx_resumes_embedding_status ON resumes(embedding_status);
CREATE INDEX CONCURRENTLY idx_resumes_experience_level ON resumes(experience_level);

CREATE INDEX CONCURRENTLY idx_matches_job_id ON job_resume_matches(job_id);
CREATE INDEX CONCURRENTLY idx_matches_resume_id ON job_resume_matches(resume_id);
CREATE INDEX CONCURRENTLY idx_matches_score ON job_resume_matches(overall_score DESC);
CREATE INDEX CONCURRENTLY idx_matches_created_at ON job_resume_matches(created_at DESC);

CREATE INDEX CONCURRENTLY idx_logs_entity ON processing_logs(entity_type, entity_id);
CREATE INDEX CONCURRENTLY idx_logs_created_at ON processing_logs(created_at DESC);

-- Create GIN indexes for array and JSONB columns
CREATE INDEX CONCURRENTLY idx_jobs_skills_gin ON jobs USING GIN(required_skills);
CREATE INDEX CONCURRENTLY idx_resumes_skills_gin ON resumes USING GIN(extracted_skills);
CREATE INDEX CONCURRENTLY idx_resumes_education_gin ON resumes USING GIN(education);
CREATE INDEX CONCURRENTLY idx_matches_matched_skills_gin ON job_resume_matches USING GIN(matched_skills);

-- Insert enhanced sample data
INSERT INTO jobs (title, company, description, requirements, required_skills, experience_level, location, department, job_type, remote_allowed) VALUES 
(
    'Senior Full Stack Engineer',
    'TechCorp Inc',
    'We are seeking a senior full stack engineer to lead our platform development team and architect scalable solutions.',
    ARRAY['Bachelor''s degree in Computer Science or related field', '5+ years of full stack development experience', 'Experience with microservices architecture', 'Strong leadership and mentoring skills'],
    ARRAY['Python', 'React', 'Node.js', 'AWS', 'Docker', 'Kubernetes', 'PostgreSQL', 'Redis', 'GraphQL'],
    'senior',
    'San Francisco, CA',
    'Engineering',
    'full_time',
    true
),
(
    'Data Scientist - Machine Learning',
    'AI Solutions Ltd',
    'Join our data science team to build cutting-edge ML models for predictive analytics and recommendation systems.',
    ARRAY['Master''s degree in Data Science, Statistics, or related field', '3+ years of ML experience', 'Strong statistical background', 'Experience with deep learning frameworks'],
    ARRAY['Python', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy', 'SQL', 'Scikit-learn', 'Apache Spark', 'MLOps'],
    'mid',
    'New York, NY',
    'Data Science',
    'full_time',
    false
),
(
    'DevOps Engineer',
    'CloudFirst Corp',
    'Looking for a DevOps engineer to manage our cloud infrastructure and implement CI/CD pipelines.',
    ARRAY['Bachelor''s degree in Engineering or related field', '4+ years of DevOps experience', 'Experience with cloud platforms', 'Knowledge of infrastructure as code'],
    ARRAY['AWS', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins', 'Git', 'Linux', 'Monitoring', 'Ansible'],
    'mid',
    'Austin, TX',
    'Infrastructure',
    'full_time',
    true
);

-- Create trigger for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
