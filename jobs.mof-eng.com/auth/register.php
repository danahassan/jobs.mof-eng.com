<?php
$page_title = "Create Account";
if (session_status() === PHP_SESSION_NONE) session_start();
require __DIR__ . '/../db.php';

$notification = $_SESSION['notification'] ?? null;
unset($_SESSION['notification']);
include __DIR__ . '/../includes/header.php';

$err = '';
$name_val = '';
$email_val = '';
$phone_val = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = trim($_POST['name']);
    $email = trim($_POST['email']);
    $phone = trim($_POST['phone']);
    $pass = $_POST['password'];
    $pass_confirm = $_POST['password_confirm'];

    $name_val = $name;
    $email_val = $email;
    $phone_val = $phone;

    if ($name === '' || $email === '' || $phone === '' || $pass === '' || $pass_confirm === '') {
        $err = "All fields are required.";
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $err = "Please enter a valid email address.";
    } elseif (!preg_match('/^[0-9+\-\s]{6,20}$/', $phone)) {
        $err = "Please enter a valid mobile number.";
    } elseif ($pass !== $pass_confirm) {
        $err = "Passwords do not match.";
    } elseif (!$err) {
        $q_check = $conn->prepare("SELECT id FROM users WHERE email=? LIMIT 1");
        $q_check->bind_param("s", $email);
        $q_check->execute();
        if ($q_check->get_result()->num_rows > 0) {
            $err = "An account with this email already exists.";
        }
    }

    if (!$err) {
        $hash = password_hash($pass, PASSWORD_BCRYPT);
        $role = 'user';
        $stmt = $conn->prepare("INSERT INTO users(name, email, phone, password_hash, role) VALUES(?,?,?,?,?)");
        $stmt->bind_param("sssss", $name, $email, $phone, $hash, $role);

        if ($stmt->execute()) {
            // --- 📧 SEND CONFIRMATION EMAIL START ---
            $to = $email;
            $subject = "Welcome to MANAGING OF FUTURE ENG. (MOF) COMPANY - Account Created Successfully";
            
// Professional HTML Email Template with Logos
            $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
            
            $message = "
            <html>
            <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                    
                    <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                        <img src='$logo_url' alt='MANAGING OF FUTURE ENG. (MOF) COMPANY Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                        <h2 style='color: #198754; margin: 0; font-size: 22px;'>Welcome to MANAGING OF FUTURE ENG. (MOF) COMPANY Careers</h2>
                    </div>

                    <p style='font-size: 16px;'>Dear <strong>$name</strong>,</p>
                    
                    <p>Thank you for registering an account with <strong>MANAGING OF FUTURE ENG. (MOF) COMPANY</strong>. We are pleased to have you join our talent community.</p>
                    
                    <p>Your account has been successfully created with the following credentials:</p>
                    
                    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;'>
                        <table style='width: 100%; border-collapse: collapse;'>
                            <tr>
                                <td style='padding: 5px 0; width: 100px; color: #666;'><strong>Email:</strong></td>
                                <td style='padding: 5px 0;'>$email</td>
                            </tr>
                            <tr>
                                <td style='padding: 5px 0; color: #666;'><strong>Phone:</strong></td>
                                <td style='padding: 5px 0;'>$phone</td>
                            </tr>
                        </table>
                    </div>

                    <p>You may now log in to your dashboard to complete your professional profile, upload your latest CV, and track the status of your job applications.</p>

                    <p style='margin-top: 30px; text-align: center;'>
                        <a href='https://jobs.mof-eng.com/auth/login.php' 
                           style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                           Access Your Dashboard
                        </a>
                    </p>

                    <div style='margin-top: 50px; padding-top: 25px; border-top: 1px solid #eee; display: flex; align-items: center;'>
                        <table style='width: 100%;'>
                            <tr>
                                <td style='vertical-align: top; width: 120px;'>
                                    <img src='$logo_url' alt='MANAGING OF FUTURE ENG. (MOF) COMPANY' style='width: 100px; height: auto; margin-top: 10px;'>
                                </td>
                                <td style='vertical-align: top; padding-left: 20px; border-left: 1px solid #ddd;'>
                                    <p style='margin: 0; font-weight: bold; color: #198754;'>Best regards,</p>
                                    <p style='margin: 5px 0;'><strong>HR Team</strong></p>
                                    
                                    <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                        <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG. (MOF) COMPANY</span><br>
                                        <strong>Tel:</strong> 07705330101<br>
                                        <strong>Address:</strong> House NO. A1-345, New Chwarchra, Near Sara petrol station,<br>
                                        Slemani (Sulaymaniyah), Iraq.<br>
                                        <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                        &copy; " . date('Y') . " MANAGING OF FUTURE ENG. (MOF) COMPANY. All rights reserved.<br>
                        This is an automated notification. Please do not reply directly to this email.
                    </div>
                </div>
            </body>
            </html>
            ";

            // Set content-type header for sending HTML email
            $headers = "MIME-Version: 1.0" . "\r\n";
            $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
            $headers .= "From: MOF HR Team<noreply@mof-eng.com>" . "\r\n";

            // Send email
            mail($to, $subject, $message, $headers);
            // --- 📧 SEND CONFIRMATION EMAIL END ---

            $_SESSION['notification'] = [
                'type' => 'success',
                'message' => 'Registration successful! A confirmation email has been sent.'
            ];
            $_SESSION['user_id'] = $stmt->insert_id;
            $_SESSION['role'] = 'user';
            header("Location: /user/dashboard.php");
            exit;
        } else {
            $err = "Registration failed due to a server error. Please try again.";
        }
    }
}
?>

