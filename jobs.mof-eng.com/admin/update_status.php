<?php
// /admin/update_status.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

$application_id = isset($_POST['application_id']) ? (int)$_POST['application_id'] : (int)($_POST['id'] ?? 0);
$status = trim($_POST['status'] ?? '');

if ($application_id <= 0 || $status === '') {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Missing application_id or status']);
    exit;
}

$allowed_statuses = ['New','Screening','Interview','Offer','Hired','Future Consideration','Rejected'];
if (!in_array($status, $allowed_statuses, true)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid status value']);
    exit;
}

// Update the status
$upd = $conn->prepare("UPDATE job_applications SET status=? WHERE id=?");
$upd->bind_param("si", $status, $application_id);
$ok = $upd->execute();
$affected = $upd->affected_rows;
$upd->close();

if (!$ok) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'DB error']);
    exit;
}

// ✅ TRIGGER EMAIL: Only if status actually changed
if ($affected > 0) {
    $query = "SELECT u.email, u.name, p.position_name 
              FROM job_applications a 
              JOIN users u ON a.user_id = u.id 
              JOIN job_positions p ON a.position_id = p.id 
              WHERE a.id = ? LIMIT 1";
    $stmt = $conn->prepare($query);
    $stmt->bind_param("i", $application_id);
    $stmt->execute();
    $user = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if ($user && !empty($user['email'])) {
        $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
        $to = $user['email'];
        $subject = "Application Status Update: " . $user['position_name'];
        $headers = "MIME-Version: 1.0\r\nContent-type:text/html;charset=UTF-8\r\nFrom: MOF HR Team <no-reply@mof-eng.com>\r\n";

        // Tailor the secondary message based on status
        $status_note = match($status) {
            'Interview' => "Our team would like to move forward with an interview. We will contact you shortly to schedule a time.",
            'Offer' => "Congratulations! We have extended an offer for this position. Please check your portal for details.",
            'Hired' => "Welcome to the team! Your application process is complete and you have been marked as Hired.",
            'Future Consideration' => "Thank you for your interest in MANAGING OF FUTURE ENG. (MOF) COMPANY. We will consider your CV for our future positions.",
            'Rejected' => "Thank you for your interest in MANAGING OF FUTURE ENG. (MOF) COMPANY. At this time, we have decided to move forward with other candidates.",
            default => "Your application status has been updated to <strong>$status</strong>. Our team is currently reviewing your profile."
        };

        $email_body = "
        <html>
        <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
            <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                
                <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                    <img src='$logo_url' alt='MANAGING OF FUTURE ENG. (MOF) COMPANY Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                    <h2 style='color: #198754; margin: 0; font-size: 22px;'>Status Update</h2>
                </div>

                <p style='font-size: 16px;'>Dear <strong>" . htmlspecialchars($user['name']) . "</strong>,</p>
                
                <p>The status of your application for the <strong>" . htmlspecialchars($user['position_name']) . "</strong> position has been updated.</p>
                
                <div style='background-color: #f8f9fa; border-radius: 6px; padding: 20px; margin: 25px 0; text-align: center;'>
                    <span style='color: #666; text-transform: uppercase; font-size: 12px; font-weight: bold; letter-spacing: 1px;'>New Status</span><br>
                    <span style='color: #198754; font-size: 24px; font-weight: bold;'>$status</span>
                </div>

                <p style='color: #555;'>$status_note</p>

                <p style='margin-top: 30px; text-align: center;'>
                    <a href='https://jobs.mof-eng.com/user/dashboard.php' 
                       style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                       View My Application
                    </a>
                </p>

                <div style='margin-top: 50px; padding-top: 25px; border-top: 1px solid #eee;'>
                    <table style='width: 100%;'>
                        <tr>
                            <td style='vertical-align: top; width: 120px;'>
                                <img src='$logo_url' alt='MANAGING OF FUTURE ENG. (MOF) COMPANY' style='width: 100px; height: auto; margin-top: 10px;'>
                            </td>
                            <td style='vertical-align: top; padding-left: 20px; border-left: 1px solid #ddd;'>
                                <p style='margin: 0; font-weight: bold; color: #198754;'>Best regards,</p>
                                <p style='margin: 5px 0;'><strong>Human Resources Team</strong></p>
                                
                                <div style='font-size: 13px; color: #555; line-height: 1.6;'>
                                    <span style='color: #000; font-weight: bold;'>MANAGING OF FUTURE ENG. (MOF) COMPANY</span><br>
                                    <strong>Tel:</strong> 07705330101<br>
                                    <strong>Web:</strong> <a href='https://www.mof-eng.com' style='color: #198754; text-decoration: none;'>www.mof-eng.com</a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>

                <div style='margin-top: 40px; font-size: 11px; color: #999; text-align: center;'>
                    &copy; " . date('Y') . " MANAGING OF FUTURE ENG. (MOF) COMPANY. All rights reserved.
                </div>
            </div>
        </body>
        </html>";

        mail($to, $subject, $email_body, $headers);
    }
}

echo json_encode(['ok' => true, 'id' => $application_id, 'status' => $status, 'changed' => ($affected > 0)]);
exit;