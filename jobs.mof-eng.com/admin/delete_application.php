<?php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['id'])) {
    $id = (int)$_POST['id'];

    // Delete comments linked to the application
    $conn->query("DELETE FROM application_comments WHERE application_id = $id");

    // Delete the application itself
    $stmt = $conn->prepare("DELETE FROM job_applications WHERE id = ?");
    $stmt->bind_param("i", $id);
    if ($stmt->execute()) {
        $_SESSION['flash_success'] = "🗑 Application deleted successfully.";
    } else {
        $_SESSION['flash_error'] = "❌ Failed to delete: " . htmlspecialchars($stmt->error);
    }
    $stmt->close();

    header("Location: /admin/dashboard.php");
    exit;
} else {
    header("Location: /admin/dashboard.php");
    exit;
}
