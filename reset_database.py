# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE RESET & INITIALIZATION SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
from supabase import create_client

# Configuration
SUPABASE_URL = "https://tmfvtzwklomwdnhygpxx.supabase.co"
SUPABASE_KEY = "sb_publishable_yB9iPWcmKXFJoAgeqjUr7A_78Ysnj4H"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def reset_database():
    """Reset all tables to fresh state"""
    print("[*] Starting database reset...")
    
    try:
        # Delete all audit logs first (no foreign keys to it)
        print("[*] Clearing audit logs...")
        try:
            supabase.table('audit_logs').delete().gt('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
        
        # Delete all reports
        print("[*] Clearing reports...")
        try:
            supabase.table('reports').delete().gt('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
        
        # Delete all scan results
        print("[*] Clearing scan results...")
        try:
            supabase.table('scan_results').delete().gt('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
        
        # Delete all patients
        print("[*] Clearing patients...")
        try:
            supabase.table('patients').delete().gt('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
        
        # Delete all users
        print("[*] Clearing users...")
        try:
            supabase.table('users').delete().gt('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
        
        print("[+] ✅ All tables cleared successfully!")
        return True
        
    except Exception as e:
        print(f"[-] ❌ Error clearing tables: {e}")
        return False


def initialize_demo_accounts():
    """Create demo accounts for testing"""
    print("\n[*] Creating demo accounts...")
    
    from db_service import UserService, PatientService
    
    try:
        # Demo Doctor
        doctor_result = UserService.register_user(
            email="dr.demo@hospital.com",
            password="Demo123456",
            full_name="Dr. Demo",
            role="doctor",
            specialization="Neurology",
            license_number="LIC123456",
            hospital_name="Demo Hospital",
            phone="+1-555-0123"
        )
        
        if doctor_result['success']:
            print(f"[+] Doctor registered: {doctor_result['data']['email']}")
        else:
            print(f"[-] Doctor registration failed: {doctor_result['error']}")
        
        # Demo Patient
        patient_result = UserService.register_user(
            email="patient.demo@email.com",
            password="Demo123456",
            full_name="Demo Patient",
            role="patient",
            phone="+1-555-9876"
        )
        
        if patient_result['success']:
            user_id = patient_result['user_id']
            print(f"[+] Patient registered: {patient_result['data']['email']}")
            
            # Create patient profile
            patient_profile = PatientService.create_patient(
                user_id=user_id,
                age=35,
                gender="Female",
                medical_history="Hypertension",
                allergies="Penicillin"
            )
            
            if patient_profile['success']:
                print(f"[+] Patient profile created")
            else:
                print(f"[-] Patient profile creation failed: {patient_profile['error']}")
        else:
            print(f"[-] Patient registration failed: {patient_result['error']}")
        
        print("\n[+] ✅ Demo accounts created successfully!")
        print("\n📋 Demo Credentials:")
        print("=" * 50)
        print("🩺 Doctor Account:")
        print("   Email: dr.demo@hospital.com")
        print("   Password: Demo123456")
        print("\n👤 Patient Account:")
        print("   Email: patient.demo@email.com")
        print("   Password: Demo123456")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"[-] ❌ Error creating demo accounts: {e}")
        return False


def verify_database():
    """Verify database connectivity and show current data"""
    print("\n[*] Verifying database connectivity...")
    
    try:
        users = supabase.table('users').select('email, full_name, role').execute()
        print(f"[+] ✅ Database connected successfully")
        print(f"[+] Total users in database: {len(users.data)}")
        
        if users.data:
            print("\n📋 Existing Users:")
            for user in users.data:
                print(f"   - {user['full_name']} ({user['email']}) - {user['role']}")
        
        return True
        
    except Exception as e:
        print(f"[-] ❌ Database connection failed: {e}")
        return False


def main():
    """Main execution"""
    print("=" * 60)
    print("🧠 NeuroScan AI - Database Reset & Initialization")
    print("=" * 60)
    
    # Verify database
    if not verify_database():
        print("\n[-] Cannot connect to database. Check .env file and credentials.")
        return
    
    # Ask for confirmation
    print("\n⚠️  WARNING: This will DELETE ALL data from the database!")
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("[-] Reset cancelled.")
        return
    
    # Reset database
    if reset_database():
        # Initialize demo accounts
        initialize_demo_accounts()
        print("\n[+] ✅ Database reset and initialized successfully!")
        print("\n🚀 You can now use the demo accounts to test the application.")
    else:
        print("\n[-] ❌ Database reset failed.")


if __name__ == "__main__":
    main()
