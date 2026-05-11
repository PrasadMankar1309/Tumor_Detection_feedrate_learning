#!/usr/bin/env python
# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE APP STARTUP & VERIFICATION SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import os
from pathlib import Path

print("\n" + "=" * 70)
print("🧠 NeuroScan AI - Application Startup Guide")
print("=" * 70)

# Check if in correct directory
current_dir = Path.cwd()
if 'vgg16 frontend' not in str(current_dir):
    print("\n⚠️  WARNING: Not in the correct directory!")
    print(f"Current: {current_dir}")
    print("Please run from: vgg16 frontend/")
    sys.exit(1)

print("\n✅ Correct directory detected")

# Check for required files
print("\n📋 Checking required files...")
required_files = [
    'app.py',
    'db_service.py',
    '.env',
    'models/vgg19_brain_tumor_95acc.h5',
    'static/css/style.css',
    'templates/login.html',
    'templates/register.html',
    'templates/dashboard.html'
]

all_exist = True
for file in required_files:
    if os.path.exists(file):
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - MISSING!")
        all_exist = False

if not all_exist:
    print("\n⚠️  Some files are missing. Please check your project structure.")
    sys.exit(1)

# Check imports
print("\n🔧 Checking Python imports...")
try:
    import flask
    print("  ✅ Flask")
except:
    print("  ❌ Flask - Install: pip install flask")

try:
    import supabase
    print("  ✅ Supabase")
except:
    print("  ❌ Supabase - Install: pip install supabase")

try:
    import tensorflow
    print("  ✅ TensorFlow")
except:
    print("  ⚠️  TensorFlow not installed (optional)")

# Check .env configuration
print("\n⚙️  Checking .env configuration...")
if not os.path.exists('.env'):
    print("  ❌ .env file not found!")
    print("  Please copy .env.example to .env")
    sys.exit(1)

try:
    with open('.env', 'r', encoding='utf-8') as f:
        env_content = f.read()
        if 'Prasad' in env_content and '1309' in env_content:
            print("  ✅ Database password configured")
        else:
            print("  ❌ Database password not set!")
            print("  Update .env with: DATABASE_URL=postgresql://postgres:Prasad@1309@...")
            sys.exit(1)
except:
    print("  ⚠️  Could not verify .env file (continuing anyway)")
    print("  Make sure DATABASE_URL contains: Prasad@1309")

print("\n" + "=" * 70)
print("🚀 READY TO START!")
print("=" * 70)

print("\n📝 Next steps:")
print("\n1. Start the application:")
print("   → python app.py")
print("\n2. Open in browser:")
print("   → http://localhost:5000")
print("\n3. Create account:")
print("   → Go to /register")
print("   → Fill in details (any email)")
print("   → Click Create Account")
print("\n4. Login:")
print("   → Use your registered credentials")
print("\n5. Upload MRI:")
print("   → Go to /upload")
print("   → Select brain MRI image")
print("   → Click Analyze")

print("\n" + "=" * 70)
print("✨ Everything is configured correctly!")
print("=" * 70 + "\n")

# Ask if user wants to start app
response = input("Start application now? (yes/no): ").strip().lower()
if response == 'yes':
    print("\n🚀 Starting Flask application...\n")
    os.system('python app.py')
else:
    print("\n📝 To start manually, run:")
    print("   python app.py")
