// Utility function to show error messages
function showAuthError(message) {
    const errDiv = document.getElementById('authError');
    const errMsg = document.getElementById('authErrorMsg');
    if (errDiv && errMsg) {
        errMsg.textContent = message;
        errDiv.classList.remove('d-none');
    }
}

// Global Auth State Observer
auth.onAuthStateChanged(user => {
    const isAuthPage = window.location.pathname.includes('/login') || window.location.pathname.includes('/register') || window.location.pathname === '/';
    const isDummyAuth = localStorage.getItem('dummyAuth') === 'true';
    
    if (user || isDummyAuth) {
        // User is signed in. Redirect away from auth pages to dashboard
        if (isAuthPage) {
            window.location.href = '/dashboard';
        }
    } else {
        // No user is signed in. Redirect away from dashboard to login
        if (window.location.pathname.includes('/dashboard')) {
            window.location.href = '/login';
        }
    }
});

// Registration Logic
const registerForm = document.getElementById('registerForm');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById('registerBtn');
        const spinner = document.getElementById('registerSpinner');
        const text = document.getElementById('registerBtnText');
        
        const fullName = document.getElementById('fullName').value.trim();
        const specialization = document.getElementById('specialization').value.trim();
        const hospitalName = document.getElementById('hospitalName').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        // UI Loading
        btn.disabled = true;
        spinner.classList.remove('d-none');
        text.textContent = 'Creating Account...';
        document.getElementById('authError').classList.add('d-none');

        try {
            // 1. Create User in Firebase Auth
            const userCredential = await auth.createUserWithEmailAndPassword(email, password);
            const user = userCredential.user;

            // 2. Update Profile Display Name
            await user.updateProfile({ displayName: fullName });

            // 3. Save extra doctor info to Realtime Database
            await database.ref('doctors/' + user.uid).set({
                fullName: fullName,
                email: email,
                specialization: specialization,
                hospitalName: hospitalName,
                createdAt: firebase.database.ServerValue.TIMESTAMP
            });

            // Show Success
            document.getElementById('authSuccess').classList.remove('d-none');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);

        } catch (error) {
            console.error(error);
            showAuthError(error.message);
            btn.disabled = false;
            spinner.classList.add('d-none');
            text.textContent = 'Create Account';
        }
    });
}

// Login Logic
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById('loginBtn');
        const spinner = document.getElementById('loginSpinner');
        const text = document.getElementById('loginBtnText');
        
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        // ─── DUMMY LOGIN BYPASS ──────────────────────────────────────────────
        if (email === "admin@test.com" && password === "admin123") {
            localStorage.setItem('dummyAuth', 'true');
            window.location.href = '/dashboard';
            return;
        }
        // ────────────────────────────────────────────────────────────────────

        // UI Loading
        btn.disabled = true;
        spinner.classList.remove('d-none');
        text.textContent = 'Authenticating...';
        document.getElementById('authError').classList.add('d-none');

        try {
            await auth.signInWithEmailAndPassword(email, password);
            // Observer will automatically redirect to /dashboard
        } catch (error) {
            console.error(error);
            showAuthError(error.message);
            btn.disabled = false;
            spinner.classList.add('d-none');
            text.textContent = 'Sign In Securely';
        }
    });
}

// Logout Utility
function logoutDoctor() {
    localStorage.removeItem('dummyAuth');
    auth.signOut().then(() => {
        window.location.href = '/login';
    }).catch((error) => {
        console.error('Logout error', error);
        window.location.href = '/login';
    });
}
