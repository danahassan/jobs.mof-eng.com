<?php
if (session_status() === PHP_SESSION_NONE) session_start();

/*
----------------------------------------------------------
 🔐 AUTH USER CHECKER
 Only allows regular "user" (applicant) role.
 Redirects others (admins or guests) to login.
----------------------------------------------------------
*/

if (empty($_SESSION['user_id']) || ($_SESSION['role'] ?? '') !== 'user') {
    // If not logged in or not a user role
    header("Location: /auth/login.php");
    exit;
}
?>
