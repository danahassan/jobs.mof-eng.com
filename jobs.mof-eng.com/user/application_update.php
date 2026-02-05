<?php
// /user/application_update.php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';

$uid    = (int)($_SESSION['user_id'] ?? 0);
$app_id = (int)($_POST['id'] ?? 0);

if (!$uid || !$app_id) {
    $_SESSION['flash_error'] = "Invalid request.";
    header("Location: /user/dashboard.php");
    exit;
}

// Ensure ownership
$chk = $conn->prepare("SELECT id FROM job_applications WHERE id=? AND user_id=?");
$chk->bind_param("ii", $app_id, $uid);
$chk->execute();
$chk->store_result();
if ($chk->num_rows === 0) {
    $chk->close();
    $_SESSION['flash_error'] = "Application not found or access denied.";
    header("Location: /user/dashboard.php");
    exit;
}
$chk->close();

// Collect fields
$f = function($k){ return trim((string)($_POST[$k] ?? '')); };
$position_id = (int)($_POST['position_id'] ?? 0);
$years_experience = (int)($_POST['years_experience'] ?? 0);
$expected_salary  = (string)($_POST['expected_salary'] ?? '');
$source = $f('source');
$message = $f('message');

// Handle CV upload (optional)
$cv_filename = null;
$resume_path = null;

if (!empty($_FILES['cv']['name'])) {
    $orig = $_FILES['cv']['name'];
    $tmp  = $_FILES['cv']['tmp_name'];
    $ext  = strtolower(pathinfo($orig, PATHINFO_EXTENSION));
    $ok   = in_array($ext, ['pdf','doc','docx']);

    if ($ok && is_uploaded_file($tmp)) {
        $newName = 'cv_' . uniqid('', true) . '.' . $ext;
        $destRel = '/uploads/' . $newName;
        $destAbs = $_SERVER['DOCUMENT_ROOT'] . $destRel;
        if (@move_uploaded_file($tmp, $destAbs)) {
            $cv_filename = $newName;
            $resume_path = ltrim($destRel, '/');
        }
    }
}

if ($cv_filename !== null) {
    $stmt = $conn->prepare("
      UPDATE job_applications
      SET position_id=?, years_experience=?, expected_salary=?, source=?, message=?, cv_filename=?, resume_path=?
      WHERE id=? AND user_id=?
    ");
    $stmt->bind_param(
        "iisssssii",
        $position_id, $years_experience, $expected_salary, $source, $message, $cv_filename, $resume_path,
        $app_id, $uid
    );
} else {
    $stmt = $conn->prepare("
      UPDATE job_applications
      SET position_id=?, years_experience=?, expected_salary=?, source=?, message=?
      WHERE id=? AND user_id=?
    ");
    $stmt->bind_param(
        "iisssii",
        $position_id, $years_experience, $expected_salary, $source, $message,
        $app_id, $uid
    );
}

if ($stmt->execute()) {
    $_SESSION['flash_success'] = "✅ Application updated successfully!";
} else {
    $_SESSION['flash_error'] = "❌ Update failed: " . htmlspecialchars($stmt->error);
}
$stmt->close();

header("Location: /user/dashboard.php");
exit;
