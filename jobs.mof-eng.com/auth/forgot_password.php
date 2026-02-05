<?php
$page_title = "Forgot Password";
require __DIR__ . '/../db.php';
if (session_status() === PHP_SESSION_NONE) session_start();
include __DIR__ . '/../includes/header.php';

$msg = '';
$type = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email']);
    
    $q = $conn->prepare("SELECT id FROM users WHERE email=? LIMIT 1");
    $q->bind_param("s", $email);
    $q->execute();
    $res = $q->get_result();

    if ($res->num_rows > 0) {
        $token = bin2hex(random_bytes(32));
        $expires = date("Y-m-d H:i:s", strtotime("+1 hour"));
        
        $upd = $conn->prepare("UPDATE users SET reset_token=?, reset_expires=? WHERE email=?");
        $upd->bind_param("sss", $token, $expires, $email);
        $upd->execute();

        $reset_link = "https://jobs.mof-eng.com/auth/reset_password.php?token=" . $token;
        
// ✅ Professional Password Reset Email Template
        $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
        $to = $email;
        $subject = "Password Reset Request - MOF-ENG";
        $headers = "MIME-Version: 1.0\r\nContent-type:text/html;charset=UTF-8\r\nFrom: MOF HR Team <noreply@mof-eng.com>\r\n";
        
        $message = "
        <html>
        <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
            <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                
                <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                    <img src='$logo_url' alt='MOF-ENG Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                    <h2 style='color: #198754; margin: 0; font-size: 22px;'>Password Reset Request</h2>
                </div>

                <p style='font-size: 16px;'>Hello,</p>
                
                <p>We received a request to reset the password for your account at <strong>MANAGING OF FUTURE ENG. (MOF) COMPANY</strong>.</p>
                
                <p>Please click the button below to choose a new password. For your security, <strong>this link will expire in 1 hour.</strong></p>
                
                <p style='margin-top: 30px; text-align: center;'>
                    <a href='$reset_link' 
                       style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                       Reset Your Password
                    </a>
                </p>

                <p style='margin-top: 25px; font-size: 14px; color: #666;'>
                    If you did not request a password reset, please ignore this email or contact our support team if you have concerns. No changes will be made to your account.
                </p>

                <div style='margin-top: 50px; padding-top: 25px; border-top: 1px solid #eee;'>
                    <table style='width: 100%;'>
                        <tr>
                            <td style='vertical-align: top; width: 120px;'>
                                <img src='$logo_url' alt='MOF-ENG' style='width: 100px; height: auto; margin-top: 10px;'>
                            </td>
                            <td style='vertical-align: top; padding-left: 20px; border-left: 1px solid #ddd;'>
                                <p style='margin: 0; font-weight: bold; color: #198754;'>Best regards,</p>
                                <p style='margin: 5px 0;'><strong>HR & IT Support Team</strong></p>
                                
                                <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                    <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG. (MOF) COMPANY</span><br>
                                    <strong>Tel:</strong> 07705330101<br>
                                    <strong>Address:</strong> House NO. A1-345, New Chwarchra, Slemani, Iraq.<br>
                                    <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>

                <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                    &copy; " . date('Y') . " MOF-ENG. All rights reserved.<br>
                    Security Notice: Never share your password or reset link with anyone.
                </div>
            </div>
        </body>
        </html>";

        mail($to, $subject, $message, $headers);
    }
    // Always show success to prevent email enumeration
    $msg = "If an account exists with that email, a reset link has been sent.";
    $type = "success";
}
?>

<div class="container my-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card p-4 shadow-sm border-0" style="border-radius:16px;">
                <h3 class="text-center text-success fw-bold">Forgot Password</h3>
                <p class="text-center text-muted">Enter your email to receive a reset link.</p>
                <?php if($msg): ?>
                    <div class="alert alert-<?=$type?>"><?=$msg?></div>
                <?php endif; ?>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Email Address</label>
                        <input type="email" name="email" class="form-control" required placeholder="e.g. john@example.com">
                    </div>
                    <button type="submit" class="btn btn-success w-100 fw-bold">Send Reset Link</button>
                    <div class="text-center mt-3">
                        <a href="login.php" class="text-muted small text-decoration-none">Return to Login</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
<?php include __DIR__ . '/../includes/footer.php'; ?>