<?php
require __DIR__ . '/../includes/auth_admin.php';
require __DIR__ . '/../db.php';
$page_title = "Application Details";

/* -----------------------------
   Fetch Application Info
----------------------------- */
$app = null;
if (isset($_GET['id']) && is_numeric($_GET['id'])) {
    $id = (int)$_GET['id'];
    $stmt = $conn->prepare("
        SELECT 
            a.*, 
            u.name AS applicant_name, 
            u.email, 
            u.phone, 
            u.areacode, 
            u.age, 
            u.address, 
            p.position_name
        FROM job_applications a
        LEFT JOIN users u ON u.id = a.user_id
        LEFT JOIN job_positions p ON p.id = a.position_id
        WHERE a.id = ?
    ");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $app = $stmt->get_result()->fetch_assoc();
    $stmt->close();
}

/* -----------------------------
   Helper: Badge color
----------------------------- */
function get_status_badge_color($status) {
    return match ($status) {
        'Hired' => 'success',
        'Interview' => 'info',
        'Offer' => 'primary',
        'Screening' => 'warning',
        'Rejected' => 'danger',
        default => 'secondary',
    };
}

include __DIR__ . '/../includes/header.php';
?>

<style>
.card {
    border-radius: 0.75rem;
    overflow: hidden;
}
.card-header {
    font-weight: 600;
    font-size: 1rem;
}
.highlight-header {
    background: linear-gradient(90deg, #198754, #0d6efd);
    color: #fff !important;
}
.info-card {
    border-top: 4px solid #198754;
}
label.fw-medium {
    min-width: 160px;
}
select.status-dropdown {
    font-weight: 600;
    border-radius: 0.4rem;
    padding: 0.3rem 0.6rem;
}
.comment-box {
    background: #f8f9fa;
    border-radius: 0.5rem;
    padding: 1rem;
    border: 1px solid #dee2e6;
    margin-bottom: 1rem;
}
.delete-box {
    border-top: 1px solid #f1f1f1;
    background: #fff8f8;
    padding: 1rem;
    text-align: right;
}
.delete-box button {
    background-color: #dc3545;
    color: #fff;
    border: none;
    border-radius: 0.4rem;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    transition: background 0.2s ease-in-out;
}
.delete-box button:hover {
    background-color: #bb2d3b;
}
</style>

<div class="container py-4">
    <?php if ($app): ?>
        <h3 class="fw-bold mb-4 border-bottom pb-2">
            Application Details — <?= htmlspecialchars($app['applicant_name'] ?? 'Applicant') ?>
        </h3>

        <div class="row g-4">
            <!-- LEFT CARD -->
            <div class="col-lg-5">
                <div class="card shadow-sm">
                    <div class="card-header highlight-header">Application Summary</div>
                    <ul class="list-group list-group-flush">
                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Position:</span>
                            <span><?= htmlspecialchars($app['position_name'] ?? 'N/A') ?></span>
                        </li>

                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span class="fw-medium">Status:</span>
                            <select id="statusDropdown" class="form-select form-select-sm w-auto status-dropdown"
                                data-id="<?= $app['id'] ?>">
                                <?php
                                $statuses = ['New', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected'];
                                foreach ($statuses as $status) {
                                    $selected = ($status === $app['status']) ? 'selected' : '';
                                    echo "<option value='$status' $selected>$status</option>";
                                }
                                ?>
                            </select>
                        </li>

                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Applied:</span>
                            <span><?= date('M d, Y H:i A', strtotime($app['applied_at'])) ?></span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Source:</span>
                            <span><?= htmlspecialchars($app['source'] ?? 'N/A') ?></span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Experience:</span>
                            <span><?= htmlspecialchars($app['years_experience'] ?? '—') ?> yrs</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Expected Salary:</span>
                            <span>$<?= htmlspecialchars($app['expected_salary'] ?? '—') ?></span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span class="fw-medium">Age:</span>
                            <span><?= htmlspecialchars($app['age'] ?? '—') ?></span>
                        </li>
                        <?php if (!empty($app['resume_path'])): ?>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span class="fw-medium">Resume:</span>
                            <a href="/<?= htmlspecialchars($app['resume_path']) ?>" target="_blank" class="btn btn-sm btn-outline-success">
                                <i class="bi bi-download"></i> Download
                            </a>
                        </li>
                        <?php endif; ?>
                    </ul>
                    <div class="delete-box">
                        <form method="post" action="/admin/delete_application.php"
                            onsubmit="return confirm('Are you sure you want to delete this application?');">
                            <input type="hidden" name="id" value="<?= $app['id'] ?>">
                            <button type="submit"><i class="bi bi-trash"></i> Delete Application</button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- RIGHT CARD -->
            <div class="col-lg-7">
                <div class="card shadow-sm info-card mb-4">
                    <div class="card-header bg-light fw-semibold">Contact & Personal Info</div>
                    <ul class="list-group list-group-flush">
                        <li class="list-group-item">
                            <label class="fw-medium">Full Name:</label>
                            <?= htmlspecialchars($app['applicant_name'] ?? 'N/A') ?>
                        </li>
                        <li class="list-group-item">
                            <label class="fw-medium">Email:</label>
                            <?= htmlspecialchars($app['email'] ?? 'N/A') ?>
                        </li>
                        <li class="list-group-item">
                            <label class="fw-medium">Phone:</label>
                            <?= htmlspecialchars(($app['areacode'] ? '(' . $app['areacode'] . ') ' : '') . ($app['phone'] ?? 'N/A')) ?>
                        </li>
                        <li class="list-group-item">
                            <label class="fw-medium">Address:</label>
                            <?= htmlspecialchars($app['address'] ?? 'N/A') ?>
                        </li>
                    </ul>
                </div>

                <!-- User Message -->
                <?php if (!empty($app['message'])): ?>
                <div class="card shadow-sm mb-4">
                    <div class="card-header bg-info text-white fw-semibold">
                        <i class="bi bi-chat-left-text"></i> User Message
                    </div>
                    <div class="card-body">
                        <p class="text-dark mb-0"><?= nl2br(htmlspecialchars($app['message'])) ?></p>
                    </div>
                </div>
                <?php endif; ?>

                <!-- Application Comments -->
                <?php
                $comments = [];
                $cid = (int)$app['id'];
                $cres = $conn->query("
                    SELECT ac.*, u.name AS author_name
                    FROM application_comments ac
                    LEFT JOIN users u ON u.id = ac.user_id
                    WHERE ac.application_id = $cid
                    ORDER BY ac.created_at DESC
                ");
                if ($cres) while ($r = $cres->fetch_assoc()) $comments[] = $r;
                ?>
                <div class="card shadow-sm">
                    <div class="card-header bg-success text-white fw-semibold">
                        <i class="bi bi-chat-dots"></i> Comments
                    </div>
                    <div class="card-body">
                        <?php if (!empty($comments)): ?>
                            <?php foreach ($comments as $c): ?>
                                <div class="comment-box">
                                    <div class="d-flex justify-content-between">
                                        <strong><?= htmlspecialchars($c['author_name'] ?? 'Admin') ?></strong>
                                        <small class="text-muted"><?= date('M d, Y H:i', strtotime($c['created_at'])) ?></small>
                                    </div>
                                    <p class="mb-1 mt-2"><?= nl2br(htmlspecialchars($c['comment'])) ?></p>
                                    <span class="badge bg-<?= $c['visible_to_applicant'] ? 'primary' : 'secondary' ?>">
                                        <?= $c['visible_to_applicant'] ? 'Visible to Applicant' : 'Admin Only' ?>
                                    </span>
                                </div>
                            <?php endforeach; ?>
                        <?php else: ?>
                            <p class="text-muted fst-italic mb-0">No comments yet.</p>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
    <?php else: ?>
        <div class="alert alert-danger text-center shadow-sm" role="alert">
            <h4 class="alert-heading">Application Not Found!</h4>
            <p>The requested application could not be located.</p>
            <hr>
            <a href="/admin/applications.php" class="btn btn-danger">
                <i class="bi bi-arrow-left"></i> Back to List
            </a>
        </div>
    <?php endif; ?>
</div>

<!-- AJAX Status Update -->
<script>
document.getElementById('statusDropdown')?.addEventListener('change', async (e) => {
    const id = e.target.dataset.id;
    const newStatus = e.target.value;
    e.target.disabled = true;
    const res = await fetch('/admin/update_status.php', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `id=${id}&status=${encodeURIComponent(newStatus)}`
    });
    if (res.ok) {
        alert(`✅ Status updated to "${newStatus}"`);
    } else {
        alert('❌ Failed to update status');
    }
    e.target.disabled = false;
});
</script>

<?php include __DIR__ . '/../includes/footer.php'; ?>
