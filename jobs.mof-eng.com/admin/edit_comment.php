<?php
// /admin/edit_comment.php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';

$comment_id = (int)($_GET['id'] ?? 0);
$err = '';
$success = '';

// Fetch existing comment
$stmt = $conn->prepare("SELECT * FROM application_comments WHERE id = ? LIMIT 1");
$stmt->bind_param("i", $comment_id);
$stmt->execute();
$comment_data = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$comment_data) {
    die("Comment not found.");
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $new_comment = trim($_POST['comment'] ?? '');
    $visible = isset($_POST['visible_to_applicant']) ? (int)$_POST['visible_to_applicant'] : 0;

    if ($new_comment !== '') {
        $upd = $conn->prepare("UPDATE application_comments SET comment = ?, visible_to_applicant = ? WHERE id = ?");
        $upd->bind_param("sii", $new_comment, $visible, $comment_id);
        
        if ($upd->execute()) {
            header("Location: /admin/application_detail.php?id=" . $comment_data['application_id'] . "&msg=updated");
            exit;
        } else {
            $err = "Update failed: " . $conn->error;
        }
        $upd->close();
    } else {
        $err = "Comment cannot be empty.";
    }
}

$page_title = "Edit Comment";
include __DIR__ . '/../includes/header.php';
?>

<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="/admin/application_detail.php?id=<?= $comment_data['application_id'] ?>">Back to Application</a></li>
                    <li class="breadcrumb-item active">Edit Comment</li>
                </ol>
            </nav>

            <div class="card shadow-sm border-0">
                <div class="card-body p-4">
                    <h3 class="fw-bold mb-4">Edit Comment</h3>
                    
                    <?php if($err): ?> <div class="alert alert-danger"><?= $err ?></div> <?php endif; ?>

                    <form method="post">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Comment Text</label>
                            <textarea name="comment" class="form-control" rows="5" required><?= htmlspecialchars($comment_data['comment']) ?></textarea>
                        </div>

                        <div class="mb-4">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="visible_to_applicant" value="1" id="visibleCheck" <?= $comment_data['visible_to_applicant'] ? 'checked' : '' ?>>
                                <label class="form-check-label" for="visibleCheck">Visible to Applicant</label>
                            </div>
                            <small class="text-muted">Note: Changing visibility to "On" does not re-send the email notification.</small>
                        </div>

                        <div class="d-flex gap-2">
                            <button type="submit" class="btn btn-success px-4 fw-bold">Save Changes</button>
                            <a href="/admin/application_detail.php?id=<?= $comment_data['application_id'] ?>" class="btn btn-light px-4">Cancel</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/../includes/footer.php'; ?>