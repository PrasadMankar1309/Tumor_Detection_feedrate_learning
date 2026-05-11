/**
 * NeuroScan AI - Core Dashboard Application Logic
 */

// Global App State
const app = {
    currentDoctor: null,
    currentPatientData: null,
    currentResult: null,
    
    // UI Elements
    els: {
        wrapper: document.getElementById('appWrapper'),
        authOverlay: document.getElementById('authLoadingOverlay'),
        aiOverlay: document.getElementById('aiProcessingOverlay'),
        navBtns: document.querySelectorAll('.nav-view-btn'),
        views: document.querySelectorAll('.app-view'),
        mobileMenuBtn: document.getElementById('mobileMenuBtn'),
        sidebar: document.getElementById('sidebar'),
        themeToggleBtn: document.getElementById('themeToggleBtn'),
        themeIcon: document.getElementById('themeIcon')
    },

    init: function() {
        this.setupAuthObserver();
        this.setupNavigation();
        this.setupUploadForm();
        this.setupDragAndDrop();
        this.setupTheme();
    },

    // --- Authentication & Initialization ---
    setupAuthObserver: function() {
        const isDummyAuth = localStorage.getItem('dummyAuth') === 'true';
        
        // Handle Dummy Auth Immediately (Faster & Bypass Firebase initialization)
        if (isDummyAuth) {
            console.log("[Auth] Dummy Admin detected. Bypassing Firebase observer.");
            this.currentDoctor = {
                uid: 'dummy-admin-id',
                email: 'admin@test.com',
                displayName: 'Administrator'
            };
            setTimeout(() => {
                const drNameEl = document.getElementById('navDrName');
                const hospNameEl = document.getElementById('navHospitalName');
                if (drNameEl) drNameEl.textContent = 'Dr. Admin';
                if (hospNameEl) hospNameEl.textContent = 'Test Hospital';
                
                this.finishLoading();
                this.loadDashboardStats();
                this.loadHistory();
            }, 100);
            return;
        }

        // Standard Firebase Auth Observer
        auth.onAuthStateChanged(user => {
            if (user) {
                this.currentDoctor = user;
                database.ref('doctors/' + user.uid).once('value').then(snapshot => {
                    const profile = snapshot.val();
                    if (profile) {
                        const drNameEl = document.getElementById('navDrName');
                        const hospNameEl = document.getElementById('navHospitalName');
                        if (drNameEl) drNameEl.textContent = 'Dr. ' + profile.fullName.split(' ')[0];
                        if (hospNameEl) hospNameEl.textContent = profile.hospitalName;
                    }
                    this.finishLoading();
                    this.loadDashboardStats();
                    this.loadHistory();
                }).catch(err => {
                    console.error("Profile load error", err);
                    this.finishLoading(); // Load anyway
                });
            } else {
                window.location.href = '/login';
            }
        });
    },

    finishLoading: function() {
        this.els.authOverlay.classList.remove('active');
        this.els.wrapper.classList.remove('d-none');
        // Trigger initial view animation
        const activeView = document.querySelector('.app-view:not(.d-none)');
        if(activeView) activeView.style.animation = 'none';
        setTimeout(() => { if(activeView) activeView.style.animation = ''; }, 10);
    },

    // --- Single Page App Navigation ---
    setupNavigation: function() {
        this.els.navBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = btn.getAttribute('data-target');
                this.switchView(targetId);
                
                // Close mobile sidebar if open
                if (window.innerWidth < 768) {
                    this.els.sidebar.classList.remove('show');
                }
            });
        });

        if (this.els.mobileMenuBtn) {
            this.els.mobileMenuBtn.addEventListener('click', () => {
                this.els.sidebar.classList.toggle('show');
            });
        }
    },

    switchView: function(targetId) {
        // Update Nav Menu UI
        this.els.navBtns.forEach(b => b.classList.remove('active'));
        const activeBtn = document.querySelector(`.nav-view-btn[data-target="${targetId}"]`);
        if(activeBtn) activeBtn.classList.add('active');

        // Update Topbar Title
        const titles = {
            'view-dashboard': 'Dashboard Overview',
            'view-upload': 'Upload MRI Scan',
            'view-result': 'Analysis Result',
            'view-history': 'Patient Records',
            'view-analytics': 'System Analytics'
        };
        document.getElementById('topbarTitle').textContent = titles[targetId] || 'Dashboard';

        // Toggle Views
        this.els.views.forEach(view => {
            if (view.id === targetId) {
                view.classList.remove('d-none');
            } else {
                view.classList.add('d-none');
            }
        });

        // Trigger specific view logic
        if (targetId === 'view-dashboard') this.loadDashboardStats();
        if (targetId === 'view-history') this.loadHistory();
        if (targetId === 'view-analytics') this.renderAnalytics();
    },

    // --- Upload & Drag/Drop Logic ---
    setupDragAndDrop: function() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('mriFileInput');
        const previewContainer = document.getElementById('imagePreviewContainer');
        const previewImg = document.getElementById('mriPreviewImg');
        const analyzeBtn = document.getElementById('analyzeBtn');

        if (!dropZone) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-active'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-active'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            handleFiles(files);
        });

        fileInput.addEventListener('change', function() { handleFiles(this.files); });

        function handleFiles(files) {
            if (files.length > 0) {
                const file = files[0];
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewImg.src = e.target.result;
                        dropZone.classList.add('d-none');
                        previewContainer.classList.remove('d-none');
                        analyzeBtn.disabled = false;
                        
                        // Store file for form submission
                        app.currentMriFile = file;
                    };
                    reader.readAsDataURL(file);
                } else {
                    alert('Please upload a valid image file (JPG, PNG).');
                }
            }
        }
    },

    clearUpload: function() {
        document.getElementById('mriFileInput').value = '';
        app.currentMriFile = null;
        document.getElementById('dropZone').classList.remove('d-none');
        document.getElementById('imagePreviewContainer').classList.add('d-none');
        document.getElementById('mriPreviewImg').src = '';
        document.getElementById('analyzeBtn').disabled = true;
    },

    // --- AI Prediction & Firebase Storage ---
    setupUploadForm: function() {
        const form = document.getElementById('uploadMriForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!this.currentMriFile) {
                alert('Please upload an MRI image first.');
                return;
            }

            // Gather Patient Data
            this.currentPatientData = {
                name: document.getElementById('upPatientName').value.trim(),
                age: document.getElementById('upPatientAge').value,
                gender: document.getElementById('upPatientGender').value,
                timestamp: Date.now() // local fallback
            };

            // Show Analysis Loading Screen & Disable Button
            const submitBtn = document.getElementById('analyzeBtn');
            submitBtn.disabled = true;
            this.showAiLoading(true);

            try {
                // 1. Send to Flask Backend API for Prediction
                const formData = new FormData();
                formData.append('file', this.currentMriFile);

                const response = await fetch('/api/predict', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (result.error) throw new Error(result.error);

                this.currentResult = result;

                // Local fallback URLs
                let originalUrl = URL.createObjectURL(this.currentMriFile);
                let heatmapUrl = result.heatmap_b64 || originalUrl;

                // 2 & 3 & 4. Firebase Operations (Best Effort, with 10 sec timeout to prevent hanging)
                const firebaseOp = async () => {
                    const storageRef = storage.ref();
                    const mriRef = storageRef.child(`mri_scans/${this.currentDoctor.uid}/${Date.now()}_original_${this.currentMriFile.name}`);
                    await mriRef.put(this.currentMriFile);
                    let finalOrig = await mriRef.getDownloadURL();

                    let finalHeat = null;
                    if (result.heatmap_b64) {
                        const heatmapBlob = await (await fetch(result.heatmap_b64)).blob();
                        const hmRef = storageRef.child(`heatmaps/${this.currentDoctor.uid}/${Date.now()}_heatmap.jpg`);
                        await hmRef.put(heatmapBlob);
                        finalHeat = await hmRef.getDownloadURL();
                    }

                    const recordRef = database.ref(`patients/${this.currentDoctor.uid}`).push();
                    const recordData = {
                        patient_name: this.currentPatientData.name,
                        age: this.currentPatientData.age,
                        gender: this.currentPatientData.gender,
                        prediction: result.prediction,
                        confidence: result.confidence,
                        all_probs: result.all_probs,
                        original_url: finalOrig,
                        heatmap_url: finalHeat,
                        timestamp: firebase.database.ServerValue.TIMESTAMP
                    };
                    await recordRef.set(recordData);
                    return { origUrl: finalOrig, heatUrl: finalHeat, reqId: recordRef.key };
                };

                // Run Firebase logic with a timeout so UI doesn't hang if user hasn't set up Firebase Storage
                try {
                    const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Firebase Timeout')), 10000));
                    const fbResult = await Promise.race([firebaseOp(), timeoutPromise]);
                    originalUrl = fbResult.origUrl;
                    heatmapUrl = fbResult.heatUrl;
                    this.currentPatientData.recordId = fbResult.reqId;
                } catch (fbError) {
                    console.warn("Firebase syncing failed (or skipped). Using local URLs.", fbError);
                }

                // Append URLs for PDF Generation
                this.currentResult.original_url = originalUrl;
                this.currentResult.heatmap_url = heatmapUrl;

                // 5. Update UI and switch to Result View
                this.populateResultView(result, originalUrl, heatmapUrl);
                this.showAiLoading(false);
                this.clearUpload();
                submitBtn.disabled = false;
                this.switchView('view-result');

            } catch (error) {
                console.error(error);
                alert('Analysis Error: ' + error.message);
                this.showAiLoading(false);
                submitBtn.disabled = false;
            }
        });
    },

    showAiLoading: function(show) {
        if (show) {
            this.els.aiOverlay.classList.remove('d-none');
            // Animate progress bar spoofing
            let width = 10;
            const bar = document.getElementById('aiProgressBar');
            app.progressInterval = setInterval(() => {
                if (width >= 90) clearInterval(app.progressInterval);
                else { width += 5; bar.style.width = width + '%'; }
            }, 500);
        } else {
            clearInterval(app.progressInterval);
            this.els.aiOverlay.classList.add('d-none');
            document.getElementById('aiProgressBar').style.width = '10%';
        }
    },

    populateResultView: function(result, origUrl, heatUrl) {
        document.getElementById('resPatientName').textContent = this.currentPatientData.name;
        
        // Images
        document.getElementById('resOriginalImg').src = result.heatmap_b64; // Using overlay for the result view, or switch between them
        // Actually, let's keep it simple: Show overlay in original, heatmap separate.
        // But since API gives b64 overlay:
        document.getElementById('resOriginalImg').src = origUrl;
        document.getElementById('resHeatmapImg').src = heatUrl || origUrl; // fallback

        // AI Info
        const info = result.info;
        document.getElementById('resIcon').innerHTML = info.icon;
        document.getElementById('resTumorName').textContent = info.full_name;
        document.getElementById('resTumorName').style.color = info.color;
        document.getElementById('resConfidence').textContent = `${result.confidence}%`;
        
        // Risk Alert Box Styling
        const alertBox = document.getElementById('resAlertBox');
        alertBox.className = 'glass-panel focus-panel p-4 mb-4'; // reset
        if (result.prediction === 'notumor') {
            alertBox.classList.add('border-success');
        } else if (result.confidence >= 90) {
            alertBox.classList.add('border-danger');
        } else {
            alertBox.classList.add('border-warning');
        }

        // Clinical Info
        document.getElementById('resDesc').textContent = info.description;
        document.getElementById('resSymptoms').textContent = info.symptoms;
        document.getElementById('resTreatments').textContent = info.treatments;
        document.getElementById('resMedicines').textContent = info.medicines;
        document.getElementById('resPrevention').textContent = info.prevention;
    },

    generateAndDownloadReport: async function() {
        if (!this.currentResult || !this.currentPatientData) return;
        
        // Let's ask Flask to generate the PDF
        const btn = event.currentTarget;
        const oldHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Generating...';
        btn.disabled = true;

        try {
            const payload = {
                patient_name: this.currentPatientData.name,
                age: this.currentPatientData.age,
                gender: this.currentPatientData.gender,
                doctor_name: document.getElementById('navDrName').textContent,
                hospital_name: document.getElementById('navHospitalName').textContent,
                scan_date: new Date().toLocaleDateString(),
                prediction: this.currentResult.prediction,
                confidence: this.currentResult.confidence
            };

            const response = await fetch('/api/report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `NeuroScan_Report_${this.currentPatientData.name.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Report generating error:', error);
            alert('Failed to generate report.');
        } finally {
            btn.innerHTML = oldHtml;
            btn.disabled = false;
        }
    },

    // --- Firebase RTDB Readers ---
    loadHistory: function() {
        if (!this.currentDoctor) return;
        
        const tbody = document.getElementById('historyTbody');
        const recentTbody = document.getElementById('recentScansTbody');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><div class="spinner-border text-accent"></div></td></tr>';
        
        database.ref('patients/' + this.currentDoctor.uid).orderByChild('timestamp').once('value').then(snapshot => {
            app.cachedPatientsData = [];
            snapshot.forEach(child => {
                app.cachedPatientsData.push({ id: child.key, ...child.val() });
            });
            // Reverse to get newest first
            app.cachedPatientsData.reverse();
            app.renderHistoryTable(app.cachedPatientsData);
            app.renderRecentScans(app.cachedPatientsData.slice(0, 5));
        }).catch(err => {
            console.error("Error loading history:", err);
            if (this.currentDoctor.uid === 'dummy-admin-id') {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary-color py-4">Dummy records loaded. Search and review past MRI scan analyses.</td></tr>';
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-4">Failed to load data. Please check your internet connection.</td></tr>';
            }
        });
    },

    renderHistoryTable: function(data) {
        const tbody = document.getElementById('historyTbody');
        tbody.innerHTML = '';
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary-color py-4">No scan records found. Upload your first MRI.</td></tr>';
            return;
        }

        data.forEach(item => {
            const dateStr = new Date(item.timestamp).toLocaleDateString();
            
            let badgeClass = 'bg-secondary';
            let formattedPred = item.prediction;
            if (item.prediction === 'notumor') { badgeClass = 'bg-success'; formattedPred = 'No Tumor'; }
            else if (item.prediction === 'glioma') { badgeClass = 'bg-danger'; formattedPred = 'Glioma'; }
            else if (item.prediction === 'meningioma') { badgeClass = 'bg-purple'; formattedPred = 'Meningioma'; }
            else if (item.prediction === 'pituitary') { badgeClass = 'bg-warning text-dark'; formattedPred = 'Pituitary'; }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="align-middle">${dateStr}</td>
                <td class="align-middle">
                    <div class="fw-bold">${item.patient_name}</div>
                    <div class="small text-secondary-color">${item.age} yrs, ${item.gender}</div>
                </td>
                <td class="align-middle">
                    <img src="${item.original_url}" width="40" height="40" class="rounded shadow-sm cursor-pointer" onclick="window.open('${item.heatmap_url || item.original_url}', '_blank')">
                </td>
                <td class="align-middle"><span class="badge ${badgeClass} shadow-sm px-2 py-1">${formattedPred}</span></td>
                <td class="align-middle fw-bold">${item.confidence}%</td>
                <td class="align-middle">
                    <button class="btn btn-sm btn-light hvr-grow text-danger me-1" onclick="app.deleteRecord('${item.id}')" title="Delete"><i class="fas fa-trash"></i></button>
                    <!-- Re-view capability could be added here -->
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    renderRecentScans: function(data) {
        const tbody = document.getElementById('recentScansTbody');
        tbody.innerHTML = '';
        
        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary-color py-4">No recent scans.</td></tr>';
            return;
        }

        data.forEach(item => {
            const dateStr = new Date(item.timestamp).toLocaleDateString();
            let badgeClass = item.prediction === 'notumor' ? 'bg-success' : 'bg-danger';
            let formattedPred = item.prediction === 'notumor' ? 'No Tumor' : item.prediction.charAt(0).toUpperCase() + item.prediction.slice(1);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="align-middle fw-bold">${item.patient_name}</td>
                <td class="align-middle small text-secondary-color">${dateStr}</td>
                <td class="align-middle"><span class="badge ${badgeClass}">${formattedPred}</span></td>
                <td class="align-middle">${item.confidence}%</td>
                <td class="align-middle">
                    <button class="btn btn-sm btn-outline-accent" onclick="app.switchView('view-history')">Details</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },

    deleteRecord: async function(recordId) {
        if (!confirm('Are you sure you want to delete this patient record?')) return;
        try {
            await database.ref(`patients/${this.currentDoctor.uid}/${recordId}`).remove();
            this.loadHistory(); // Reload
        } catch(e) {
            console.error(e);
            alert('Failed to delete record.');
        }
    },

    loadDashboardStats: function() {
        if (!this.currentDoctor) return;
        
        database.ref('patients/' + this.currentDoctor.uid).once('value').then(snapshot => {
            let total = 0, glioma = 0, pituitary = 0, meningioma = 0, notumor = 0;
            app.cachedPatientsData = [];

            if (snapshot.exists()) {
                snapshot.forEach(child => {
                    total++;
                    const pred = child.val().prediction;
                    if (pred === 'glioma') glioma++;
                    else if (pred === 'pituitary') pituitary++;
                    else if (pred === 'meningioma') meningioma++;
                    else if (pred === 'notumor') notumor++;
                    
                    app.cachedPatientsData.push({ id: child.key, ...child.val() });
                });
            } else if (this.currentDoctor.uid === 'dummy-admin-id') {
                // Mock stats for dummy user if DB is empty
                total = 12; glioma = 3; pituitary = 2; meningioma = 4; notumor = 3;
            }

            // Animate counters
            app.animateCounter('statTotalScans', total);
            app.animateCounter('statGlioma', glioma);
            app.animateCounter('statPituitary', pituitary);
            app.animateCounter('statMeningioma', meningioma);

            app.stats = { total, glioma, pituitary, meningioma, notumor };
        }).catch(err => {
            console.error("Dashboard stats error", err);
            // Fallback to dummy stats if it's the dummy user
            if (this.currentDoctor.uid === 'dummy-admin-id') {
                const total = 12, glioma = 3, pituitary = 2, meningioma = 4, notumor = 3;
                app.animateCounter('statTotalScans', total);
                app.animateCounter('statGlioma', glioma);
                app.animateCounter('statPituitary', pituitary);
                app.animateCounter('statMeningioma', meningioma);
                app.stats = { total, glioma, pituitary, meningioma, notumor };
            }
        });
    },

    animateCounter: function(elementId, target) {
        const el = document.getElementById(elementId);
        if(!el) return;
        let p = 0;
        const speed = 20; // ms
        const step = Math.max(1, Math.ceil(target / 20));
        
        const timer = setInterval(() => {
            p += step;
            if (p >= target) {
                clearInterval(timer);
                el.textContent = target;
            } else {
                el.textContent = p;
            }
        }, speed);
    },

    // --- Analytics / Chart.js ---
    renderAnalytics: function() {
        if (!this.stats) {
            // Need data first
            this.loadDashboardStats();
            setTimeout(() => this.renderAnalytics(), 500);
            return;
        }

        const data = [this.stats.glioma, this.stats.meningioma, this.stats.pituitary, this.stats.notumor];
        const labels = ['Glioma', 'Meningioma', 'Pituitary', 'No Tumor'];
        const colorsArr = ['#ef4444', '#a855f7', '#f59e0b', '#22c55e'];

        Chart.defaults.color = document.documentElement.getAttribute('data-theme') === 'dark' ? '#94a3b8' : '#64748b';
        Chart.defaults.font.family = "'Inter', sans-serif";

        // 1. Donut Chart
        if (app.chart1) app.chart1.destroy();
        const ctx1 = document.getElementById('chartTumorDist').getContext('2d');
        app.chart1 = new Chart(ctx1, {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colorsArr, borderWidth: 0 }] },
            options: { cutout: '75%', responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
        });

        // 2. Bar Chart
        if (app.chart2) app.chart2.destroy();
        const ctx2 = document.getElementById('chartBarCases').getContext('2d');
        app.chart2 = new Chart(ctx2, {
            type: 'bar',
            data: { labels, datasets: [{ label: 'Cases', data, backgroundColor: colorsArr, borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } }, x: { grid: { display: false } } } }
        });

        // 3. Line Chart (Mock Scans over time based on actual data if possible)
        // For simplicity, grouping by month/day is complex without specific Date sets, we just mock trend or use last N days
        if (app.chart3) app.chart3.destroy();
        const ctx3 = document.getElementById('chartScansTime').getContext('2d');
        
        // Very basic aggregation by day (last 7 days)
        const last7Days = Array(7).fill(0);
        const dateLabels = Array(7).fill('');
        const now = new Date();
        now.setHours(0,0,0,0);
        
        for (let i=6; i>=0; i--) {
            let d = new Date(now);
            d.setDate(d.getDate() - i);
            dateLabels[6-i] = d.toLocaleDateString(undefined, {weekday: 'short'});
        }

        if (app.cachedPatientsData) {
            app.cachedPatientsData.forEach(item => {
                const itemDate = new Date(item.timestamp);
                itemDate.setHours(0,0,0,0);
                const diffTime = Math.abs(now - itemDate);
                const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                if (diffDays >= 0 && diffDays < 7) {
                    last7Days[6 - diffDays]++;
                }
            });
        }

        app.chart3 = new Chart(ctx3, {
            type: 'line',
            data: {
                labels: dateLabels,
                datasets: [{
                    label: 'Scans',
                    data: last7Days,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#6366f1'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(148, 163, 184, 0.1)' } }, x: { grid: { display: false } } } }
        });
    },

    // --- Theme Toggling ---
    setupTheme: function() {
        const savedTheme = localStorage.getItem('neuroTheme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);

        this.els.themeToggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const target = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', target);
            localStorage.setItem('neuroTheme', target);
            this.updateThemeIcon(target);
            
            // Re-render charts for new theme colors
            if (this.els.views[this.els.views.length - 1].classList.contains('d-none') === false && app.chart1) {
                this.renderAnalytics();
            }
        });
    },

    updateThemeIcon: function(theme) {
        if (theme === 'dark') {
            this.els.themeIcon.className = 'fas fa-sun'; // Show sun button indicating light is an option
        } else {
            this.els.themeIcon.className = 'fas fa-moon'; // Show moon
        }
    }
};

// Initialize App Setup
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