<style>
    body {
        background: linear-gradient(135deg, #f0f4f8, #e9f7ef);
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }
    .register-card {
        border: none;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        overflow: hidden;
        background-color: #fff;
    }
    .form-label {
        font-weight: 600;
        color: #333;
    }
    small.text-muted {
        color: #6c757d !important;
    }
    .form-control {
        border-radius: 8px;
    }
    .btn-primary {
        background-color: #198754;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .btn-primary:hover {
        background-color: #157347;
    }
    .toggle-password i {
        font-size: 1.1rem;
    }
    .logo-top {
        max-width: 180px;
        height: auto;
        margin-bottom: 1rem;
    }
</style>

<div class="container my-5">
    <div class="row justify-content-center">
        <div class="col-lg-6 col-md-8 col-sm-10">

            <?php if ($notification): ?>
                <div class="alert alert-<?= $notification['type'] === 'success' ? 'success' : 'danger' ?> text-center mb-4" role="alert">
                    <?= htmlspecialchars($notification['message']) ?>
                </div>
            <?php endif; ?>

            <div class="card register-card p-4">
                <div class="card-body text-center">
                    <img src="https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png"
                         alt="MANAGING OF FUTURE ENG. (MOF) COMPANY Logo" class="logo-top">

                    <h3 class="fw-bold mb-4 text-success">Create Your Account</h3>

                    <?php if ($err): ?>
                        <div class="alert alert-danger text-center" role="alert"><?= htmlspecialchars($err) ?></div>
                    <?php endif; ?>

                    <form method="post">
                        <div class="mb-3 text-start">
                            <label for="name" class="form-label">Full Name</label>
                            <input type="text" id="name" name="name"
                                   class="form-control"
                                   placeholder="Enter your full name (e.g., John Doe)"
                                   value="<?= htmlspecialchars($name_val) ?>" required>
                            <small class="text-muted">Use your real name as on official documents.</small>
                        </div>

                        <div class="mb-3 text-start">
                            <label for="email" class="form-label">Email Address</label>
                            <input type="email" id="email" name="email"
                                   class="form-control"
                                   placeholder="e.g., john@example.com"
                                   value="<?= htmlspecialchars($email_val) ?>" required>
                            <small class="text-muted">This will be used for login and notifications.</small>
                        </div>

                        <div class="mb-4 text-start">
                            <label for="phone" class="form-label">Mobile Number</label>
                            <input type="text" id="phone" name="phone"
                                   class="form-control"
                                   placeholder="e.g., 0700 000 0000"
                                   value="<?= htmlspecialchars($phone_val) ?>" required>
                            <small class="text-muted">Include your valid phone number for HR communication.</small>
                        </div>

                        <div class="mb-3 text-start">
                            <label for="password" class="form-label">Password</label>
                            <div class="input-group">
                                <input type="password" id="password" name="password"
                                       class="form-control"
                                       placeholder="Create a strong password" required>
                                <button type="button" class="btn btn-outline-secondary toggle-password" data-target="password">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </div>
                            <small class="text-muted">Use at least 8 characters with letters and numbers.</small>
                        </div>

                        <div class="mb-4 text-start">
                            <label for="password_confirm" class="form-label">Confirm Password</label>
                            <div class="input-group">
                                <input type="password" id="password_confirm" name="password_confirm"
                                       class="form-control"
                                       placeholder="Re-enter your password" required>
                                <button type="button" class="btn btn-outline-secondary toggle-password" data-target="password_confirm">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </div>
                            <small class="text-muted">Must match the password above exactly.</small>
                        </div>

                        <div class="d-grid gap-2">
                            <button class="btn btn-primary btn-lg" type="submit">Register Account</button>
                        </div>
                    </form>
                </div>
            </div>

            <p class="text-center mt-3">
                Already have an account? <a href="/auth/login.php" class="fw-bold text-success">Login here</a>
            </p>

        </div>
    </div>
</div>

<script>
document.querySelectorAll('.toggle-password').forEach(btn => {
  btn.addEventListener('click', function() {
    const targetId = this.getAttribute('data-target');
    const input = document.getElementById(targetId);
    const icon = this.querySelector('i');
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    icon.classList.toggle('bi-eye');
    icon.classList.toggle('bi-eye-slash');
  });
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>