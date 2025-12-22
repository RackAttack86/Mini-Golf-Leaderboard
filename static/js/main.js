// Mini Golf Leaderboard - Main JavaScript

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Confirm delete actions
    const deleteForms = document.querySelectorAll('form[action*="delete"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Table row click to navigate
    const tableRows = document.querySelectorAll('table tbody tr[data-href]');
    tableRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(e) {
            // Don't navigate if clicking a button or link
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A') {
                window.location = this.dataset.href;
            }
        });
    });
});

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

// Show loading state
function showLoading(button) {
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
}

// Format date to YYYY-MM-DD
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Local storage helper for form data persistence
function saveFormData(formId, data) {
    localStorage.setItem(`form_${formId}`, JSON.stringify(data));
}

function loadFormData(formId) {
    const data = localStorage.getItem(`form_${formId}`);
    return data ? JSON.parse(data) : null;
}

function clearFormData(formId) {
    localStorage.removeItem(`form_${formId}`);
}
