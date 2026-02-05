<?php
// /user/profile_save.php
// Handles updating user profile (contact + education + experience + skills)

require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php';

if (session_status() === PHP_SESSION_NONE) { session_start(); }

$uid = (int)($_SESSION['user_id'] ?? 0);
if ($uid === 0) {
    redirect('/auth/login.php');
}

$action = $_POST['action'] ?? '';

if ($action === 'edit_contact') {
    // Safe trimming helper (no dependency on sanitize_input)
    $f = function($k) { return trim((string)($_POST[$k] ?? '')); };

    $name   = $f('name');
    $email  = $f('email');
    $phone  = $f('phone');
    $gender = $f('gender');
    $age    = (int)($_POST['age'] ?? 0);
    $address  = $f('address');
    $address2 = $f('address2');
    $city     = $f('city');
    $country  = $f('country');

    // Integrated fields
    $highest_degree = $f('highest_degree');
    $institution    = $f('institution');
    $graduation_year = $f('graduation_year');
    $experience_title = $f('experience_title');
    $experience_company = $f('experience_company');
    $experience_years = $f('experience_years');
    $experience_description = $f('experience_description');
    $skills = $f('skills');

    $sql = "UPDATE users SET
                name=?, email=?, phone=?, gender=?, age=?,
                address=?, address2=?, city=?, country=?,
                highest_degree=?, institution=?, graduation_year=?,
                experience_title=?, experience_company=?, experience_years=?, experience_description=?, skills=?
            WHERE id=?";

    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        $_SESSION['message'] = "Error preparing statement.";
        $_SESSION['message_type'] = "danger";
        redirect('/user/dashboard.php');
        exit;
    }

    $stmt->bind_param(
        "ssssissssssssssssi",
        $name, $email, $phone, $gender, $age,
        $address, $address2, $city, $country,
        $highest_degree, $institution, $graduation_year,
        $experience_title, $experience_company, $experience_years, $experience_description, $skills,
        $uid
    );

    if ($stmt->execute()) {
        $_SESSION['message'] = "Personal information updated successfully!";
        $_SESSION['message_type'] = "success";
    } else {
        $_SESSION['message'] = "Error updating information: " . e($stmt->error);
        $_SESSION['message_type'] = "danger";
    }
    $stmt->close();

    redirect('/user/dashboard.php');
    exit;
}

// Default redirect if action not recognized
redirect('/user/dashboard.php');
exit;
