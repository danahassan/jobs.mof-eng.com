<?php
// /admin/save_comment.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $application_id = (int)($_POST['application_id'] ?? 0);
    $comment = trim($_POST['comment'] ?? '');
    $visible_to_applicant = isset($_POST['visible_to_applicant']) ? (int)$_POST['visible_to_applicant'] : 0;
    $user_id = $_SESSION['user_id'] ?? 0;

    if ($application_id > 0 && $comment !== '' && $user_id > 0) {
        $stmt = $conn->prepare("
            INSERT INTO application_comments (application_id, user_id, comment, visible_to_applicant, created_at)
            VALUES (?, ?, ?, ?, NOW())
        ");
        $stmt->bind_param("iisi", $application_id, $user_id, $comment, $visible_to_applicant);
        
        if ($stmt->execute()) {
            // ✅ TRIGGER EMAIL: Only if the comment is set to be visible to applicant
            if ($visible_to_applicant === 1) {
                $query = "SELECT u.email, u.name, p.position_name 
                          FROM job_applications a 
                          JOIN users u ON a.user_id = u.id 
                          JOIN job_positions p ON a.position_id = p.id 
                          WHERE a.id = ? LIMIT 1";
                $e_stmt = $conn->prepare($query);
                $e_stmt->bind_param("i", $application_id);
                $e_stmt->execute();
                $user = $e_stmt->get_result()->fetch_assoc();
                $e_stmt->close();

                if ($user && !empty($user['email'])) {
                    $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
                    $to = $user['email'];
                    $subject = "New Comment on your application: " . $user['position_name'];
                    
                    $headers = "MIME-Version: 1.0" . "\r\n";
                    $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
                    $headers .= "From: MOF HR Team <no-reply@mof-eng.com>" . "\r\n";

                    $email_body = "
                    <html>
                    <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                        <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                            
                            <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                                <img src='$logo_url' alt='MOF-ENG Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                                <h2 style='color: #198754; margin: 0; font-size: 22px;'>New Application Comment</h2>
                            </div>

                            <p style='font-size: 16px;'>Dear <strong>" . htmlspecialchars($user['name']) . "</strong>,</p>
                            
                            <p>An HR representative has added a new comment regarding your application for the <strong>" . htmlspecialchars($user['position_name']) . "</strong> position:</p>
                            
                            <div style='background-color: #f8f9fa; border-left: 5px solid #198754; padding: 20px; margin: 25px 0; font-style: italic; color: #444;'>
                                " . nl2br(htmlspecialchars($comment)) . "
                            </div>

                            <p>If you have any questions or need to provide further information, please log in to your applicant portal to respond.</p>

                            <p style='margin-top: 30px; text-align: center;'>
                                <a href='https://jobs.mof-eng.com/user/dashboard.php' 
                                   style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                                   View Application Dashboard
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
                                            <p style='margin: 5px 0;'><strong>HR Recruitment Team</strong></p>
                                            
                                            <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                                <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG COMPANY</span><br>
                                                <strong>Tel:</strong> 07705330101<br>
                                                <strong>Address:</strong> House NO. A1-345, New Chwarchra, Near Sara petrol station, Slemani, Iraq.<br>
                                                <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                                &copy; " . date('Y') . " MOF-ENG. All rights reserved.<br>
                                This is an automated notification regarding your job application.
                            </div>
                        </div>
                    </body>
                    </html>";

                    mail($to, $subject, $email_body, $headers);
                }
            }
        }
        $stmt->close();
    }
}

// Redirect back to the application detail page
header("Location: /admin/application_detail.php?id=" . urlencode($application_id));
exit;