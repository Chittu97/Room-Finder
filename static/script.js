document.addEventListener("DOMContentLoaded", function () {
    let currentForm = 0; // Index of the current form
    const forms = document.querySelectorAll('.form-box form > div');
    const nextButton = document.querySelector('.btn-next'); // Single next button
    const prevButton = document.querySelector('.btn-prev'); // Single back button
    const submitButton = document.querySelector('.btn-submit'); // Submit button
    const steps = document.querySelectorAll('.progress ul.progress-steps li');

    // Function to handle the display of the current form and steps
    function updateFormDisplay() {
        // Hide all forms
        forms.forEach((form, index) => {
            form.classList.toggle('active', index === currentForm);
        });

        // Update step indicator
        steps.forEach((step, index) => {
            const stepNumber = step.querySelector('span');
            if (index < currentForm) {
                step.classList.add('completed');
                step.classList.remove('active');
                stepNumber.style.backgroundColor = "orange";
            } else if (index === currentForm) {
                step.classList.add('active');
                step.classList.remove('completed');
                stepNumber.style.backgroundColor = "green";
            } else {
                step.classList.remove('active', 'completed');
                stepNumber.style.backgroundColor = "var(--lighter-color)";
            }
        });

        // Manage button visibility and state
        prevButton.disabled = currentForm === 0; // Disable Back button on the first form
        nextButton.style.display = currentForm === forms.length - 1 ? 'none' : 'inline-block'; // Hide Next on last form
        submitButton.style.display = currentForm === forms.length - 1 ? 'inline-block' : 'none'; // Show Submit on last form
    }

    // Event listener for Next button
    nextButton.addEventListener('click', function () {
        if (currentForm < forms.length - 1) {
            currentForm++;
            updateFormDisplay();
        }
    });

    // Event listener for Back button
    prevButton.addEventListener('click', function () {
        if (currentForm > 0) {
            currentForm--;
            updateFormDisplay();
        }
    });

    // Initialize form display
    updateFormDisplay();
});
