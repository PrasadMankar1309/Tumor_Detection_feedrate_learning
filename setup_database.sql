-- ═══════════════════════════════════════════════════════════════════════════════
-- BRAIN TUMOR DETECTION - DATABASE SETUP (PostgreSQL / Supabase)
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── USERS TABLE (Doctors/Patients) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  role VARCHAR(50) CHECK (role IN ('doctor', 'patient', 'admin')) NOT NULL,
  specialization VARCHAR(255),
  license_number VARCHAR(255),
  hospital_name VARCHAR(255),
  phone VARCHAR(20),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- ─── PATIENTS TABLE (Doctor-Patient Relationship) ───────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  age INT CHECK (age > 0 AND age <= 150),
  gender VARCHAR(20) CHECK (gender IN ('Male', 'Female', 'Other')),
  medical_history TEXT,
  allergies TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─── SCAN RESULTS TABLE (Brain Tumor Detection Records) ───────────────────────────
CREATE TABLE IF NOT EXISTS scan_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
  scan_date TIMESTAMP WITH TIME ZONE NOT NULL,
  mri_image_url TEXT,
  heatmap_image_url TEXT,
  prediction VARCHAR(100) NOT NULL CHECK (prediction IN ('glioma', 'meningioma', 'notumor', 'pituitary')),
  confidence FLOAT CHECK (confidence >= 0 AND confidence <= 100) NOT NULL,
  all_probabilities JSONB,
  status VARCHAR(50) CHECK (status IN ('completed', 'processing', 'failed')) DEFAULT 'processing',
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─── REPORTS TABLE (Generated PDF Reports) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_result_id UUID NOT NULL REFERENCES scan_results(id) ON DELETE CASCADE,
  report_url TEXT NOT NULL,
  file_name VARCHAR(255),
  generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  downloaded_count INT DEFAULT 0
);

-- ─── AUDIT LOG TABLE (Track all operations) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(255) NOT NULL,
  table_name VARCHAR(100),
  record_id UUID,
  old_data JSONB,
  new_data JSONB,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ─── INDEXES FOR PERFORMANCE ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_patients_user_id ON patients(user_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_patient_id ON scan_results(patient_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_doctor_id ON scan_results(doctor_id);
CREATE INDEX IF NOT EXISTS idx_scan_results_prediction ON scan_results(prediction);
CREATE INDEX IF NOT EXISTS idx_scan_results_created_at ON scan_results(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_scan_result_id ON reports(scan_result_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);

-- ─── RLS (ROW LEVEL SECURITY) ─────────────────────────────────────────────────
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Users can view their own profile
CREATE POLICY users_select_policy ON users FOR SELECT
  USING (auth.uid()::text = id::text OR role = 'admin');

-- Doctors can view their patients' data
CREATE POLICY patients_select_policy ON patients FOR SELECT
  USING (auth.uid()::text = user_id::text);

-- Doctors can view scans of their patients
CREATE POLICY scan_results_select_policy ON scan_results FOR SELECT
  USING (auth.uid()::text = doctor_id::text OR auth.uid()::text = (
    SELECT user_id FROM patients WHERE id = patient_id
  )::text);

-- ═════════════════════════════════════════════════════════════════════════════════
