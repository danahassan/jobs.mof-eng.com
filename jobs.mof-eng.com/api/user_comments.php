<?php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

$user_id = (int)($_POST['user_id'] ?? 0);
$comment = trim($_POST['comment'] ?? '');
$admin_id = (int)$_SESSION['user_id'];

if ($user_id && $comment !== ''){
  $stmt = $conn->prepare("INSERT INTO user_comments(user_id, admin_id, comment) VALUES (?,?,?)");
  $stmt->bind_param("iis", $user_id, $admin_id, $comment);
  $stmt->execute();
}
header("Location: /admin/user_view.php?id=".$user_id);
exit;
