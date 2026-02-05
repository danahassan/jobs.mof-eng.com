<?php
if (session_status() === PHP_SESSION_NONE) session_start();
// Simple gate: ensure role is admin
if (empty($_SESSION['user_id']) || ($_SESSION['role'] ?? 'user') !== 'admin') {
    header("Location: /auth/login.php");
    exit;
}
