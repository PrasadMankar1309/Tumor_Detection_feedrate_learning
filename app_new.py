import os
import io
import json
import base64
import numpy as np
import uuid
from datetime import datetime
from PIL import Image
import scipy.ndimage as ndimage
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_session import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER
from werkzeug.security import generate_password_hash, check_password_hash

# ─── Import Database Service ───────────────────────────────────────────────────
from db_service import UserService, PatientService, ScanService, ReportService, AuditService

# ─── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'brain-tumor-detection-secret-key-2024'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folders for temporary processing before uploading to Supabase
TEMP_FOLDER = os.path.join(BASE_DIR, 'static', 'temp_process')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
UPLOADS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
HEATMAPS_FOLDER = os.path.join(BASE_DIR, 'static', 'heatmaps')

for d in [TEMP_FOLDER, REPORTS_FOLDER, UPLOADS_FOLDER, HEATMAPS_FOLDER]:
    os.makedirs(d, exist_ok=True)

# ─── Load Model ────────────────────────────────────────────────────────────────
print("[*] Loading VGG19 Brain Tumor Model...")
model_path = os.path.join(BASE_DIR, 'models', 'vgg19_brain_tumor_95acc.h5')
model = load_model(model_path)
print("[+] Model loaded successfully.")

CLASS_NAMES = ['pituitary', 'glioma', 'notumor', 'meningioma']

TUMOR_INFO = {
    'pituitary': {
        'icon': '🧬',
        'full_name': 'Pituitary Tumor',
        'description': 'A pituitary tumor grows in the pituitary gland at the base of the brain. Most are benign (non-cancerous), known as pituitary adenomas.',
        'symptoms': 'Headaches, vision loss, unexplained fatigue, and hormonal imbalances.',
        'treatments': 'Transsphenoidal surgery, radiation therapy, and hormone replacement.',
        'medicines': 'Cabergoline, Bromocriptine (for prolactinomas).',
        'prevention': 'No known prevention. Regular vision/hormone checks recommended for at-risk individuals.',
        'color': '#f59e0b'
    },
    'glioma': {
        'icon': '⚠️',
        'full_name': 'Glioma Tumor',
        'description': 'Glioma is a type of tumor that occurs in the brain and spinal cord. It begins in the glial cells that surround and support neurons.',
        'symptoms': 'Severe headaches, nausea, speech difficulties, seizures, and cognitive decline.',
        'treatments': 'Surgical resection, targeted radiation, and chemotherapy.',
        'medicines': 'Temozolomide, Bevacizumab, Corticosteroids (for swelling).',
        'prevention': 'Avoid high-dose radiation exposure. Genetic counseling if family history exists.',
        'color': '#ef4444'
    },
    'notumor': {
        'icon': '✅',
        'full_name': 'No Tumor Detected',
        'description': 'The MRI scan analysis shows no detectable brain tumor patterns. The brain structure appears within normal parameters.',
        'symptoms': 'N/A',
        'treatments': 'N/A',
        'medicines': 'N/A',
        'prevention': 'Maintain a healthy lifestyle, manage blood pressure, and report persistent neuro-symptoms.',
        'color': '#22c55e'
    },
    'meningioma': {
        'icon': '🔍',
        'full_name': 'Meningioma Tumor',
        'description': 'Meningioma arises from the meninges — the membranes that surround the brain and spinal cord. Most are slow-growing and benign.',
        'symptoms': 'Changes in vision, hearing loss, morning headaches, seizure, memory loss.',
        'treatments': 'Active surveillance (watchful waiting), craniotomy, radiosurgery.',
        'medicines': 'Anti-seizure drugs (Levetiracetam), Corticosteroids (Dexamethasone).',
        'prevention': 'Minimize unnecessary head radiation. Maintain healthy BMI.',
        'color': '#8b5cf6'
    }
}

