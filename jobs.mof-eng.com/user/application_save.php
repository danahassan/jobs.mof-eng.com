<?php
// Handles edit/delete for user job applications

require __DIR__ . '/../includes/auth_user.php';
require __DIR__ . '/../db.php';
require __DIR__ . '/../includes/helpers.php';

$uid = (int)($_SESSION['user_id'] ?? 0);
if ($uid === 0) {
    redirect('/auth/login.php');
}

$action = $_POST['action'] ?? '';

/* ------------------------------------
   📝 Edit Application
------------------------------------ */
if ($action === 'edit_application') {
    $id = (int)($_POST['id'] ?? 0);

    // Verify that this application belongs to the logged-in user
    $check = $conn->prepare("SELECT id FROM job_applications WHERE id=? AND user_id=?");
    $check->bind_param("ii", $id, $uid);
    $check->execute();
    $exists = $check->get_result()->num_rows;
    $check->close();

    if (!$exists) {
        $_SESSION['message'] = "Unauthorized edit attempt.";
        $_SESSION['message_type'] = "danger";
        redirect('/user/dashboard.php');
    }

    $position = sanitize_input($_POST['position'] ?? '');
    $years_experience = (int)($_POST['years_experience'] ?? 0);
    $expected_salary = (float)($_POST['expected_salary'] ?? 0);
    $message = sanitize_input($_POST['message'] ?? '');

    $stmt = $conn->prepare("UPDATE job_applications 
        SET position=?, years_experience=?, expected_salary=?, message=? 
        WHERE id=? AND user_id=?");
    $stmt->bind_param("sidssi", $position, $years_experience, $expected_salary, $message, $id, $uid);

    if ($stmt->execute()) {
        $_SESSION['message'] = "Application updated successfully.";
        $_SESSION['message_type'] = "success";
    } else {
        $_SESSION['message'] = "Error updating application: " . $stmt->error;
        $_SESSION['message_type'] = "danger";
    }
    $stmt->close();

/* ------------------------------------
   🗑️ Delete Application
------------------------------------ */
} elseif ($action === 'delete_application') {
    $id = (int)($_POST['id'] ?? 0);

    $stmt = $conn->prepare("DELETE FROM job_applications WHERE id=? AND user_id=?");
    $stmt->bind_param("ii", $id, $uid);

    if ($stmt->execute()) {
        $_SESSION['message'] = "Application deleted successfully.";
        $_SESSION['message_type'] = "success";
    } else {
        $_SESSION['message'] = "Error deleting application: " . $stmt->error;
        $_SESSION['message_type'] = "danger";
    }
    $stmt->close();
}

redirect('/user/dashboard.php');
exit;
?>
