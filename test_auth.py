#!/usr/bin/env python
# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION TEST SCRIPT - Direct Testing Without Web Interface
# ═══════════════════════════════════════════════════════════════════════════════

from db_service import UserService, PatientService, supabase
import json

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def test_database_connection():
    """Test if database is connected"""
    print_header("1️⃣  DATABASE CONNECTION TEST")
    try:
        result = supabase.table('users').select('email').limit(1).execute()
        print_success("Database connected successfully!")
        return True
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False

def list_all_users():
    """List all existing users"""
    print_header("2️⃣  EXISTING USERS IN DATABASE")
    try:
        users = supabase.table('users').select('email, full_name, role, created_at').execute()
        
        if not users.data:
            print_info("No users found in database")
            return
        
        print(f"Total users: {len(users.data)}\n")
        for i, user in enumerate(users.data, 1):
            print(f"{i}. {user['full_name']} ({user['email']})")
            print(f"   Role: {user['role']}")
            print(f"   Created: {user['created_at']}\n")
    except Exception as e:
        print_error(f"Failed to fetch users: {e}")

def test_register_doctor(email, password, name):
    """Test doctor registration"""
    print_header(f"3️⃣  TESTING DOCTOR REGISTRATION")
    print_info(f"Email: {email}")
    print_info(f"Name: {name}")
    
    result = UserService.register_user(
        email=email,
        password=password,
        full_name=name,
        role="doctor",
        specialization="Neurology",
        license_number="LIC123456",
        hospital_name="Test Hospital",
        phone="+1-555-0100"
    )
    
    if result['success']:
        print_success(f"Doctor registration successful!")
        print_info(f"User ID: {result['user_id']}")
        return True
    else:
        print_error(f"Registration failed: {result['error']}")
        return False

def test_register_patient(email, password, name, age, gender):
    """Test patient registration"""
    print_header(f"4️⃣  TESTING PATIENT REGISTRATION")
    print_info(f"Email: {email}")
    print_info(f"Name: {name}")
    
    # Register patient
    result = UserService.register_user(
        email=email,
        password=password,
        full_name=name,
        role="patient",
        phone="+1-555-0200"
    )
    
    if result['success']:
        print_success(f"Patient registration successful!")
        user_id = result['user_id']
        print_info(f"User ID: {user_id}")
        
        # Create patient profile
        patient_result = PatientService.create_patient(
            user_id=user_id,
            age=age,
            gender=gender,
            medical_history="Test history",
            allergies="Test allergy"
        )
        
        if patient_result['success']:
            print_success(f"Patient profile created!")
            return True
        else:
            print_error(f"Patient profile creation failed: {patient_result['error']}")
            return False
    else:
        print_error(f"Registration failed: {result['error']}")
        return False

def test_login(email, password):
    """Test user login"""
    print_header(f"5️⃣  TESTING LOGIN")
    print_info(f"Email: {email}")
    
    result = UserService.login_user(email, password)
    
    if result['success']:
        print_success(f"Login successful!")
        user = result['data']
        print_info(f"Name: {user['full_name']}")
        print_info(f"Role: {user['role']}")
        print_info(f"Email: {user['email']}")
        return True
    else:
        print_error(f"Login failed: {result['error']}")
        return False

def test_get_user(user_id):
    """Test getting user by ID"""
    print_header(f"6️⃣  TESTING GET USER BY ID")
    print_info(f"User ID: {user_id}")
    
    result = UserService.get_user_by_id(user_id)
    
    if result['success']:
        print_success(f"User fetched successfully!")
        user = result['data']
        print_info(f"Name: {user['full_name']}")
        print_info(f"Email: {user['email']}")
        print_info(f"Role: {user['role']}")
        return True
    else:
        print_error(f"Failed to fetch user: {result['error']}")
        return False

def main():
    """Main test execution"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "🧠 NeuroScan AI - Authentication Test" + " " * 14 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Test 1: Database connection
    if not test_database_connection():
        print_error("Cannot continue without database connection")
        return
    
    # Test 2: List existing users
    list_all_users()
    
    # Test 3: Register new doctor
    doctor_email = "test.doctor@hospital.com"
    doctor_result = test_register_doctor(
        email=doctor_email,
        password="Doctor123456",
        name="Test Doctor"
    )
    
    # Test 4: Register new patient
    patient_email = "test.patient@email.com"
    patient_result = test_register_patient(
        email=patient_email,
        password="Patient123456",
        name="Test Patient",
        age=35,
        gender="Female"
    )
    
    # Test 5: Login tests
    if doctor_result:
        test_login(doctor_email, "Doctor123456")
    
    if patient_result:
        test_login(patient_email, "Patient123456")
    
    # Test 6: Get user details
    if doctor_result:
        users = supabase.table('users').select('id').eq('email', doctor_email).execute()
        if users.data:
            test_get_user(users.data[0]['id'])
    
    # Final summary
    print_header("✨ TEST SUMMARY")
    print_info("All authentication tests completed!")
    print_info("Check the results above to verify functionality")
    
    # Show what to do next
    print("\n" + "=" * 70)
    print("📋 NEXT STEPS:")
    print("=" * 70)
    print("1. If all tests passed (✅):")
    print("   → Run: python app.py")
    print("   → Visit: http://localhost:5000/login")
    print("   → Use test credentials from above")
    print("\n2. If tests failed (❌):")
    print("   → Check .env file (password should be: Prasad@1309)")
    print("   → Run: python reset_database.py")
    print("   → Try again\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
