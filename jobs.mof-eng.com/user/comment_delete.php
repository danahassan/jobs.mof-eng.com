<?php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';

$uid = (int)($_SESSION['user_id'] ?? 0);
$id = (int)($_POST['id'] ?? 0);

if ($uid > 0 && $id > 0) {
    $stmt = $conn->prepare("DELETE FROM application_comments WHERE id=? AND user_id=?");
    $stmt->bind_param("ii", $id, $uid);
    $stmt->execute();
    $stmt->close();
    http_response_code(200);
    exit;
}
http_response_code(400);
