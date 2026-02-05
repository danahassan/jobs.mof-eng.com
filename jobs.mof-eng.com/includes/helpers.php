<?php
if (session_status() === PHP_SESSION_NONE) session_start();

/* -------------------------------
   🧭 Session & Role Helpers
--------------------------------*/
function is_logged_in() { 
    return !empty($_SESSION['user_id']); 
}

function current_user_id() { 
    return $_SESSION['user_id'] ?? null; 
}

function current_user_role() { 
    return $_SESSION['role'] ?? null; 
}

function is_admin() { 
    return (current_user_role() === 'admin'); 
}

/* -------------------------------
   🧹 Input & Output Sanitization
--------------------------------*/
/**
 * Escapes output safely for HTML.
 */
function e($s) { 
    return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); 
}

/**
 * Sanitizes incoming input from forms.
 * Works for strings and arrays recursively.
 */
function sanitize_input($data) {
    if (is_array($data)) {
        return array_map('sanitize_input', $data);
    }
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data, ENT_QUOTES, 'UTF-8');
    return $data;
}

/* -------------------------------
   🔁 Redirect Helper
--------------------------------*/
function redirect($url){
    header("Location: " . $url);
    exit;
}
?>
