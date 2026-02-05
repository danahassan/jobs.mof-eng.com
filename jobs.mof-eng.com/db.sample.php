
<?php
date_default_timezone_set('Asia/Baghdad');
// Database connection
$DB_HOST = 'localhost';
$DB_USER = 'mofengco_jobs';
$DB_PASS = 'Jobs@2025';
$DB_NAME = 'mofengco_jobs';

$conn = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME);
if ($conn->connect_error) {
    die("Database connection failed: " . htmlspecialchars($conn->connect_error));
}
$conn->set_charset("utf8mb4");
$conn->query("SET time_zone = '+03:00'");
?>
