//  CONNECTIVITY CHECK 
function createConnectivityBanner() {
    const banner = document.createElement('div');
    banner.id = 'connectivity-banner';
    banner.style.cssText = `position:fixed;top:0;left:0;right:0;padding:.9rem;
        text-align:center;font-weight:600;z-index:10000;display:none;font-size:.875rem;`;
    document.body.insertBefore(banner, document.body.firstChild);
    return banner;
}
function updateConnectivityStatus(online) {
    const banner = document.getElementById('connectivity-banner') || createConnectivityBanner();
    if (!online) {
        banner.textContent = '⚠️ No Internet Connection – Please check your WiFi or mobile data';
        banner.style.cssText += 'background:#dc2626;color:#fff;display:block;';
    } else {
        banner.textContent = '✅ Back Online';
        banner.style.cssText += 'background:#16a34a;color:#fff;display:block;';
        setTimeout(() => { banner.style.display = 'none'; }, 3000);
    }
}
window.addEventListener('online',  () => updateConnectivityStatus(true));
window.addEventListener('offline', () => updateConnectivityStatus(false));
window.addEventListener('load',    () => { if (!navigator.onLine) updateConnectivityStatus(false); });

//  ELEMENTS 
const loginModal  = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
const bookingModal= document.getElementById('bookingModal');

//  OPEN / CLOSE MODALS 
function openModal(modal) {
    if (modal) modal.style.display = 'block';
}
function closeModal(modal) {
    if (modal) modal.style.display = 'none';
}

document.getElementById('loginBtn')    ?.addEventListener('click', e => { e.preventDefault(); openModal(loginModal); });
document.getElementById('getStartedBtn')?.addEventListener('click', () => openModal(loginModal));
document.getElementById('bookTicketsBtn')?.addEventListener('click', () => openModal(bookingModal));
document.getElementById('closeLogin')  ?.addEventListener('click', () => closeModal(loginModal));
document.getElementById('closeSignup') ?.addEventListener('click', () => closeModal(signupModal));
document.getElementById('closeBooking')?.addEventListener('click', () => closeModal(bookingModal));
document.getElementById('switchToSignup')?.addEventListener('click', e => { e.preventDefault(); closeModal(loginModal); openModal(signupModal); });
document.getElementById('switchToLogin') ?.addEventListener('click', e => { e.preventDefault(); closeModal(signupModal); openModal(loginModal); });

window.addEventListener('click', e => {
    if (e.target === loginModal)   closeModal(loginModal);
    if (e.target === signupModal)  closeModal(signupModal);
    if (e.target === bookingModal) closeModal(bookingModal);
});

//  HELPER: show inline alert inside a modal 
function showModalAlert(elId, msg) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 5000);
}

//  LOGIN FORM 
document.getElementById('loginForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    if (!navigator.onLine) {
        showModalAlert('loginAlert', '❌ No Internet Connection! Please connect and try again.');
        return;
    }
    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    if (!email || !password) { showModalAlert('loginAlert', '❌ Please fill in all fields.'); return; }
    const emailOk  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    if (!emailOk)  { showModalAlert('loginAlert', '❌ Please enter a valid email address.'); return; }

    const btn = this.querySelector('button[type="submit"]');
    const orig = btn.textContent;
    btn.textContent = 'Logging in…';
    btn.disabled = true;

    try {
        const res  = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.success) {
            closeModal(loginModal);
            this.reset();
            window.location.href = '/planner';          // ← redirect to planner
        } else {
            showModalAlert('loginAlert', '❌ ' + (data.message || 'Login failed.'));
            btn.textContent = orig;
            btn.disabled = false;
        }
    } catch (err) {
        showModalAlert('loginAlert', '❌ Connection error. Please try again.');
        btn.textContent = orig;
        btn.disabled = false;
    }
});

//  SIGNUP FORM 
document.getElementById('signupForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    if (!navigator.onLine) {
        showModalAlert('signupAlert', '❌ No Internet Connection! Please connect and try again.');
        return;
    }
    const name     = document.getElementById('signup-name').value.trim();
    const email    = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirm  = document.getElementById('confirm-password').value;
    const terms    = document.getElementById('terms')?.checked;

    if (name.length < 2) { showModalAlert('signupAlert', '❌ Please enter your full name (min 2 chars).'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { showModalAlert('signupAlert', '❌ Please enter a valid email.'); return; }
    if (password.length < 6) { showModalAlert('signupAlert', '❌ Password must be at least 6 characters.'); return; }
    if (password !== confirm) { showModalAlert('signupAlert', '❌ Passwords do not match!'); return; }
    if (!terms) { showModalAlert('signupAlert', '❌ Please accept the Terms & Conditions.'); return; }

    const btn = this.querySelector('button[type="submit"]');
    const orig = btn.textContent;
    btn.textContent = 'Creating Account…';
    btn.disabled = true;

    try {
        const res  = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (data.success) {
            closeModal(signupModal);
            this.reset();
            window.location.href = '/planner';          // ← redirect to planner
        } else {
            showModalAlert('signupAlert', '❌ ' + (data.message || 'Signup failed.'));
            btn.textContent = orig;
            btn.disabled = false;
        }
    } catch (err) {
        showModalAlert('signupAlert', '❌ Connection error. Please try again.');
        btn.textContent = orig;
        btn.disabled = false;
    }
});

//  PASSWORD STRENGTH 
document.getElementById('signup-password')?.addEventListener('input', function() {
    const help = document.getElementById('passwordHelp');
    if (!help) return;
    const len = this.value.length;
    if (len === 0) { help.textContent = 'Password must be at least 6 characters'; help.style.color = '#64748b'; }
    else if (len < 6) { help.textContent = 'Too short – need at least 6 characters'; help.style.color = '#dc2626'; }
    else if (len < 9) { help.textContent = '⚡ Weak – consider a longer password'; help.style.color = '#d97706'; }
    else { help.textContent = '✅ Strong password'; help.style.color = '#16a34a'; }
});

//  SMOOTH SCROLL 
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href.startsWith('#')) {
            e.preventDefault();
            document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
        }
    });
});