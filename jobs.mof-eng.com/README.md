# Job Application Form Project

This project is a web-based job application form where applicants can submit their details for job positions. The project includes a form for applicants to fill out, server-side PHP scripts to handle form submissions, and integration with Google reCAPTCHA for spam prevention.

## Features

- User-friendly job application form with fields for personal information, contact details, and resume upload.
- CSRF token validation to prevent Cross-Site Request Forgery attacks.
- Google reCAPTCHA integration to verify that the form submission is not from a bot.
- Server-side validation of form input to ensure data integrity.
- Database storage of job application details for future reference.
- Email notification to the admin with applicant details and resume attachment upon successful submission.

## Technologies Used

- **HTML/CSS:** Frontend development for creating the user interface and styling.
- **Bootstrap:** Used for responsive design and styling of the form and thank you page.
- **JavaScript/jQuery:** Client-side scripting for form validation and AJAX submission.
- **PHP:** Server-side scripting language for form handling, data validation, and database interaction.
- **MySQL:** Database management system used to store job application data.
- **Google reCAPTCHA:** Integration for spam prevention and bot detection.
- **PHPMailer:** Library used for sending email notifications from the server.
- **Composer:** Dependency manager for PHP used to install PHPMailer library.
- **XAMPP/WAMP/MAMP:** Local server environment for testing and development.

## Setup Instructions

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/wonderakwei/Job-Application-System-with-PHP-and-MySQL.git
    ```

2. Install Composer dependencies:

    ```bash
     composer require phpmailer/phpmailer
    ```

3. Create the database and table in your MySQL via phpMyAdmin.

4. Configure the database connection in `process_form.php` file with your database credentials.

5. Obtain and replace the Google reCAPTCHA site key and secret key in the job application form (`index.php`) and PHP script (`process_form.php`).

6. Configure SMTP details in `process_form.php` for sending email notifications.

7. Start your local server environment (XAMPP, WAMP, MAMP, etc.).

8. Access the application in your web browser:

    ```url
    http://localhost/job-application-form/index.php
    ```

## Usage

1. Fill out the job application form with your details.
2. Complete the Google reCAPTCHA verification.
3. Click the "Apply Now" button to submit the form.
4. Upon successful submission, you will be redirected to the thank you page.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---
