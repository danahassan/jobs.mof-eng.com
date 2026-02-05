<?php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';

$uid     = (int)($_SESSION['user_id'] ?? 0);
$appId   = (int)($_POST['application_id'] ?? 0);
$comment = trim($_POST['comment'] ?? '');

if ($uid > 0 && $appId > 0 && $comment !== '') {

    // Insert applicant comment (visible to applicant)
    $stmt = $conn->prepare("
        INSERT INTO application_comments (application_id, user_id, comment, author_role, visible_to_applicant, created_at)
        VALUES (?, ?, ?, 'user', 1, NOW())
    ");
    $stmt->bind_param("iis", $appId, $uid, $comment);

    if ($stmt->execute()) {

        // ✅ TRIGGER EMAIL TO ADMIN (when applicant adds a comment)
        $query = "SELECT u.name, u.email, p.position_name
                  FROM job_applications a
                  JOIN users u ON a.user_id = u.id
                  JOIN job_positions p ON a.position_id = p.id
                  WHERE a.id = ? AND a.user_id = ?
                  LIMIT 1";
        $e_stmt = $conn->prepare($query);
        $e_stmt->bind_param("ii", $appId, $uid);
        $e_stmt->execute();
        $user = $e_stmt->get_result()->fetch_assoc();
        $e_stmt->close();

        if ($user) {
            $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";

            $to = "admin@mof-eng.com";
            $subject = "New Applicant Comment: " . ($user['position_name'] ?? 'Job Application');

            $headers = "MIME-Version: 1.0" . "\r\n";
            $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
            $headers .= "From: MOF Jobs Portal <no-reply@mof-eng.com>" . "\r\n";

            $email_body = "
            <html>
            <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                    
                    <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                        <img src='$logo_url' alt='MOF-ENG Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                        <h2 style='color: #198754; margin: 0; font-size: 22px;'>New Applicant Comment</h2>
                    </div>

                    <p style='font-size: 16px;'>
                        An applicant has posted a new comment on their application.
                    </p>

                    <table style='width: 100%; border-collapse: collapse; margin: 20px 0;'>
                        <tr>
                            <td style='padding: 8px 0; width: 160px; color: #666;'><strong>Applicant:</strong></td>
                            <td style='padding: 8px 0;'>" . htmlspecialchars($user['name'] ?? 'N/A') . "</td>
                        </tr>
                        <tr>
                            <td style='padding: 8px 0; color: #666;'><strong>Email:</strong></td>
                            <td style='padding: 8px 0;'>" . htmlspecialchars($user['email'] ?? 'N/A') . "</td>
                        </tr>
                        <tr>
                            <td style='padding: 8px 0; color: #666;'><strong>Position:</strong></td>
                            <td style='padding: 8px 0;'>" . htmlspecialchars($user['position_name'] ?? 'N/A') . "</td>
                        </tr>
                        <tr>
                            <td style='padding: 8px 0; color: #666;'><strong>Application ID:</strong></td>
                            <td style='padding: 8px 0;'>" . (int)$appId . "</td>
                        </tr>
                    </table>

                    <div style='background-color: #fff3cd; border-left: 5px solid #fd7e14; padding: 20px; margin: 25px 0; font-style: italic; color: #444;'>
                        " . nl2br(htmlspecialchars($comment)) . "
                    </div>

                    <p style='margin-top: 30px; text-align: center;'>
                        <a href='https://jobs.mof-eng.com/admin/application_detail.php?id=" . (int)$appId . "'
                           style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                           Open Application Details
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
                                    <p style='margin: 5px 0;'><strong>MOF Jobs Portal</strong></p>

                                    <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                        <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG. (MOF) COMPANY</span><br>
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
                        This is an automated notification from the job portal.
                    </div>
                </div>
            </body>
            </html>";

            mail($to, $subject, $email_body, $headers);
        }

        http_response_code(200);
        $stmt->close();
        exit;
    }

    $stmt->close();
}

http_response_code(400);
