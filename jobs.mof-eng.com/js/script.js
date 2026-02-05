// Function to validate the job application form
function validateForm() {
    // Get form inputs
    var firstname = document.getElementById('firstname').value.trim();
    var lastname = document.getElementById('lastname').value.trim();
    var email = document.getElementById('email').value.trim();
    var phone = document.getElementById('phone').value.trim();
    var age = document.getElementById('age').value.trim();
    var startdate = document.getElementById('startdate').value.trim();
    var address = document.getElementById('address').value.trim();
    var message = document.getElementById('message').value.trim();
    var upload = document.getElementById('upload').value.trim();

    // Validate first name
    if (firstname === '') {
        alert('Please enter your first name.');
        return false;
    }

    // Validate last name
    if (lastname === '') {
        alert('Please enter your last name.');
        return false;
    }

    // Validate email
    if (email === '') {
        alert('Please enter your email.');
        return false;
    } else if (!isValidEmail(email)) {
        alert('Please enter a valid email address.');
        return false;
    }

    // Validate phone
    if (phone === '') {
        alert('Please enter your phone number.');
        return false;
    }

    // Validate age
    if (age === '') {
        alert('Please enter your age.');
        return false;
    }

    // Validate date of birth
    if (startdate === '') {
        alert('Please enter your date of birth.');
        return false;
    }

    // Validate address
    if (address === '') {
        alert('Please enter your address.');
        return false;
    }

    // Validate message
    if (message === '') {
        alert('Please enter your cover letter.');
        return false;
    }

    // Validate uploaded file
    if (upload === '') {
        alert('Please upload your resume.');
        return false;
    }

    // If all validations pass, return true
    return true;
}

// Function to validate email format
function isValidEmail(email) {
    // Regular expression to validate email format
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Function to validate file type
function validateFileType() {
    // Get the file input element
    var fileInput = document.getElementById('upload');
    // Get the selected file
    var file = fileInput.files[0];

    // Check if a file is selected
    if (!file) {
        alert('Please upload a file.');
        return false;
    }

    // Get the file extension
    var fileExtension = file.name.split('.').pop().toLowerCase();

    // Allowed file types
    var allowedExtensions = ['pdf', 'doc', 'docx'];

    // Check if the file type is allowed
    if (allowedExtensions.indexOf(fileExtension) === -1) {
        alert('Please upload a PDF, DOC, or DOCX file.');
        return false;
    }

    // If file type is allowed, return true
    return true;
}
