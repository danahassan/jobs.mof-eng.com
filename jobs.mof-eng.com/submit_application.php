<?php
session_start();
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

require __DIR__ . '/db.php';
require __DIR__ . '/includes/helpers.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user_id          = (int)($_SESSION['user_id'] ?? 0);
    $position_id      = (int)($_POST['position_id'] ?? 0);
    $expected_salary  = trim($_POST['expected_salary'] ?? '');
    $years_experience = (int)($_POST['years_experience'] ?? 0);
    $source           = trim($_POST['source'] ?? 'Website');
    $message          = trim($_POST['message'] ?? '');

    // ✅ Basic validation
    if (!$user_id || !$position_id || !$expected_salary || $years_experience < 0) {
        $_SESSION['flash_error'] = "❌ Please fill in all required fields.";
        header("Location: /apply.php?position_id=" . $position_id);
        exit;
    }

    // ✅ Validate position existence
    $stmt = $conn->prepare("SELECT position_name FROM job_positions WHERE id=? AND status='active'");
    $stmt->bind_param("i", $position_id);
    $stmt->execute();
    $pos = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if (!$pos) {
        $_SESSION['flash_error'] = "❌ Invalid or inactive job position.";
        header("Location: /jobs.php");
        exit;
    }

    // ✅ Handle CV upload
    $cv_filename = null;
    $resume_path = null;

    if (!empty($_FILES['cv']['name'])) {
        $ext = strtolower(pathinfo($_FILES['cv']['name'], PATHINFO_EXTENSION));
        $allowed = ['pdf', 'doc', 'docx'];
        if (!in_array($ext, $allowed)) {
            $_SESSION['flash_error'] = "❌ Invalid CV format. Only PDF, DOC, or DOCX allowed.";
            header("Location: /apply.php?position_id=" . $position_id);
            exit;
        }

        $upload_dir = $_SERVER['DOCUMENT_ROOT'] . '/uploads/';
        if (!is_dir($upload_dir)) mkdir($upload_dir, 0755, true);

        $cv_filename = 'cv_' . uniqid() . '.' . $ext;
        $resume_path = '/uploads/' . $cv_filename;
        move_uploaded_file($_FILES['cv']['tmp_name'], $upload_dir . $cv_filename);
    } else {
        $_SESSION['flash_error'] = "❌ Please upload your CV file.";
        header("Location: /apply.php?position_id=" . $position_id);
        exit;
    }

    // ✅ Insert into job_applications
    $stmt = $conn->prepare("
        INSERT INTO job_applications 
        (user_id, position_id, expected_salary, years_experience, message, cv_filename, resume_path, source, status, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', NOW())
    ");
    $stmt->bind_param(
        "iissssss",
        $user_id,
        $position_id,
        $expected_salary,
        $years_experience,
        $message,
        $cv_filename,
        $resume_path,
        $source
    );

    if ($stmt->execute()) {
        $_SESSION['flash_success'] = "✅ Application submitted successfully!";
        header("Location: /user/dashboard.php");
        exit;
    } else {
        $_SESSION['flash_error'] = "❌ Database error: " . htmlspecialchars($stmt->error);
        header("Location: /apply.php?position_id=" . $position_id);
        exit;
    }
}
?>
