<?php
// /apply.php — Job Application Form + Submission Handler
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/includes/helpers.php';
require_once __DIR__ . '/includes/auth_user.php';

include __DIR__ . '/includes/header.php';

$uid = (int)($_SESSION['user_id'] ?? 0);
$message = '';
$alert = '';
$position = null;
$already_applied = false;

// 1. Determine Position ID from GET or POST
$position_id = isset($_GET['position_id']) ? (int) $_GET['position_id'] : (int)($_POST['position_id'] ?? 0);

// 2. CHECK IF ALREADY APPLIED
if ($uid > 0 && $position_id > 0) {
    $check_stmt = $conn->prepare("SELECT id FROM job_applications WHERE user_id = ? AND position_id = ?");
    $check_stmt->bind_param("ii", $uid, $position_id);
    $check_stmt->execute();
    $check_res = $check_stmt->get_result();
    if ($check_res->num_rows > 0) {
        $already_applied = true;
    }
    $check_stmt->close();
}

// ✅ Handle submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $expected_salary = trim($_POST['expected_salary'] ?? '');
    $years_experience = isset($_POST['years_experience']) ? trim($_POST['years_experience']) : '';
    $message_text = trim($_POST['message'] ?? '');
    $source = trim($_POST['source'] ?? '');
    $pos_name = trim($_POST['position_name_hidden'] ?? 'Job Position');

    // Validation
    if ($position_id <= 0 || $uid === 0) {
        $alert = "❌ Invalid request.";
    } elseif ($already_applied) {
        $alert = "❌ You have already submitted an application for this position.";
    } elseif (empty($expected_salary) || $years_experience === '' || empty($message_text) || empty($source)) {
        $alert = "❌ All fields are mandatory. Please fill out the entire form.";
    } elseif (empty($_FILES['cv']['name'])) {
        $alert = "❌ Please upload your CV file.";
    } else {
        // Handle CV Upload
        $cv_filename = $_FILES['cv']['name'];
        $tmp_name = $_FILES['cv']['tmp_name'];
        $ext = strtolower(pathinfo($cv_filename, PATHINFO_EXTENSION));
        $allowed = ['pdf', 'doc', 'docx'];

        if (!in_array($ext, $allowed)) {
            $alert = "❌ Only PDF, DOC, or DOCX files are allowed.";
        } else {
            $new_name = 'cv_' . uniqid() . '.' . $ext;
            $upload_dir = $_SERVER['DOCUMENT_ROOT'] . '/uploads/';
            if (!is_dir($upload_dir)) mkdir($upload_dir, 0755, true);
            $dest_path = $upload_dir . $new_name;

            if (move_uploaded_file($tmp_name, $dest_path)) {
                $resume_path = '/uploads/' . $new_name;

                // Insert into Database
                $stmt = $conn->prepare("
                    INSERT INTO job_applications 
                    (user_id, position_id, expected_salary, years_experience, message, cv_filename, resume_path, source, status, applied_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'New', NOW())
                ");
                $stmt->bind_param("iissssss", $uid, $position_id, $expected_salary, $years_experience, $message_text, $cv_filename, $resume_path, $source);
                
                if ($stmt->execute()) {
                    // Fetch User Info for Email
                    $user_stmt = $conn->prepare("SELECT name, email FROM users WHERE id = ?");
                    $user_stmt->bind_param("i", $uid);
                    $user_stmt->execute();
                    $user_res = $user_stmt->get_result()->fetch_assoc();
                    $target_email = $user_res['email'] ?? '';
                    $user_name = $user_res['name'] ?? 'Applicant';
                    $user_stmt->close();

                    // 5. Professional Email Template (Restored)
                    if (!empty($target_email)) {
                        $logo_url = "https://mof-eng.com/wp-content/uploads/2025/05/cropped-MOF-LOGO-transparent--100x46.png";
                        $to = $target_email;
                        $subject = "Application Received: " . $pos_name;
                        
                        $headers = "MIME-Version: 1.0" . "\r\n";
                        $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
                        $headers .= "From: MOF HR Team<no-reply@mof-eng.com>" . "\r\n";

                        $email_body = "
                        <html>
                        <body style='font-family: \"Segoe UI\", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f9f9f9;'>
                            <div style='max-width: 650px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'>
                                
                                <div style='text-align: center; border-bottom: 2px solid #198754; padding-bottom: 20px; margin-bottom: 30px;'>
                                    <img src='$logo_url' alt='MANAGING OF FUTURE ENG. (MOF) COMPANY Logo' style='height: 50px; width: auto; margin-bottom: 10px;'>
                                    <h2 style='color: #198754; margin: 0; font-size: 22px;'>Application Received</h2>
                                </div>

                                <p style='font-size: 16px;'>Dear <strong>$user_name</strong>,</p>
                                
                                <p>Thank you for applying for the <strong>" . htmlspecialchars($pos_name) . "</strong> position at <strong>MANAGING OF FUTURE ENG. (MOF) COMPANY</strong>.</p>
                                
                                <p>We have received your application details as summarized below:</p>
                                
                                <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;'>
                                    <table style='width: 100%; border-collapse: collapse;'>
                                        <tr>
                                            <td style='padding: 8px 0; width: 150px; color: #666;'><strong>Position:</strong></td>
                                            <td style='padding: 8px 0;'>" . htmlspecialchars($pos_name) . "</td>
                                        </tr>
                                        <tr>
                                            <td style='padding: 8px 0; color: #666;'><strong>Experience:</strong></td>
                                            <td style='padding: 8px 0;'>" . htmlspecialchars($years_experience) . " Years</td>
                                        </tr>
                                        <tr>
                                            <td style='padding: 8px 0; color: #666;'><strong>Expected Salary:</strong></td>
                                            <td style='padding: 8px 0;'>" . htmlspecialchars($expected_salary) . " IQD</td>
                                        </tr>
                                    </table>
                                </div>

                                <p>Our recruitment team will review your qualifications and contact you if your profile matches our requirements for the next stage of the hiring process.</p>

                                <p style='margin-top: 30px; text-align: center;'>
                                    <a href='https://jobs.mof-eng.com/user/dashboard.php' 
                                       style='background-color: #198754; color: #ffffff; padding: 14px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>
                                       Track Application Status
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
                                                <p style='margin: 5px 0;'><strong>Recruitment Team</strong></p>
                                                
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
                                    &copy; " . date('Y') . " MANAGING OF FUTURE ENG. (MOF) COMPANY. All rights reserved.
                                </div>
                            </div>
                        </body>
                        </html>";

                        mail($to, $subject, $email_body, $headers);
                    }

                    $_SESSION['flash_success'] = "✅ Application submitted successfully!";
                    header("Location: /user/dashboard.php");
                    exit;
                } else {
                    $alert = "❌ Database error: " . htmlspecialchars($stmt->error);
                }
                $stmt->close();
            } else {
                $alert = "❌ Failed to upload CV file.";
            }
        }
    }
}

