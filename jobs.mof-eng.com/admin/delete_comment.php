<?php
// /admin/delete_comment.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

// Only allow POST for deletions (Security best practice)
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $comment_id = (int)($_POST['id'] ?? 0);
    $application_id = (int)($_POST['application_id'] ?? 0);

    if ($comment_id > 0) {
        $stmt = $conn->prepare("DELETE FROM application_comments WHERE id = ?");
        $stmt->bind_param("i", $comment_id);
        
        if ($stmt->execute()) {
            // Success
            header("Location: /admin/application_detail.php?id=" . $application_id . "&msg=deleted");
        } else {
            // Error
            header("Location: /admin/application_detail.php?id=" . $application_id . "&msg=error");
        }
        $stmt->close();
    } else {
        header("Location: /admin/dashboard.php");
    }
} else {
    die("Method not allowed.");
}
exit;