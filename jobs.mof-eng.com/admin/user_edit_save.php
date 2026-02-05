<?php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = (int)($_POST['id'] ?? 0);
    $name = trim($_POST['name'] ?? '');
    $email = trim($_POST['email'] ?? '');
    $phone = trim($_POST['phone'] ?? '');
    $city = trim($_POST['city'] ?? '');
    $country = trim($_POST['country'] ?? '');

    if ($id <= 0 || $name === '' || $email === '') {
        echo "Invalid data.";
        exit;
    }

    // Update only users (not admins)
    $stmt = $conn->prepare("
        UPDATE users
        SET name=?, email=?, phone=?, city=?, country=?
        WHERE id=? AND role='user'
    ");
    $stmt->bind_param("sssssi", $name, $email, $phone, $city, $country, $id);
    $stmt->execute();

    if ($stmt->affected_rows >= 0) {
        echo "success";
    } else {
        echo "error";
    }

    $stmt->close();
}
?>
