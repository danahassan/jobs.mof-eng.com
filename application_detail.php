<?php
// Improved application_detail.php Code

// Secure Database Connection
function getDB() {
    $host = 'localhost';
    $db = 'dbname';
    $user = 'dbuser';
    $pass = 'dbpass';
    $charset = 'utf8mb4';

    $dsn = "mysql:host=$host;dbname=$db;charset=$charset";
    $options = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];

    try {
        return new PDO($dsn, $user, $pass, $options);
    } catch (	hrowable $e) {
        echo 'Connection failed: ' . $e->getMessage();
        exit;
    }
}

// CSRF Protection
session_start();
if (empty($_SESSION['token'])) {
    $_SESSION['token'] = bin2hex(random_bytes(32));
}
$token = $_SESSION['token'];

// Fetching application details securely
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($token, $_POST['token'])) {
        die('CSRF token validation failed.');
    }

    $appID = filter_input(INPUT_POST, 'app_id', FILTER_SANITIZE_NUMBER_INT);
    $stmt = getDB()->prepare('SELECT * FROM applications WHERE id = :id');
    $stmt->execute(['id' => $appID]);
    $application = $stmt->fetch();
}

// Further processing...
?>