# ─── Helper: Check if user is logged in ────────────────────────────────────────
def login_required(f):
    """Decorator to require login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized. Please login first.'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ─── Grad-CAM Functions ────────────────────────────────────────────────────────
def generate_gradcam(img_array, model, last_conv_layer_name=None):
    try:
        if last_conv_layer_name is None:
            for layer in reversed(model.layers):
                if isinstance(layer, tf.keras.layers.Conv2D):
                    last_conv_layer_name = layer.name
                    break

        grad_model = tf.keras.models.Model(
            inputs=model.inputs,
            outputs=[model.get_layer(last_conv_layer_name).output, model.output]
        )

        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            
            if isinstance(predictions, list):
                predictions = predictions[0]
            if isinstance(conv_outputs, list):
                conv_outputs = conv_outputs[0]
                
            pred_index = tf.argmax(predictions[0])
            class_channel = predictions[:, pred_index]

        grads = tape.gradient(class_channel, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
        return heatmap.numpy()
    except Exception as e:
        print(f"Grad-CAM error: {e}")
        return None

def apply_heatmap_overlay(original_path, heatmap):
    try:
        orig = Image.open(original_path).convert('RGB').resize((224, 224))
        orig_arr = np.array(orig, dtype=np.float32)

        heatmap_resized = ndimage.zoom(heatmap, (224 / heatmap.shape[0], 224 / heatmap.shape[1]))
        heatmap_resized = np.clip(heatmap_resized, 0, 1)

        r = np.clip(heatmap_resized * 2 - 0.5, 0, 1) * 255
        g = np.clip(1 - np.abs(heatmap_resized * 2 - 1), 0, 1) * 255
        b = np.clip(0.5 - heatmap_resized, 0, 1) * 255 * 2
        heatmap_rgb = np.stack([r, g, b], axis=-1)

        overlay = orig_arr * 0.5 + heatmap_rgb * 0.5
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)
        
        overlay_img = Image.fromarray(overlay)
        buffered = io.BytesIO()
        overlay_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Heatmap overlay error: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@app.route('/history')
@login_required
def history():
    return render_template('history.html')

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/result')
@login_required
def result():
    return render_template('result.html')

# ═════════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION API ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Register a new user (Doctor or Patient)"""
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        role = data.get('role')  # 'doctor' or 'patient'
        
        if not all([email, password, full_name, role]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Additional fields for doctors
        specialization = data.get('specialization') if role == 'doctor' else None
        license_number = data.get('license_number') if role == 'doctor' else None
        hospital_name = data.get('hospital_name') if role == 'doctor' else None
        phone = data.get('phone')
        
        # Register user
        user_result = UserService.register_user(
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            specialization=specialization,
            license_number=license_number,
            hospital_name=hospital_name,
            phone=phone
        )
        
        if not user_result['success']:
            return jsonify({'error': user_result['error']}), 400
        
        user_id = user_result['user_id']
        
        # If patient, create patient record
        if role == 'patient':
            age = data.get('age')
            gender = data.get('gender')
            
            PatientService.create_patient(
                user_id=user_id,
                age=age,
                gender=gender,
                medical_history=data.get('medical_history'),
                allergies=data.get('allergies')
            )
        
        # Log action
        AuditService.log_action(user_id, 'USER_REGISTRATION', 'users', user_id, new_data={'email': email, 'role': role})
        
        return jsonify({
            'success': True,
            'message': f'{role.capitalize()} registered successfully',
            'user_id': user_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Authenticate user
        login_result = UserService.login_user(email, password)
        
        if not login_result['success']:
            return jsonify({'error': login_result['error']}), 401
        
        user = login_result['data']
        
        # Store in session
        session['user_id'] = user['user_id']
        session['email'] = user['email']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        session['hospital_name'] = user['hospital_name']
        
        # Log action
        AuditService.log_action(user['user_id'], 'LOGIN', 'users', user['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout user"""
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            AuditService.log_action(user_id, 'LOGOUT', 'users', user_id)
        
        session.clear()
        return jsonify({'success': True, 'message': 'Logout successful'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/user', methods=['GET'])
@login_required
def api_get_user():
    """Get current logged-in user info"""
    try:
        user_id = session.get('user_id')
        user_result = UserService.get_user_by_id(user_id)
        
        if user_result['success']:
            return jsonify({'success': True, 'user': user_result['data']}), 200
        return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════════
# SCAN PREDICTION API ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    """Predict tumor from uploaded MRI image"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        user_id = session.get('user_id')
        user_result = UserService.get_user_by_id(user_id)
        
        if not user_result['success']:
            return jsonify({'error': 'User not found'}), 404

        user = user_result['data']
        
        # Save temporary file
        ext = file.filename.rsplit('.', 1)[-1].lower()
        temp_id = uuid.uuid4().hex[:8]
        filepath = os.path.join(TEMP_FOLDER, f"{temp_id}.{ext}")
        file.save(filepath)

        # Predict
        img = keras_image.load_img(filepath, target_size=(224, 224))
        img_array = keras_image.img_to_array(img)
        img_batch = np.expand_dims(img_array, axis=0) / 255.0

        preds = model.predict(img_batch)
        pred_idx = int(np.argmax(preds[0]))
        prediction_class = CLASS_NAMES[pred_idx]
        confidence = round(float(np.max(preds[0])) * 100, 2)
        all_probs = {CLASS_NAMES[i]: round(float(preds[0][i]) * 100, 2) for i in range(len(CLASS_NAMES))}

        # Generate Grad-CAM Heatmap
        heatmap = generate_gradcam(img_batch, model)
        heatmap_b64 = None
        if heatmap is not None:
            heatmap_b64 = apply_heatmap_overlay(filepath, heatmap)

        # Clean up temp file
        if os.path.exists(filepath):
            os.remove(filepath)

        # Log prediction
        AuditService.log_action(user_id, 'SCAN_PREDICTION', 'scan_results', None, new_data={
            'prediction': prediction_class,
            'confidence': confidence
        })

        return jsonify({
            'success': True,
            'prediction': prediction_class,
            'confidence': confidence,
            'all_probs': all_probs,
            'heatmap_b64': heatmap_b64,
            'info': TUMOR_INFO.get(prediction_class, TUMOR_INFO['notumor'])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scan/save', methods=['POST'])
@login_required
def api_save_scan():
    """Save scan result to database"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # Get doctor's patient if they have one
        patient_result = PatientService.get_patient_by_user_id(user_id)
        
        if not patient_result['success']:
            return jsonify({'error': 'Patient record not found. Please complete your profile.'}), 404
        
        patient_id = patient_result['data']['id']
        
        # Save scan result
        scan_result = ScanService.create_scan_result(
            patient_id=patient_id,
            doctor_id=user_id,
            prediction=data.get('prediction'),
            confidence=data.get('confidence'),
            mri_image_url=data.get('mri_image_url'),
            heatmap_image_url=data.get('heatmap_image_url'),
            all_probabilities=data.get('all_probs'),
            notes=data.get('notes')
        )
        
        if not scan_result['success']:
            return jsonify({'error': scan_result['error']}), 500
        
        scan_id = scan_result['scan_id']
        
        # Log action
        AuditService.log_action(user_id, 'SCAN_SAVED', 'scan_results', scan_id, new_data={
            'prediction': data.get('prediction'),
            'confidence': data.get('confidence')
        })

        return jsonify({
            'success': True,
            'message': 'Scan saved successfully',
            'scan_id': scan_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scan/<scan_id>', methods=['GET'])
@login_required
def api_get_scan(scan_id):
    """Get scan result details"""
    try:
        scan_result = ScanService.get_scan_result(scan_id)
        
        if not scan_result['success']:
            return jsonify({'error': 'Scan not found'}), 404
        
        return jsonify({'success': True, 'data': scan_result['data']}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patient/<patient_id>/scans', methods=['GET'])
@login_required
def api_get_patient_scans(patient_id):
    """Get all scans for a patient"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        scans_result = ScanService.get_patient_scans(patient_id, limit=limit, offset=offset)
        
        if not scans_result['success']:
            return jsonify({'error': scans_result['error']}), 500
        
        return jsonify({
            'success': True,
            'data': scans_result['data'],
            'count': scans_result['count']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════════
# REPORT API ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/api/report', methods=['POST'])
@login_required
def api_report():
    """Generate and save PDF report"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        doc_id = str(uuid.uuid4())[:8]
        report_path = os.path.join(REPORTS_FOLDER, f'NeuroScan_Report_{doc_id}.pdf')

        doc = SimpleDocTemplate(report_path, pagesize=A4, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=4, alignment=TA_CENTER)
        sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=2, alignment=TA_CENTER)
        
        story.append(Paragraph("NeuroScan AI - Brain Tumor Detection", title_style))
        story.append(Paragraph("Confidential Medical Report", sub_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", sub_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6366f1'), spaceAfter=12))

        # Patient Info
        info_data = [
            ['Patient Name', data.get('patient_name', 'Unknown'), 'Age', str(data.get('age', 'N/A'))],
            ['Gender', data.get('gender', 'N/A'), 'Scan Date', data.get('scan_date', 'N/A')],
            ['Doctor', data.get('doctor_name', 'Unknown'), 'Hospital', data.get('hospital_name', 'Unknown')],
        ]
        t = Table(info_data, colWidths=[1.4*inch, 2.2*inch, 1.4*inch, 2.2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 16))

        # Prediction
        pred = data.get('prediction', 'notumor')
        conf = data.get('confidence', 0)
        info = TUMOR_INFO.get(pred, TUMOR_INFO['notumor'])
        p_style = ParagraphStyle('Pred', parent=styles['Normal'], fontSize=16, textColor=colors.HexColor(info['color']), fontName='Helvetica-Bold', spaceAfter=6, alignment=TA_CENTER)
        story.append(Paragraph(f"AI Prediction: {info['full_name']} ({conf}%)", p_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=12))

        story.append(Paragraph("Clinical Information", styles['Heading3']))
        story.append(Paragraph(f"<b>Description:</b> {info['description']}", styles['Normal']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Symptoms:</b> {info['symptoms']}", styles['Normal']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Treatment Options:</b> {info['treatments']}", styles['Normal']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Recommended Medicines:</b> {info['medicines']}", styles['Normal']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Prevention:</b> {info['prevention']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("Disclaimer: This AI prediction is for reference only and should not replace professional medical diagnosis.", styles['Normal']))
        
        doc.build(story)
        
        # Save report to database
        report_result = ReportService.create_report(
            scan_result_id=data.get('scan_id'),
            report_url=report_path,
            file_name=f"Report_{data.get('patient_name', 'Patient')}.pdf"
        )
        
        # Log action
        AuditService.log_action(user_id, 'REPORT_GENERATED', 'reports', report_result['data']['id'] if report_result['success'] else None)

        return send_file(report_path, as_attachment=True, download_name=f"Report_{data.get('patient_name', 'Patient')}.pdf")

    except Exception as e:
        print(f"Report generation error: {e}")
        return jsonify({'error': str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════════
# ANALYTICS API ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/api/analytics/statistics', methods=['GET'])
@login_required
def api_get_statistics():
    """Get scan statistics for logged-in doctor"""
    try:
        user_id = session.get('user_id')
        
        stats_result = ScanService.get_scan_statistics(user_id)
        
        if not stats_result['success']:
            return jsonify({'error': stats_result['error']}), 500
        
        return jsonify({'success': True, 'data': stats_result['data']}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/doctor-stats', methods=['GET'])
@login_required
def api_doctor_stats():
    """Get doctor's patients and statistics"""
    try:
        user_id = session.get('user_id')
        
        patients_result = PatientService.get_all_patients_for_doctor(user_id)
        stats_result = ScanService.get_scan_statistics(user_id)
        
        return jsonify({
            'success': True,
            'patients': patients_result['data'] if patients_result['success'] else [],
            'statistics': stats_result['data'] if stats_result['success'] else {}
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
