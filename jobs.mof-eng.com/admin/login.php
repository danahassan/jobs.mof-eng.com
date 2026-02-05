<?php
if (session_status() === PHP_SESSION_NONE) session_start();
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php';

if (!empty($_SESSION['user_id']) && ($_SESSION['role'] ?? '') === 'admin') {
    header('Location: /admin/dashboard.php'); exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';

    $stmt = $conn->prepare("SELECT id, name, email, password_hash, role FROM users WHERE email=? LIMIT 1");
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $user = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if ($user && password_verify($password, $user['password_hash']) && $user['role'] === 'admin') {
        $_SESSION['user_id'] = (int)$user['id'];
        $_SESSION['role'] = 'admin';
        $_SESSION['name'] = $user['name'];
        $_SESSION['email'] = $user['email'];
        header('Location: /admin/dashboard.php'); exit;
    } else {
        $error = "Invalid admin credentials.";
    }
}

$page_title = "Admin Login";
include __DIR__ . '/../includes/header.php';
?>
<div class="container py-5" style="max-width:600px;">
    <div class="card shadow-sm">
        <div class="card-header bg-dark text-white">
            <strong><i class="bi bi-shield-lock"></i> Admin Login</strong>
        </div>
        <div class="card-body">
            <?php if ($error): ?>
                <div class="alert alert-danger"><?= e($error) ?></div>
            <?php endif; ?>
            <form method="post">
                <div class="mb-3">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-control" name="email" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" class="form-control" name="password" required>
                </div>
                <button class="btn btn-dark w-100">Login</button>
            </form>
        </div>
    </div>
</div>
<?php include __DIR__ . '/../includes/footer.php'; ?>
