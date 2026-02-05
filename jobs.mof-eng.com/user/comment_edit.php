<?php
require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';

$uid = (int)($_SESSION['user_id'] ?? 0);
$id = (int)($_POST['id'] ?? 0);
$comment = trim($_POST['comment'] ?? '');

if ($uid <= 0 || $id <= 0 || $comment === '') {
    http_response_code(400);
    exit('Invalid data.');
}

// Check ownership first (optional but safer)
$check = $conn->prepare("SELECT id FROM application_comments WHERE id=? AND user_id=?");
$check->bind_param("ii", $id, $uid);
$check->execute();
$found = $check->get_result()->fetch_assoc();
$check->close();

if (!$found) {
    http_response_code(403);
    exit('Not allowed.');
}

// Update comment text
if ($conn->query("SHOW COLUMNS FROM application_comments LIKE 'updated_at'")->num_rows > 0) {
    $stmt = $conn->prepare("UPDATE application_comments SET comment=?, updated_at=NOW() WHERE id=? AND user_id=?");
} else {
    $stmt = $conn->prepare("UPDATE application_comments SET comment=? WHERE id=? AND user_id=?");
}
$stmt->bind_param("sii", $comment, $id, $uid);

if ($stmt->execute()) {
    http_response_code(200);
    exit('Updated.');
} else {
    http_response_code(500);
    exit('Database error: ' . $stmt->error);
}
