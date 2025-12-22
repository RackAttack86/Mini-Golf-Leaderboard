// Form Validation JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Add Bootstrap validation classes to all forms
    const forms = document.querySelectorAll('form[method="POST"]');

    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Real-time validation for specific fields
    const nameInputs = document.querySelectorAll('input[name="name"]');
    nameInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value.trim().length < 1) {
                this.setCustomValidity('Name is required');
                this.classList.add('is-invalid');
            } else if (this.value.length > 100) {
                this.setCustomValidity('Name is too long (max 100 characters)');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    });

    // Score validation
    const scoreInputs = document.querySelectorAll('input[name="score[]"]');
    scoreInputs.forEach(input => {
        input.addEventListener('blur', function() {
            const score = parseInt(this.value);
            if (isNaN(score)) {
                this.setCustomValidity('Score must be a number');
                this.classList.add('is-invalid');
            } else if (score < -50) {
                this.setCustomValidity('Score unreasonably low (min -50)');
                this.classList.add('is-invalid');
            } else if (score > 500) {
                this.setCustomValidity('Score seems too high (max 500)');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    });

    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !this.value.includes('@')) {
                this.setCustomValidity('Please enter a valid email address');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                if (this.value) {
                    this.classList.add('is-valid');
                }
            }
        });
    });

    // Date validation
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('blur', function() {
            const selectedDate = new Date(this.value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            if (selectedDate > today) {
                this.setCustomValidity('Date cannot be in the future');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    });
});