// Fetch Position Data for Display
if ($position_id > 0) {
    $stmt = $conn->prepare("SELECT id, position_name, location, employment_type, description FROM job_positions WHERE id = ? AND status='active'");
    $stmt->bind_param("i", $position_id);
    $stmt->execute();
    $position = $stmt->get_result()->fetch_assoc();
    $stmt->close();
}
?>

<div class="container py-5">
  <?php if (!empty($alert)): ?>
    <div class="alert alert-danger text-center shadow-sm"><?= $alert ?></div>
  <?php endif; ?>

  <?php if (!$position): ?>
    <div class="alert alert-danger text-center shadow-sm">❌ Invalid or unavailable job position.</div>
  <?php elseif ($already_applied): ?>
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-body p-5 text-center">
            <h2 class="text-success mb-3"><i class="bi bi-check2-circle"></i> Already Applied</h2>
            <p class="lead">You have already submitted an application for the <strong><?= htmlspecialchars($position['position_name']) ?></strong> position.</p>
            <a href="/user/dashboard.php" class="btn btn-success mt-3">View My Applications</a>
        </div>
    </div>
  <?php else: ?>
    <div class="row justify-content-center">
      <div class="col-lg-8">
        <div class="card border-0 shadow-sm mb-4">
            <div class="card-body p-4">
                <h2 class="fw-bold text-success mb-3"><?= htmlspecialchars($position['position_name']) ?></h2>
                <div class="d-flex flex-wrap gap-3 mb-4">
                    <span class="badge bg-light text-dark border p-2">📍 <?= htmlspecialchars($position['location'] ?: 'Not Specified') ?></span>
                    <span class="badge bg-light text-dark border p-2">⏰ <?= ucwords(htmlspecialchars($position['employment_type'] ?: 'Full Time')) ?></span>
                </div>
                <h5 class="fw-bold border-bottom pb-2">Job Description</h5>
                <p class="text-muted" style="white-space: pre-line; line-height: 1.7;"><?= htmlspecialchars($position['description'] ?: 'No description provided.') ?></p>
            </div>
        </div>

        <h4 class="fw-bold mb-3 mt-5">Submit Your Application</h4>
        <form method="post" action="apply.php" enctype="multipart/form-data" class="border p-4 bg-white shadow-sm rounded-3">
          <input type="hidden" name="position_id" value="<?= $position_id ?>">
          <input type="hidden" name="position_name_hidden" value="<?= htmlspecialchars($position['position_name']) ?>">

          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label fw-semibold">Years of Experience <span class="text-danger">*</span></label>
              <input type="number" name="years_experience" class="form-control" min="0" required>
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Expected Salary (IQD) <span class="text-danger">*</span></label>
              <input type="number" step="0.01" name="expected_salary" class="form-control" required>
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">Where did you hear about this job? <span class="text-danger">*</span></label>
              <select name="source" class="form-select" required>
                <option value="" disabled selected>-- Select an option --</option>
                <option value="Website">Website</option>
                <option value="LinkedIn">LinkedIn</option>
                <option value="Referral">Referral</option>
                <option value="Walk-in">Walk-in</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">Message / Cover Letter <span class="text-danger">*</span></label>
              <textarea name="message" class="form-control" rows="4" placeholder="Briefly describe your fit for this role..." required></textarea>
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">Upload CV (PDF, DOC, DOCX) <span class="text-danger">*</span></label>
              <input type="file" name="cv" class="form-control" accept=".pdf,.doc,.docx" required>
            </div>
          </div>

          <button type="submit" class="btn btn-success btn-lg w-100 mt-4 shadow-sm">
            <i class="bi bi-send-check-fill me-2"></i> Confirm & Submit Application
          </button>
        </form>
      </div>
    </div>
  <?php endif; ?>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>