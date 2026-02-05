<?php
$page_title = "Reset Password";
require __DIR__ . '/../db.php';
include __DIR__ . '/../includes/header.php';

$token = $_GET['token'] ?? '';
$err = ''; $success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = $_POST['token'];
    $new_pass = $_POST['password'];
    $confirm_pass = $_POST['confirm_password'];

    if ($new_pass !== $confirm_pass) {
        $err = "Passwords do not match.";
    } else {
        // Fetch user data including email for the notification
        $q = $conn->prepare("SELECT id, name, email FROM users WHERE reset_token=? AND reset_expires > NOW() LIMIT 1");
        $q->bind_param("s", $token);
        $q->execute();
        $res = $q->get_result();

        if ($u = $res->fetch_assoc()) {
            $user_id = $u['id'];
            $user_email = $u['email'];
            $user_name = $u['name'];

            $hash = password_hash($new_pass, PASSWORD_BCRYPT);
            $upd = $conn->prepare("UPDATE users SET password_hash=?, reset_token=NULL, reset_expires=NULL WHERE id=?");
            $upd->bind_param("si", $hash, $user_id);
            
            if ($upd->execute()) {
                $success = "Password reset successful! You can now login.";

                // ✅ SEND CONFIRMATION EMAIL
                $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
                $to = $user_email;
                $subject = "Security Alert: Password Changed - MOF-ENG";
                $headers = "MIME-Version: 1.0\r\nContent-type:text/html;charset=UTF-8\r\nFrom: MOF-ENG Security <noreply@mof-eng.com>\r\n";

                $message = "
                <html>
                <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                    <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                        
                        <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                            <img src='$logo_url' alt='MOF-ENG Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                            <h2 style='color: #198754; margin: 0; font-size: 22px;'>Password Changed Successfully</h2>
                        </div>

                        <p style='font-size: 16px;'>Dear <strong>$user_name</strong>,</p>
                        
                        <p>This is a confirmation that the password for your account at <strong>Managing Of Future Eng. Company (MOF-ENG)</strong> has been successfully changed.</p>
                        
                        <div style='background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; margin: 20px 0;'>
                            <p style='margin: 0; font-size: 14px; color: #856404;'>
                                <strong>Important:</strong> If you did not make this change, please contact our HR or IT support team immediately as your account security may be compromised.
                            </p>
                        </div>

                        <p>If this was you, you can now log in using your new password:</p>

                        <p style='margin-top: 30px; text-align: center;'>
                            <a href='https://jobs.mof-eng.com/auth/login.php' 
                               style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                               Login to Your Account
                            </a>
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
                                            <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG COMPANY</span><br>
                                            <strong>Tel:</strong> 07705330101<br>
                                            <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                            &copy; " . date('Y') . " MOF-ENG. All rights reserved.
                        </div>
                    </div>
                </body>
                </html>";

                mail($to, $subject, $message, $headers);
            }
        } else {
            $err = "Invalid or expired token.";
        }
    }
}
?>

<div class="container my-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card p-4 shadow-sm border-0" style="border-radius:16px;">
                <h3 class="text-center text-success fw-bold">Set New Password</h3>
                <?php if($err): ?> <div class="alert alert-danger"><?=$err?></div> <?php endif; ?>
                <?php if($success): ?> <div class="alert alert-success"><?=$success?> <a href="login.php">Login here</a></div> <?php endif; ?>
                
                <?php if(!$success): ?>
                <form method="post">
                    <input type="hidden" name="token" value="<?=htmlspecialchars($token)?>">
                    <div class="mb-3">
                        <label class="form-label">New Password</label>
                        <input type="password" name="password" class="form-control" required minlength="8">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Confirm New Password</label>
                        <input type="password" name="confirm_password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100 fw-bold">Update Password</button>
                </form>
                <?php endif; ?>
            </div>
        </div>
    </div>
</div>
<?php include __DIR__ . '/../includes/footer.php'; ?>