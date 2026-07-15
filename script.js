//  modal elements
const loginModal = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
const bookingModal = document.getElementById('bookingModal');
const loginBtn = document.getElementById('loginBtn');
const getStartedBtn = document.getElementById('getStartedBtn');
const bookTicketsBtn = document.getElementById('bookTicketsBtn');
const closeLogin = document.getElementById('closeLogin');
const closeSignup = document.getElementById('closeSignup');
const closeBooking = document.getElementById('closeBooking');
const loginForm = document.getElementById('loginForm');
const signupForm = document.getElementById('signupForm');
const switchToSignup = document.getElementById('switchToSignup');
const switchToLogin = document.getElementById('switchToLogin');

// Open login modal when clicking "Login" button in nav
loginBtn.onclick = function(e) {
    e.preventDefault();
    loginModal.style.display = 'block';
    signupModal.style.display = 'none';
    bookingModal.style.display = 'none';
}

// Open login modal when clicking "Get Started" button
getStartedBtn.onclick = function() {
    loginModal.style.display = 'block';
    signupModal.style.display = 'none';
    bookingModal.style.display = 'none';
}

// Open booking modal when clicking "Book Tickets" button
bookTicketsBtn.onclick = function() {
    bookingModal.style.display = 'block';
    loginModal.style.display = 'none';
    signupModal.style.display = 'none';
}

// Close login modal when clicking X
closeLogin.onclick = function() {
    loginModal.style.display = 'none';
}

// Close signup modal when clicking X
closeSignup.onclick = function() {
    signupModal.style.display = 'none';
}

// Close booking modal when clicking X
closeBooking.onclick = function() {
    bookingModal.style.display = 'none';
}

// Switch from login to signup
switchToSignup.onclick = function(e) {
    e.preventDefault();
    loginModal.style.display = 'none';
    signupModal.style.display = 'block';
}

// Switch from signup to login
switchToLogin.onclick = function(e) {
    e.preventDefault();
    signupModal.style.display = 'none';
    loginModal.style.display = 'block';
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    if (event.target == loginModal) {
        loginModal.style.display = 'none';
    }
    if (event.target == signupModal) {
        signupModal.style.display = 'none';
    }
    if (event.target == bookingModal) {
        bookingModal.style.display = 'none';
    }
}

// Handle login form submission
loginForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    // Basic validation
    if (!email || !password) {
        alert('Please fill in all fields');
        return;
    }
    
    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('Please enter a valid email address');
        return;
    }
    
    // For now, just show success message
    console.log('Login attempt:', { email, password });
    alert('✅ Login Successful!\n\nEmail: ' + email + '\n\n');
    
    // Close modal
    loginModal.style.display = 'none';
    
    // Clear form
    loginForm.reset();
});

// Handle signup form submission
signupForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const termsAccepted = document.getElementById('terms').checked;
    
    //Check full name
    if (name.length < 2) {
        alert('❌ Please enter your full name (at least 2 characters)');
        return;
    }
    
    //Check email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('❌ Please enter a valid email address');
        return;
    }
    
    //Check password length
    if (password.length < 6) {
        alert('❌ Password must be at least 6 characters long');
        return;
    }
    
    //Check if passwords match
    if (password !== confirmPassword) {
        alert('❌ Passwords do not match! Please try again.');
        return;
    }
    
    // All validations passed!
    console.log('Signup Data:', { name, email, password });
    
    // Success message
    alert(`✅ Account Created Successfully!\n\nWelcome, ${name}!\nEmail: ${email}\n\n(Connect to Flask backend to save this data)`);
    
    // Clear form and close modal
    signupForm.reset();
    signupModal.style.display = 'none';
});

// Password strength indicator
const passwordInput = document.getElementById('signup-password');
const passwordHelp = document.getElementById('passwordHelp');

if (passwordInput && passwordHelp) {
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        
        if (password.length === 0) {
            passwordHelp.textContent = 'Password must be at least 6 characters';
            passwordHelp.style.color = '#666';
        } else if (password.length < 6) {
            passwordHelp.textContent = 'Too short (at least 6 characters needed)';
            passwordHelp.style.color = '#e74c3c';
        } else if (password.length < 8) {
            passwordHelp.textContent = 'Weak password (consider adding more characters)';
            passwordHelp.style.color = '#f39c12';
        } else {
            passwordHelp.textContent = 'Strong password ✓';
            passwordHelp.style.color = '#27ae60';
        }
    });
}

// Smooth scrolling for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href.startsWith('#')) {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        }
    });
});
