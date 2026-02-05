<?php
// /user/application_delete.php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';

$app_id = (int)($_POST['id'] ?? 0);
$uid    = (int)($_SESSION['user_id'] ?? 0);

if (!$app_id || !$uid) {
    $_SESSION['flash_error'] = "Invalid request.";
    header("Location: /user/dashboard.php");
    exit;
}

// Delete only if owned by current user
$stmt = $conn->prepare("DELETE FROM job_applications WHERE id=? AND user_id=?");
$stmt->bind_param("ii", $app_id, $uid);
if ($stmt->execute()) {
    $_SESSION['flash_success'] = "✅ Application deleted successfully!";
} else {
    $_SESSION['flash_error'] = "❌ Failed to delete application.";
}
$stmt->close();

header("Location: /user/dashboard.php");
exit;
