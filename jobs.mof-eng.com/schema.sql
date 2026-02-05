-- Core schema for MOF Jobs Portal

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('user','admin') NOT NULL DEFAULT 'user',
  gender ENUM('male','female','others') DEFAULT NULL,
  areacode VARCHAR(10) DEFAULT NULL,
  phone VARCHAR(20) DEFAULT NULL,
  age INT DEFAULT NULL,
  address VARCHAR(255) DEFAULT NULL,
  address2 VARCHAR(255) DEFAULT NULL,
  city VARCHAR(100) DEFAULT NULL,
  country VARCHAR(100) DEFAULT NULL,
  profile_photo_path VARCHAR(255) DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Extend existing job_applications table to support dashboards/filters
ALTER TABLE job_applications
  ADD COLUMN IF NOT EXISTS user_id INT NULL,
  ADD COLUMN IF NOT EXISTS position VARCHAR(120) NULL,
  ADD COLUMN IF NOT EXISTS years_experience TINYINT UNSIGNED NULL,
  ADD COLUMN IF NOT EXISTS source ENUM('Website','LinkedIn','Referral','Walk-in','Other') DEFAULT 'Website',
  ADD COLUMN IF NOT EXISTS status ENUM('New','Screening','Interview','Offer','Hired','Rejected') DEFAULT 'New',
  ADD COLUMN IF NOT EXISTS stage_notes TEXT NULL,
  ADD COLUMN IF NOT EXISTS expected_salary DECIMAL(12,2) NULL,
  ADD COLUMN IF NOT EXISTS cv_filename VARCHAR(255) NULL;

-- Admin comments on user profiles
CREATE TABLE IF NOT EXISTS user_comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  admin_id INT NOT NULL,
  comment TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
