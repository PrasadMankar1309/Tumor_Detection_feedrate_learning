import os
import io
import json
import base64
import sqlite3
import numpy as np
import uuid
from datetime import datetime
from PIL import Image
import scipy.ndimage as ndimage
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER

# ─── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'neuroscan-secret-key-2024'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMP_FOLDER = os.path.join(BASE_DIR, 'static', 'temp_process')
REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
UPLOADS_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
HEATMAPS_FOLDER = os.path.join(BASE_DIR, 'static', 'heatmaps')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'vgg19_brain_tumor_95acc.h5')
DB_PATH = os.path.join(BASE_DIR, 'neuroscan.db')

for d in [TEMP_FOLDER, REPORTS_FOLDER, UPLOADS_FOLDER, HEATMAPS_FOLDER]:
    os.makedirs(d, exist_ok=True)

# ─── Database Setup ────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        patient_age INTEGER,
        prediction TEXT NOT NULL,
        confidence REAL NOT NULL,
        all_probs TEXT,
        filename TEXT,
        heatmap_file TEXT,
        scan_date TEXT DEFAULT (date('now'))
    )''')
    conn.commit()
    conn.close()

init_db()

# ─── Load Model ────────────────────────────────────────────────────────────────
print("[*] Loading VGG19 Brain Tumor Model...")
model = load_model(MODEL_PATH)
print("[+] Model loaded successfully.")

CLASS_NAMES = ['pituitary', 'glioma', 'notumor', 'meningioma']

TUMOR_INFO = {
    'pituitary': {
        'icon': '🧬', 'full_name': 'Pituitary Tumor', 'color': '#f59e0b',
        'risk': 'Moderate', 'recommendation': 'Consult an endocrinologist for hormonal evaluation and an MRI follow-up in 3 months.',
        'description': 'A pituitary tumor grows in the pituitary gland at the base of the brain. Most are benign (non-cancerous), known as pituitary adenomas.',
        'symptoms': 'Headaches, vision loss, unexplained fatigue, and hormonal imbalances.',
        'treatments': 'Transsphenoidal surgery, radiation therapy, and hormone replacement.',
        'medicines': 'Cabergoline, Bromocriptine (for prolactinomas).',
        'prevention': 'No known prevention. Regular vision/hormone checks recommended for at-risk individuals.',
    },
    'glioma': {
        'icon': '⚠️', 'full_name': 'Glioma Tumor', 'color': '#ef4444',
        'risk': 'High', 'recommendation': 'Immediate referral to a neuro-oncologist. Biopsy and advanced imaging recommended.',
        'description': 'Glioma is a type of tumor that occurs in the brain and spinal cord. It begins in the glial cells that surround and support neurons.',
        'symptoms': 'Severe headaches, nausea, speech difficulties, seizures, and cognitive decline.',
        'treatments': 'Surgical resection, targeted radiation, and chemotherapy.',
        'medicines': 'Temozolomide, Bevacizumab, Corticosteroids (for swelling).',
        'prevention': 'Avoid high-dose radiation exposure. Genetic counseling if family history exists.',
    },
    'notumor': {
        'icon': '✅', 'full_name': 'No Tumor Detected', 'color': '#22c55e',
        'risk': 'None', 'recommendation': 'No immediate action required. Continue routine health check-ups.',
        'description': 'The MRI scan analysis shows no detectable brain tumor patterns. The brain structure appears within normal parameters.',
        'symptoms': 'N/A', 'treatments': 'N/A', 'medicines': 'N/A',
        'prevention': 'Maintain a healthy lifestyle, manage blood pressure, and report persistent neuro-symptoms.',
    },
    'meningioma': {
        'icon': '🔍', 'full_name': 'Meningioma Tumor', 'color': '#8b5cf6',
        'risk': 'Moderate', 'recommendation': 'Follow-up MRI in 6 months. Surgical evaluation if symptomatic.',
        'description': 'Meningioma arises from the meninges — the membranes that surround the brain and spinal cord. Most are slow-growing and benign.',
        'symptoms': 'Changes in vision, hearing loss, morning headaches, seizure, memory loss.',
        'treatments': 'Active surveillance (watchful waiting), craniotomy, radiosurgery.',
        'medicines': 'Anti-seizure drugs (Levetiracetam), Corticosteroids (Dexamethasone).',
        'prevention': 'Minimize unnecessary head radiation. Maintain healthy BMI.',
    }
}

# ─── Auth Helper ───────────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

# ─── Grad-CAM ──────────────────────────────────────────────────────────────────
def generate_gradcam(img_array, mdl, last_conv_layer_name=None):
    try:
        if last_conv_layer_name is None:
            for layer in reversed(mdl.layers):
                if isinstance(layer, tf.keras.layers.Conv2D):
                    last_conv_layer_name = layer.name
                    break
        grad_model = tf.keras.models.Model(
            inputs=mdl.inputs,
            outputs=[mdl.get_layer(last_conv_layer_name).output, mdl.output]
        )
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array)
            if isinstance(predictions, list): predictions = predictions[0]
            if isinstance(conv_outputs, list): conv_outputs = conv_outputs[0]
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
        return Image.fromarray(overlay)
    except Exception as e:
        print(f"Heatmap overlay error: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET'])
def login_page():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_submit():
    email = request.form.get('email', '')
    password = request.form.get('password', '')
    if email == 'admin@test.com' and password == 'admin123':
        session['logged_in'] = True
        session['user_name'] = 'Dr. Admin'
        session['hospital'] = 'Test Hospital'
        return redirect(url_for('dashboard'))
    return render_template('login.html', error='Invalid email or password.')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    scans = conn.execute('SELECT * FROM scans ORDER BY id DESC LIMIT 5').fetchall()
    total = conn.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    glioma = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='glioma'").fetchone()[0]
    meningioma = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='meningioma'").fetchone()[0]
    pituitary = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='pituitary'").fetchone()[0]
    notumor = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='notumor'").fetchone()[0]
    conn.close()
    return render_template('dashboard.html', scans=scans, total=total,
                           glioma=glioma, meningioma=meningioma, pituitary=pituitary, notumor=notumor)

@app.route('/upload', methods=['GET'])
@login_required
def upload():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_submit():
    if 'file' not in request.files:
        return render_template('upload.html', error='No file uploaded.')
    file = request.files['file']
    if file.filename == '':
        return render_template('upload.html', error='No file selected.')
    patient_name = request.form.get('patient_name', 'Unknown')
    patient_age = request.form.get('patient_age', 0)

    try:
        # Save original
        ext = file.filename.rsplit('.', 1)[-1].lower()
        fname = f"{uuid.uuid4().hex[:10]}.{ext}"
        filepath = os.path.join(UPLOADS_FOLDER, fname)
        file.save(filepath)

        # Predict
        img = keras_image.load_img(filepath, target_size=(224, 224))
        img_array = keras_image.img_to_array(img)
        img_batch = np.expand_dims(img_array, axis=0) / 255.0
        preds = model.predict(img_batch)
        pred_idx = int(np.argmax(preds[0]))
        prediction = CLASS_NAMES[pred_idx]
        confidence = round(float(np.max(preds[0])) * 100, 2)
        all_probs = {CLASS_NAMES[i]: round(float(preds[0][i]) * 100, 2) for i in range(len(CLASS_NAMES))}

        # Grad-CAM
        heatmap = generate_gradcam(img_batch, model)
        heatmap_file = None
        if heatmap is not None:
            overlay_img = apply_heatmap_overlay(filepath, heatmap)
            if overlay_img:
                heatmap_file = f"hm_{fname}"
                overlay_img.save(os.path.join(HEATMAPS_FOLDER, heatmap_file), format="JPEG")

        # Save to DB
        conn = get_db()
        cur = conn.execute(
            'INSERT INTO scans (patient_name, patient_age, prediction, confidence, all_probs, filename, heatmap_file, scan_date) VALUES (?,?,?,?,?,?,?,?)',
            (patient_name, patient_age, prediction, confidence, json.dumps(all_probs), fname, heatmap_file, datetime.now().strftime('%Y-%m-%d'))
        )
        scan_id = cur.lastrowid
        conn.commit()
        conn.close()

        return redirect(url_for('result_page', scan_id=scan_id))
    except Exception as e:
        print(f"Upload error: {e}")
        return render_template('upload.html', error=f'Analysis failed: {str(e)}')

@app.route('/result/<int:scan_id>')
@login_required
def result_page(scan_id):
    conn = get_db()
    scan = conn.execute('SELECT * FROM scans WHERE id=?', (scan_id,)).fetchone()
    conn.close()
    if not scan:
        return redirect(url_for('history'))
    info = TUMOR_INFO.get(scan['prediction'], TUMOR_INFO['notumor'])
    all_probs = json.loads(scan['all_probs']) if scan['all_probs'] else {}
    conf = scan['confidence']
    if conf >= 90: risk_level, risk_color = 'High Confidence', '#22c55e'
    elif conf >= 70: risk_level, risk_color = 'Moderate Confidence', '#f59e0b'
    else: risk_level, risk_color = 'Low Confidence', '#ef4444'
    return render_template('result.html', scan=scan, info=info, all_probs=all_probs,
                           risk_level=risk_level, risk_color=risk_color)

@app.route('/history')
@login_required
def history():
    conn = get_db()
    scans = conn.execute('SELECT * FROM scans ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('history.html', scans=scans)

@app.route('/analytics')
@login_required
def analytics():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    glioma = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='glioma'").fetchone()[0]
    meningioma = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='meningioma'").fetchone()[0]
    pituitary = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='pituitary'").fetchone()[0]
    notumor = conn.execute("SELECT COUNT(*) FROM scans WHERE prediction='notumor'").fetchone()[0]
    dates_raw = conn.execute("SELECT scan_date FROM scans ORDER BY scan_date").fetchall()
    conn.close()
    dates = [r['scan_date'] for r in dates_raw if r['scan_date']]
    return render_template('analytics.html', total=total, glioma=glioma,
                           meningioma=meningioma, pituitary=pituitary, notumor=notumor, dates=json.dumps(dates))

@app.route('/delete/<int:scan_id>', methods=['POST'])
@login_required
def delete_scan(scan_id):
    conn = get_db()
    scan = conn.execute('SELECT * FROM scans WHERE id=?', (scan_id,)).fetchone()
    if scan:
        # Delete files
        for f in [scan['filename'], scan['heatmap_file']]:
            if f:
                for folder in [UPLOADS_FOLDER, HEATMAPS_FOLDER]:
                    p = os.path.join(folder, f)
                    if os.path.exists(p): os.remove(p)
        conn.execute('DELETE FROM scans WHERE id=?', (scan_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('history'))

@app.route('/report/<int:scan_id>')
@login_required
def download_report(scan_id):
    conn = get_db()
    scan = conn.execute('SELECT * FROM scans WHERE id=?', (scan_id,)).fetchone()
    conn.close()
    if not scan:
        return redirect(url_for('history'))

    info = TUMOR_INFO.get(scan['prediction'], TUMOR_INFO['notumor'])
    report_path = os.path.join(REPORTS_FOLDER, f'Report_{scan_id}.pdf')

    doc = SimpleDocTemplate(report_path, pagesize=A4, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=4, alignment=TA_CENTER)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=2, alignment=TA_CENTER)

    story.append(Paragraph("NeuroScan AI", title_style))
    story.append(Paragraph("Confidential Medical Report", sub_style))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6366f1'), spaceAfter=12))

    info_data = [
        ['Patient Name', scan['patient_name'], 'Age', str(scan['patient_age'] or 'N/A')],
        ['Scan Date', scan['scan_date'] or 'N/A', 'Doctor', session.get('user_name', 'Dr. Admin')],
        ['Hospital', session.get('hospital', 'Test Hospital'), 'Scan ID', f"#{scan['id']:04d}"],
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

    p_style = ParagraphStyle('Pred', parent=styles['Normal'], fontSize=16, textColor=colors.HexColor(info['color']), fontName='Helvetica-Bold', spaceAfter=6, alignment=TA_CENTER)
    story.append(Paragraph(f"AI Prediction: {info['full_name']} ({scan['confidence']}%)", p_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=12))

    story.append(Paragraph("Clinical Information", styles['Heading3']))
    for label, key in [("Description", "description"), ("Symptoms", "symptoms"), ("Treatment", "treatments"), ("Medicines", "medicines"), ("Prevention", "prevention")]:
        story.append(Paragraph(f"<b>{label}:</b> {info.get(key, 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Disclaimer: This AI prediction is for reference only and should not replace professional medical diagnosis.", styles['Normal']))

    doc.build(story)
    return send_file(report_path, as_attachment=True, download_name=f"NeuroScan_Report_{scan['patient_name']}.pdf")

# ─── JSON API for frontend predict (kept for compatibility) ────────────────────
@app.route('/api/predict', methods=['POST'])
def api_predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    try:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        temp_id = uuid.uuid4().hex[:8]
        filepath = os.path.join(TEMP_FOLDER, f"{temp_id}.{ext}")
        file.save(filepath)
        img = keras_image.load_img(filepath, target_size=(224, 224))
        img_array = keras_image.img_to_array(img)
        img_batch = np.expand_dims(img_array, axis=0) / 255.0
        preds = model.predict(img_batch)
        pred_idx = int(np.argmax(preds[0]))
        prediction_class = CLASS_NAMES[pred_idx]
        confidence = round(float(np.max(preds[0])) * 100, 2)
        all_probs = {CLASS_NAMES[i]: round(float(preds[0][i]) * 100, 2) for i in range(len(CLASS_NAMES))}
        heatmap = generate_gradcam(img_batch, model)
        heatmap_b64 = None
        if heatmap is not None:
            overlay_img = apply_heatmap_overlay(filepath, heatmap)
            if overlay_img:
                buffered = io.BytesIO()
                overlay_img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                heatmap_b64 = f"data:image/jpeg;base64,{img_str}"
        if os.path.exists(filepath): os.remove(filepath)
        return jsonify({
            'success': True, 'prediction': prediction_class, 'confidence': confidence,
            'all_probs': all_probs, 'heatmap_b64': heatmap_b64,
            'info': TUMOR_INFO.get(prediction_class, TUMOR_INFO['notumor'])
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
