<?php
// -----------------------------------------------------------------------------
// File: /home/mofengco/jobs.mof-eng.com/index.php
// Purpose: Redirect visitors appropriately
// -----------------------------------------------------------------------------

session_start();

// ✅ If user already logged in, redirect by role
if (isset($_SESSION['user_id']) && isset($_SESSION['role'])) {
    if ($_SESSION['role'] === 'admin') {
        header("Location: /admin/dashboard.php");
        exit;
    } elseif ($_SESSION['role'] === 'user') {
        header("Location: /user/dashboard.php");
        exit;
    }
}

// 🚪 Default: show job listings for everyone else
header("Location: /auth/login.php");
exit;
?>
