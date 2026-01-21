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

// ===== Shared Template Functions =====

/**
 * Setup auto-submit for form inputs
 * @param {string} formId - The form element ID
 * @param {string} selectorType - CSS selector for inputs (default: 'input[type="checkbox"]')
 */
function setupAutoSubmitForm(formId, selectorType = 'input[type="checkbox"]') {
    const form = document.getElementById(formId);
    if (!form) return;

    const inputs = form.querySelectorAll(selectorType);
    inputs.forEach(input => {
        input.addEventListener('change', function() {
            form.submit();
        });
    });
}

/**
 * Update course preview handling both HTTP URLs and uploaded files
 * @param {string} imageUrl - The image URL or filename
 * @param {string} previewElementId - ID of the preview image element
 */
function updateCoursePreview(imageUrl, previewElementId) {
    const preview = document.getElementById(previewElementId);
    if (!preview) return;

    if (imageUrl) {
        if (imageUrl.startsWith('http')) {
            preview.src = imageUrl;
        } else {
            // Construct path to uploads/courses/
            preview.src = `/static/uploads/courses/${imageUrl}`;
        }
        preview.style.display = 'block';
    } else {
        preview.style.display = 'none';
    }
}

/**
 * Create a Chart.js score chart with standard configuration
 * @param {HTMLCanvasElement} ctx - Canvas context
 * @param {Object} data - Chart data object
 * @param {Object} options - Additional chart options (merged with defaults)
 * @returns {Chart} Chart instance
 */
function createScoreChart(ctx, data, options = {}) {
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
            y: {
                reverse: true,
                beginAtZero: false,
                title: {
                    display: true,
                    text: 'Score (lower is better)'
                }
            }
        },
        plugins: {
            legend: {
                display: data.datasets && data.datasets.length > 1
            }
        }
    };

    // Deep merge options
    const mergedOptions = Object.assign({}, defaultOptions, options);

    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: mergedOptions
    });
}

/**
 * Setup table filtering with visible count
 * @param {string} inputId - Search input element ID
 * @param {string} tableId - Table element ID
 * @param {Object} options - Configuration options
 */
function setupTableFilter(inputId, tableId, options = {}) {
    const searchInput = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!searchInput || !table) return;

    const countElementId = options.countElementId || null;
    const countElement = countElementId ? document.getElementById(countElementId) : null;

    searchInput.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        let visibleCount = 0;

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(filter)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        if (countElement) {
            countElement.textContent = `Showing ${visibleCount} of ${rows.length}`;
        }
    });
}

/**
 * Calculate total score from hole inputs
 * @param {NodeList|Array} holeInputs - Input elements or array of values
 * @returns {number} Total score
 */
function calculateTotalScore(holeInputs) {
    let total = 0;
    holeInputs.forEach(input => {
        const value = typeof input === 'object' ? parseInt(input.value) : parseInt(input);
        if (!isNaN(value)) {
            total += value;
        }
    });
    return total;
}

/**
 * Set form loading state (enhanced version)
 * @param {string} formId - Form element ID
 * @param {string} loadingText - Text to display while loading
 * @param {boolean} isLoading - Whether to show or hide loading state
 */
function setFormLoading(formId, loadingText, isLoading = true) {
    const form = document.getElementById(formId);
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) return;

    if (isLoading) {
        submitButton.disabled = true;
        submitButton.dataset.originalText = submitButton.innerHTML;
        submitButton.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
    } else {
        submitButton.disabled = false;
        submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
    }
}

/**
 * Initialize collapsible sections with state persistence
 * @param {string} storageKey - LocalStorage key prefix for state persistence
 */
function initCollapsibleSections(storageKey = 'collapsible') {
    const collapsibles = document.querySelectorAll('[data-collapsible-section]');

    collapsibles.forEach(element => {
        const sectionId = element.getAttribute('data-collapsible-section');
        const savedState = localStorage.getItem(`${storageKey}_${sectionId}`);
        const collapseElement = document.getElementById(sectionId);

        if (!collapseElement) return;

        // Apply saved state (collapsed = 'false')
        if (savedState === 'false') {
            collapseElement.classList.remove('show');
            element.setAttribute('aria-expanded', 'false');
        }

        // Save state on toggle using Bootstrap events
        collapseElement.addEventListener('shown.bs.collapse', function() {
            localStorage.setItem(`${storageKey}_${sectionId}`, 'true');
            element.setAttribute('aria-expanded', 'true');
        });

        collapseElement.addEventListener('hidden.bs.collapse', function() {
            localStorage.setItem(`${storageKey}_${sectionId}`, 'false');
            element.setAttribute('aria-expanded', 'false');
        });
    });
}
