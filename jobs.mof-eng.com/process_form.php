<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);

/* ------------------------------------------------------------------
   Database connection (PDO)
------------------------------------------------------------------ */
$DB_HOST = 'localhost';
$DB_USER = 'mofengco_jobs';
$DB_PASS = 'Jobs@2025';
$DB_NAME = 'mofengco_jobs';

try {
    $pdo = new PDO("mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4",
                   $DB_USER, $DB_PASS,
                   [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
} catch (PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}

if (session_status() === PHP_SESSION_NONE) session_start();

/* ------------------------------------------------------------------
   Utility
------------------------------------------------------------------ */
function e($s){ return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

/* ------------------------------------------------------------------
   Handle form
------------------------------------------------------------------ */
if ($_SERVER['REQUEST_METHOD'] === 'POST') {

    // 1️⃣  Collect inputs
    $firstname  = trim($_POST['firstname']  ?? '');
    $lastname   = trim($_POST['lastname']   ?? '');
    $email      = trim($_POST['email']      ?? '');
    $gender     = trim($_POST['gender']     ?? '');
    $areacode   = trim($_POST['areacode']   ?? '');
    $phone      = trim($_POST['phone']      ?? '');
    $age        = (int)($_POST['age'] ?? 0);
    $startdate  = $_POST['startdate'] ?? null;
    $address    = trim($_POST['address']    ?? '');
    $address2   = trim($_POST['address2']   ?? '');
    $message    = trim($_POST['message']    ?? '');
    $position   = trim($_POST['position']   ?? '');
    $years_experience = ($_POST['years_experience']!=='') ? (int)$_POST['years_experience'] : null;
    $source     = $_POST['source'] ?? 'Website';
    $expected_salary = ($_POST['expected_salary']!=='') ? (float)$_POST['expected_salary'] : null;
    $user_id    = $_SESSION['user_id'] ?? null;

    // 2️⃣  Upload resume
    $cv_filename = null;
    $resume_path = null;
    if (!empty($_FILES['resume']['name'])) {
        $ext = strtolower(pathinfo($_FILES['resume']['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, ['pdf','doc','docx'])) {
            die("Invalid resume file type.");
        }
        $upload_dir = __DIR__ . '/uploads/resumes/';
        if (!is_dir($upload_dir)) mkdir($upload_dir, 0755, true);

        $cv_filename = uniqid('cv_') . '.' . $ext;
        $resume_path = '/uploads/resumes/' . $cv_filename;
        $dest = $upload_dir . $cv_filename;

        if (!move_uploaded_file($_FILES['resume']['tmp_name'], $dest)) {
            die("Failed to save uploaded resume. Check folder permissions.");
        }
    }

    // 3️⃣  Insert using PDO
    $sql = "INSERT INTO job_applications
            (firstname, lastname, email, gender, areacode, phone, age, startdate,
             address, address2, message, resume_path,
             applied_at, submission_date, user_id, position,
             years_experience, source, status, expected_salary, cv_filename)
            VALUES (:firstname, :lastname, :email, :gender, :areacode, :phone, :age,
                    :startdate, :address, :address2, :message, :resume_path,
                    NOW(), NOW(), :user_id, :position, :years_experience,
                    :source, 'New', :expected_salary, :cv_filename)";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        ':firstname' => $firstname,
        ':lastname'  => $lastname,
        ':email'     => $email,
        ':gender'    => $gender,
        ':areacode'  => $areacode,
        ':phone'     => $phone,
        ':age'       => $age,
        ':startdate' => $startdate,
        ':address'   => $address,
        ':address2'  => $address2,
        ':message'   => $message,
        ':resume_path' => $resume_path,
        ':user_id'   => $user_id,
        ':position'  => $position,
        ':years_experience' => $years_experience,
        ':source'    => $source,
        ':expected_salary' => $expected_salary,
        ':cv_filename' => $cv_filename
    ]);

    // 4️⃣  Redirect after success
    header("Location: /user/dashboard.php?submitted=1");
    exit;
}
?>
