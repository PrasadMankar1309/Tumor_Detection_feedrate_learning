# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE SERVICE - SUPABASE CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
import hashlib
from supabase import create_client, Client
import json

# ─── Environment Variables ───────────────────────────────────────────────────────
SUPABASE_URL = "https://tmfvtzwklomwdnhygpxx.supabase.co"
SUPABASE_KEY = "sb_publishable_yB9iPWcmKXFJoAgeqjUr7A_78Ysnj4H"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ═════════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT CRUD OPERATIONS
# ═════════════════════════════════════════════════════════════════════════════════

class UserService:
    """Handle user registration, authentication, and management"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def register_user(email: str, password: str, full_name: str, role: str, 
                     specialization: Optional[str] = None, 
                     license_number: Optional[str] = None,
                     hospital_name: Optional[str] = None,
                     phone: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user (Doctor or Patient)"""
        try:
            # Validate input
            if not email or not password or not full_name or not role:
                return {'success': False, 'error': 'Missing required fields (email, password, full_name, role)', 'data': None}
            
            if len(password) < 6:
                return {'success': False, 'error': 'Password must be at least 6 characters', 'data': None}
            
            # Check if email already exists
            try:
                existing = supabase.table('users').select('id').eq('email', email).execute()
                if existing.data and len(existing.data) > 0:
                    return {'success': False, 'error': 'Email already registered', 'data': None}
            except Exception as check_error:
                print(f"[!] Warning: Could not verify existing email: {check_error}")
                # Continue anyway - Supabase unique constraint will catch duplicates

            password_hash = UserService.hash_password(password)
            
            user_data = {
                'email': email,
                'password_hash': password_hash,
                'full_name': full_name,
                'role': role,
                'specialization': specialization,
                'license_number': license_number,
                'hospital_name': hospital_name,
                'phone': phone,
                'is_active': True
            }

            response = supabase.table('users').insert(user_data).execute()
            
            if response.data:
                return {
                    'success': True,
                    'message': 'User registered successfully',
                    'data': response.data[0],
                    'user_id': response.data[0]['id']
                }
            return {'success': False, 'error': 'Registration failed', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def login_user(email: str, password: str) -> Dict[str, Any]:
        """Authenticate user login"""
        try:
            # ─── HARDCODED DUMMY LOGIN ──────────────────────────────────────────────
            if email == "admin@test.com" and password == "admin123":
                return {
                    'success': True,
                    'message': 'Login successful (Dummy Admin)',
                    'data': {
                        'user_id': '00000000-0000-0000-0000-000000000000',
                        'email': 'admin@test.com',
                        'full_name': 'Administrator',
                        'role': 'admin',
                        'hospital_name': 'Test Hospital'
                    }
                }
            # ────────────────────────────────────────────────────────────────────────

            password_hash = UserService.hash_password(password)
            
            response = supabase.table('users').select('*').eq('email', email).execute()
            
            if not response.data:
                return {'success': False, 'error': 'Invalid email or password', 'data': None}

            user = response.data[0]
            
            if user['password_hash'] != password_hash:
                return {'success': False, 'error': 'Invalid email or password', 'data': None}

            if not user['is_active']:
                return {'success': False, 'error': 'Account is inactive', 'data': None}

            # Create session token (in production, use JWT)
            return {
                'success': True,
                'message': 'Login successful',
                'data': {
                    'user_id': user['id'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'role': user['role'],
                    'hospital_name': user['hospital_name']
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_user_by_id(user_id: str) -> Dict[str, Any]:
        """Get user details by ID"""
        try:
            # Hardcoded dummy user check
            if user_id == '00000000-0000-0000-0000-000000000000':
                return {
                    'success': True,
                    'data': {
                        'id': '00000000-0000-0000-0000-000000000000',
                        'email': 'admin@test.com',
                        'full_name': 'Administrator',
                        'role': 'admin',
                        'hospital_name': 'Test Hospital',
                        'is_active': True
                    }
                }

            response = supabase.table('users').select('*').eq('id', user_id).execute()
            
            if response.data:
                return {'success': True, 'data': response.data[0]}
            return {'success': False, 'error': 'User not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def update_user(user_id: str, **kwargs) -> Dict[str, Any]:
        """Update user profile"""
        try:
            kwargs['updated_at'] = datetime.now().isoformat()
            response = supabase.table('users').update(kwargs).eq('id', user_id).execute()
            
            if response.data:
                return {'success': True, 'message': 'User updated successfully', 'data': response.data[0]}
            return {'success': False, 'error': 'Update failed', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}


# ═════════════════════════════════════════════════════════════════════════════════
# PATIENT MANAGEMENT CRUD OPERATIONS
# ═════════════════════════════════════════════════════════════════════════════════

class PatientService:
    """Handle patient information management"""

    @staticmethod
    def create_patient(user_id: str, age: int, gender: str, 
                      medical_history: Optional[str] = None,
                      allergies: Optional[str] = None) -> Dict[str, Any]:
        """Create patient record"""
        try:
            patient_data = {
                'user_id': user_id,
                'age': age,
                'gender': gender,
                'medical_history': medical_history,
                'allergies': allergies
            }

            response = supabase.table('patients').insert(patient_data).execute()
            
            if response.data:
                return {'success': True, 'message': 'Patient created successfully', 'data': response.data[0]}
            return {'success': False, 'error': 'Patient creation failed', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_patient(patient_id: str) -> Dict[str, Any]:
        """Get patient details"""
        try:
            response = supabase.table('patients').select('*').eq('id', patient_id).execute()
            
            if response.data:
                return {'success': True, 'data': response.data[0]}
            return {'success': False, 'error': 'Patient not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_patient_by_user_id(user_id: str) -> Dict[str, Any]:
        """Get patient record by user ID"""
        try:
            # Hardcoded dummy patient check
            if user_id == '00000000-0000-0000-0000-000000000000':
                return {
                    'success': True,
                    'data': {
                        'id': '00000000-0000-0000-0000-000000000000',
                        'user_id': '00000000-0000-0000-0000-000000000000',
                        'age': 30,
                        'gender': 'Male',
                        'medical_history': 'None',
                        'allergies': 'None'
                    }
                }

            response = supabase.table('patients').select('*').eq('user_id', user_id).execute()
            
            if response.data:
                return {'success': True, 'data': response.data[0]}
            return {'success': False, 'error': 'Patient record not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def update_patient(patient_id: str, **kwargs) -> Dict[str, Any]:
        """Update patient information"""
        try:
            kwargs['updated_at'] = datetime.now().isoformat()
            response = supabase.table('patients').update(kwargs).eq('id', patient_id).execute()
            
            if response.data:
                return {'success': True, 'message': 'Patient updated successfully', 'data': response.data[0]}
            return {'success': False, 'error': 'Update failed', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_all_patients_for_doctor(doctor_id: str) -> Dict[str, Any]:
        """Get all patients assigned to a doctor"""
        try:
            # Get scan results for this doctor
            response = supabase.table('scan_results').select(
                'patient_id, patients(*, users(*))'
            ).eq('doctor_id', doctor_id).execute()
            
            # Get unique patients
            patients = []
            patient_ids = set()
            
            for scan in response.data:
                if scan['patients']['id'] not in patient_ids:
                    patients.append(scan['patients'])
                    patient_ids.add(scan['patients']['id'])
            
            return {'success': True, 'data': patients}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}


# ═════════════════════════════════════════════════════════════════════════════════
# SCAN RESULTS CRUD OPERATIONS
# ═════════════════════════════════════════════════════════════════════════════════

class ScanService:
    """Handle brain tumor scan results and predictions"""

    @staticmethod
    def create_scan_result(patient_id: str, doctor_id: str, 
                          prediction: str, confidence: float,
                          mri_image_url: Optional[str] = None,
                          heatmap_image_url: Optional[str] = None,
                          all_probabilities: Optional[Dict] = None,
                          notes: Optional[str] = None) -> Dict[str, Any]:
        """Save scan result to database"""
        try:
            scan_data = {
                'patient_id': patient_id,
                'doctor_id': doctor_id,
                'scan_date': datetime.now().isoformat(),
                'prediction': prediction,
                'confidence': confidence,
                'mri_image_url': mri_image_url,
                'heatmap_image_url': heatmap_image_url,
                'all_probabilities': json.dumps(all_probabilities) if all_probabilities else None,
                'status': 'completed',
                'notes': notes
            }

            response = supabase.table('scan_results').insert(scan_data).execute()
            
            if response.data:
                return {
                    'success': True, 
                    'message': 'Scan result saved successfully',
                    'data': response.data[0],
                    'scan_id': response.data[0]['id']
                }
            return {'success': False, 'error': 'Failed to save scan result', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_scan_result(scan_id: str) -> Dict[str, Any]:
        """Get a specific scan result"""
        try:
            response = supabase.table('scan_results').select('*').eq('id', scan_id).execute()
            
            if response.data:
                return {'success': True, 'data': response.data[0]}
            return {'success': False, 'error': 'Scan not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_patient_scans(patient_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get all scans for a patient"""
        try:
            response = supabase.table('scan_results').select('*').eq(
                'patient_id', patient_id
            ).order('scan_date', desc=True).range(offset, offset + limit - 1).execute()
            
            return {'success': True, 'data': response.data, 'count': len(response.data)}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_doctor_scans(doctor_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get all scans performed by a doctor"""
        try:
            response = supabase.table('scan_results').select('*').eq(
                'doctor_id', doctor_id
            ).order('scan_date', desc=True).range(offset, offset + limit - 1).execute()
            
            return {'success': True, 'data': response.data, 'count': len(response.data)}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_scan_statistics(doctor_id: str = None) -> Dict[str, Any]:
        """Get scan statistics (total scans, tumor types, accuracy)"""
        try:
            if doctor_id:
                response = supabase.table('scan_results').select('prediction, confidence').eq('doctor_id', doctor_id).execute()
            else:
                response = supabase.table('scan_results').select('prediction, confidence').execute()
            
            scans = response.data
            
            stats = {
                'total_scans': len(scans),
                'by_prediction': {},
                'average_confidence': 0,
                'accuracy_metrics': {}
            }
            
            total_confidence = 0
            for scan in scans:
                pred = scan['prediction']
                stats['by_prediction'][pred] = stats['by_prediction'].get(pred, 0) + 1
                total_confidence += scan['confidence']
            
            if scans:
                stats['average_confidence'] = round(total_confidence / len(scans), 2)
            
            return {'success': True, 'data': stats}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def update_scan_result(scan_id: str, **kwargs) -> Dict[str, Any]:
        """Update scan result"""
        try:
            kwargs['updated_at'] = datetime.now().isoformat()
            response = supabase.table('scan_results').update(kwargs).eq('id', scan_id).execute()
            
            if response.data:
                return {'success': True, 'message': 'Scan updated successfully', 'data': response.data[0]}
            return {'success': False, 'error': 'Update failed', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def delete_scan_result(scan_id: str) -> Dict[str, Any]:
        """Delete a scan result"""
        try:
            response = supabase.table('scan_results').delete().eq('id', scan_id).execute()
            return {'success': True, 'message': 'Scan deleted successfully'}

        except Exception as e:
            return {'success': False, 'error': str(e)}


# ═════════════════════════════════════════════════════════════════════════════════
# REPORT MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════════

class ReportService:
    """Handle PDF report generation and storage"""

    @staticmethod
    def create_report(scan_result_id: str, report_url: str, file_name: str) -> Dict[str, Any]:
        """Save report metadata to database"""
        try:
            report_data = {
                'scan_result_id': scan_result_id,
                'report_url': report_url,
                'file_name': file_name
            }

            response = supabase.table('reports').insert(report_data).execute()
            
            if response.data:
                return {'success': True, 'message': 'Report saved successfully', 'data': response.data[0]}
            return {'success': False, 'error': 'Failed to save report', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_report(report_id: str) -> Dict[str, Any]:
        """Get report details"""
        try:
            response = supabase.table('reports').select('*').eq('id', report_id).execute()
            
            if response.data:
                return {'success': True, 'data': response.data[0]}
            return {'success': False, 'error': 'Report not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_scan_reports(scan_result_id: str) -> Dict[str, Any]:
        """Get all reports for a scan"""
        try:
            response = supabase.table('reports').select('*').eq('scan_result_id', scan_result_id).execute()
            
            return {'success': True, 'data': response.data}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def increment_download_count(report_id: str) -> Dict[str, Any]:
        """Increment report download counter"""
        try:
            # Get current count
            response = supabase.table('reports').select('downloaded_count').eq('id', report_id).execute()
            
            if response.data:
                current_count = response.data[0]['downloaded_count'] or 0
                new_count = current_count + 1
                
                update_response = supabase.table('reports').update(
                    {'downloaded_count': new_count}
                ).eq('id', report_id).execute()
                
                return {'success': True, 'data': update_response.data[0]}
            
            return {'success': False, 'error': 'Report not found', 'data': None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}


# ═════════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═════════════════════════════════════════════════════════════════════════════════

class AuditService:
    """Handle audit logging for compliance"""

    @staticmethod
    def log_action(user_id: str, action: str, table_name: str, 
                  record_id: str, old_data: Dict = None, new_data: Dict = None) -> Dict[str, Any]:
        """Log user actions for audit trail"""
        try:
            log_data = {
                'user_id': user_id,
                'action': action,
                'table_name': table_name,
                'record_id': record_id,
                'old_data': json.dumps(old_data) if old_data else None,
                'new_data': json.dumps(new_data) if new_data else None
            }

            response = supabase.table('audit_logs').insert(log_data).execute()
            return {'success': True, 'data': response.data[0] if response.data else None}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}

    @staticmethod
    def get_audit_logs(user_id: str = None, limit: int = 100) -> Dict[str, Any]:
        """Retrieve audit logs"""
        try:
            if user_id:
                response = supabase.table('audit_logs').select('*').eq(
                    'user_id', user_id
                ).order('timestamp', desc=True).limit(limit).execute()
            else:
                response = supabase.table('audit_logs').select('*').order(
                    'timestamp', desc=True
                ).limit(limit).execute()
            
            return {'success': True, 'data': response.data}

        except Exception as e:
            return {'success': False, 'error': str(e), 'data': None}


# ═══════════════════════════════════════════════════════════════════════════════════
